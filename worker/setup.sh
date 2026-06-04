#!/usr/bin/env bash
# Self-configuring orchestra worker setup.
#
# Starts the webhook receiver + a cloudflared quick tunnel, reads the tunnel's
# assigned URL, and registers/updates the GitHub push webhook to point at it.
# Re-running re-points the webhook (quick-tunnel URLs change on restart).
#
# Usage:  REPO=owner/name bash worker/setup.sh
# Override: WORKDIR, PORT, PI_PROVIDER, PI_MODEL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
set -euo pipefail

REPO="${REPO:-khangpworking/model-orchestra}"
WORKDIR="${WORKDIR:-$HOME/orchestra-worker}"
PORT="${PORT:-8799}"
REPO_DIR="$WORKDIR/repo"
SECRET_FILE="$WORKDIR/.webhook-secret"

# 1. preflight ------------------------------------------------------------
missing=0
for c in git gh cloudflared python3 openssl; do
  command -v "$c" >/dev/null || { echo "MISSING: $c"; missing=1; }
done
command -v pi >/dev/null || echo "WARN: 'pi' not on PATH — the implementer step will fail until it is."
[ "$missing" = 1 ] && { echo "Install the missing tools above, then re-run."; exit 1; }
gh auth status >/dev/null 2>&1 || {
  echo "Not authed. Run:  gh auth login --scopes 'repo,admin:repo_hook'"
  echo "Then re-run this script."; exit 1; }

# 2. clone / update -------------------------------------------------------
mkdir -p "$WORKDIR"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" fetch --all -q
  git -C "$REPO_DIR" checkout master -q
  git -C "$REPO_DIR" reset --hard origin/master -q   # pick up worker-code fixes on re-run
else
  gh repo clone "$REPO" "$REPO_DIR"
fi
# commit identity for the worker's status/result pushes (not an AI footprint)
git -C "$REPO_DIR" config user.name "orchestra-worker"
git -C "$REPO_DIR" config user.email "orchestra-worker@local"

# 3. shared secret (generated once, reused) -------------------------------
[ -f "$SECRET_FILE" ] || (umask 077; openssl rand -hex 32 > "$SECRET_FILE")
SECRET="$(cat "$SECRET_FILE")"

# 4. (re)start the receiver ----------------------------------------------
pkill -f "$WORKDIR/repo/worker/receiver.py" 2>/dev/null || true
WEBHOOK_SECRET="$SECRET" REPO_DIR="$REPO_DIR" PORT="$PORT" \
  PI_PROVIDER="${PI_PROVIDER:-cliproxy}" PI_MODEL="${PI_MODEL:-gemma-31b}" \
  TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}" TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}" \
  nohup python3 "$REPO_DIR/worker/receiver.py" > "$WORKDIR/receiver.log" 2>&1 &
sleep 1

# 5. (re)start the quick tunnel, capture its URL --------------------------
pkill -f "cloudflared tunnel --url" 2>/dev/null || true
nohup cloudflared tunnel --url "http://localhost:$PORT" > "$WORKDIR/tunnel.log" 2>&1 &
URL=""
for _ in $(seq 1 30); do
  URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$WORKDIR/tunnel.log" | head -1 || true)
  [ -n "$URL" ] && break; sleep 1
done
[ -z "$URL" ] && { echo "Tunnel URL not found — see $WORKDIR/tunnel.log"; exit 1; }
HOOK_URL="$URL/dispatch"

# 6. register or update the GitHub webhook --------------------------------
existing=$(gh api "repos/$REPO/hooks" --jq '.[] | select(.config.url | endswith("/dispatch")) | .id' 2>/dev/null | head -1 || true)
payload=$(printf '{"config":{"url":"%s","content_type":"json","secret":"%s"},"events":["push"],"active":true}' "$HOOK_URL" "$SECRET")
if [ -n "$existing" ]; then
  printf '%s' "$payload" | gh api -X PATCH "repos/$REPO/hooks/$existing" --input - >/dev/null
  echo "Updated webhook $existing"
else
  printf '%s' "$payload" | gh api -X POST "repos/$REPO/hooks" --input - >/dev/null
  echo "Created webhook"
fi

echo
echo "Worker up."
echo "  repo:   $REPO"
echo "  tunnel: $URL  (-> 127.0.0.1:$PORT)"
echo "  logs:   $WORKDIR/receiver.log  $WORKDIR/tunnel.log"
echo "  stop:   pkill -f receiver.py; pkill -f 'cloudflared tunnel --url'"
echo
echo "NOTE: quick-tunnel URLs change on restart. If the tunnel restarts, re-run this script to re-point the webhook."
