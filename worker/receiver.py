#!/usr/bin/env python3
"""Orchestra worker webhook receiver.

Listens for GitHub push webhooks. When a feature branch is pushed whose
`.ai/DISPATCH.md` has `status: requested`, it runs the listed implementer
steps through scripts/dispatch.py and pushes the result branch back, flipping
the marker status as it goes.

The audit gate is NOT run here — that stays on the orchestrator
(see docs/distributed.md). This worker implements and pushes; it never approves.

WARNING: the /dispatch endpoint executes code (the implementer writes and
pushes). The webhook secret is its only gate — treat it as a credential.

Env:
  WEBHOOK_SECRET   shared secret GitHub signs payloads with (required)
  REPO_DIR         path to the cloned repo (required)
  PORT             listen port on 127.0.0.1 (default 8799)
  PI_PROVIDER      passed to dispatch.py --provider (default cliproxy)
  PI_MODEL         passed to dispatch.py --model    (default gemma-31b)
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   optional, for done/failed pings
"""
import hashlib
import hmac
import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

SECRET = os.environ["WEBHOOK_SECRET"].encode()
REPO_DIR = os.environ["REPO_DIR"]
PORT = int(os.environ.get("PORT", "8799"))
PROVIDER = os.environ.get("PI_PROVIDER", "cliproxy")
MODEL = os.environ.get("PI_MODEL", "gemma-31b")
MARKER = ".ai/DISPATCH.md"


def git(*args):
    return subprocess.run(
        ["git", "-C", REPO_DIR, *args], check=True, capture_output=True, text=True
    ).stdout


def valid_sig(body, sig):
    if not sig or not sig.startswith("sha256="):
        return False
    mac = hmac.new(SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest("sha256=" + mac, sig)


def read_marker():
    path = os.path.join(REPO_DIR, MARKER)
    fields = {}
    if os.path.isfile(path):
        for line in open(path):
            if ":" in line and not line.lstrip().startswith("#"):
                k, v = line.split(":", 1)
                fields[k.strip()] = v.strip()
    return fields


def set_status(branch, status):
    path = os.path.join(REPO_DIR, MARKER)
    txt = re.sub(r"(?m)^status:.*$", f"status: {status}", open(path).read())
    open(path, "w").write(txt)
    # stage everything so the implementer's edits ride along with the status flip,
    # not just the marker. "running" is committed pre-run (clean tree → marker only);
    # "done"/"failed" captures whatever the implementer wrote.
    git("add", "-A")
    git("commit", "-m", f"worker: dispatch {status}")
    git("push", "origin", branch)
    notify(f"dispatch {status} on {branch}")


def notify(msg):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (tok and chat):
        return
    import urllib.parse
    import urllib.request

    data = urllib.parse.urlencode({"chat_id": chat, "text": "[orchestra-worker] " + msg}).encode()
    try:
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=10
        )
    except Exception:
        pass


def run_dispatch(branch, steps):
    set_status(branch, "running")
    base = ["python3", os.path.join(REPO_DIR, "scripts", "dispatch.py"),
            REPO_DIR, "--provider", PROVIDER, "--model", MODEL]
    ok = True
    for step in [s.strip() for s in steps.split(",") if s.strip()]:
        if subprocess.run(base + ["--step", step], cwd=REPO_DIR).returncode != 0:
            ok = False
            break
    set_status(branch, "done" if ok else "failed")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if not valid_sig(body, self.headers.get("X-Hub-Signature-256")):
            self.send_response(401)
            self.end_headers()
            return
        self.send_response(202)  # ack fast — GitHub times out at 10s
        self.end_headers()
        try:
            branch = json.loads(body).get("ref", "").replace("refs/heads/", "")
            if not branch.startswith("feat/"):
                return
            # sync to the pushed branch, then act only on a fresh dispatch request.
            # our own status pushes set status != requested, so they no-op here.
            git("fetch", "origin", branch)
            git("checkout", branch)
            git("reset", "--hard", f"origin/{branch}")
            marker = read_marker()
            if marker.get("status") == "requested":
                run_dispatch(branch, marker.get("steps", ""))
        except Exception as e:
            notify(f"error: {e}")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"receiver listening on 127.0.0.1:{PORT}", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
