#!/usr/bin/env python3
"""dispatch.py — run the implementer steps of an orchestra plan through Pi.

Reads <project>/.ai/STATE.md, then runs each unchecked `executor: implementer`
step through Pi (headless, agentic) against the configured provider/model.
Steps run sequentially — no parallel provider spam (flow.md step 4).

Audit and the plan/push gates are NOT this script's job: the human (or Claude
wearing the reviewer hat) gates the plan before dispatch and audits the diff
after. This script only drives the implementer.

Usage:
  dispatch.py <project-dir> [--step N] [--model kimi-code] [--provider kimi]
              [--gemini-review] [--dry-run]

  --gemini-review  After each step, run `gemini` to verify the diff looks right.
                   Requires `gemini` on PATH. Set GEMINI_CMD to override the
                   default command (default: gemini --yolo -p).

Examples:
  dispatch.py ~/Developer/my-project                       # run all implementer steps
  dispatch.py ~/Developer/my-project --step 4              # run only Step 4
  dispatch.py ~/Developer/my-project --gemini-review       # implement + gemini review
  dispatch.py ~/Developer/my-project --dry-run             # show plan, run nothing
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

EFFORT_TO_THINKING = {"low": "low", "standard": "medium", "high": "high"}

STEP_RE = re.compile(r"^- \[( |x)\] (Step (\d+):.*)$")
FIELD_RE = re.compile(r"^\s*(executor|effort|agent):\s*(\S+)")

# Exit code the orchestrator uses to signal a blocked step.
EXIT_BLOCKED = 2

DEFAULT_AGENT = "kimi"

# git worktree add/remove and ref creation race on the shared .git when run
# from multiple threads; serialise just those mutations (not the agent runs).
_WORKTREE_LOCK = threading.Lock()


def parse_steps(text):
    """Return list of {num, desc, done, executor, effort} from a STATE.md body."""
    steps = []
    cur = None
    for line in text.splitlines():
        m = STEP_RE.match(line)
        if m:
            if cur:
                steps.append(cur)
            cur = {
                "done": m.group(1) == "x",
                "desc": m.group(2).strip(),
                "num": int(m.group(3)),
                "executor": None,
                "effort": None,
                "agent": None,
            }
            continue
        if cur:
            fm = FIELD_RE.match(line)
            if fm:
                cur[fm.group(1)] = fm.group(2)
    if cur:
        steps.append(cur)
    return steps


def build_prompt(step):
    return (
        "You are the implementer in a model-orchestra workflow.\n"
        "Read AGENTS.md (in the repo root) for your role and rules before doing anything.\n"
        "Then read .ai/STATE.md and the relevant design files under docs-md/ "
        "for the goal, constraints, and files in scope.\n\n"
        f"Execute ONLY this step, nothing else:\n\n  {step['desc']}\n\n"
        "If you are blocked or uncertain about anything, follow the BLOCKED procedure "
        "in AGENTS.md — write .ai/BLOCKED.md and print 'BLOCKED: see .ai/BLOCKED.md'. "
        "Do not guess or invent scope.\n\n"
        "When finished, print a one-paragraph summary of exactly which files you "
        "created or changed (with paths relative to the repo root), and the result "
        "of the verification you ran."
    )


def build_review_prompt(step, project):
    diff = subprocess.run(
        ["git", "diff", "--cached", "--stat"],
        cwd=project, capture_output=True, text=True
    ).stdout or subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=project, capture_output=True, text=True
    ).stdout
    return (
        f"You are the reviewer in a model-orchestra workflow.\n\n"
        f"The implementer just finished this step:\n\n  {step['desc']}\n\n"
        f"Git diff stat:\n{diff or '(no diff)'}\n\n"
        "Check: does the diff match what the step asked for — no more, no less? "
        "Are any obviously wrong files created or modified? "
        "Reply with one of:\n"
        "  LGTM: <one sentence why>\n"
        "  CONCERN: <specific issue>\n\n"
        "Do not re-implement anything. Observe only."
    )


def is_blocked(project):
    return (pathlib.Path(project) / ".ai" / "BLOCKED.md").is_file()


# --- parallel dispatch ----------------------------------------------------

def git(cwd, *args):
    """Run a git command, returning stdout. Raises on non-zero exit."""
    return subprocess.run(
        ["git", "-C", cwd, *args], check=True, capture_output=True, text=True
    ).stdout


def agent_cmd(agent, thinking, prompt, provider, model):
    """Map a step's agent tag to the command that runs it (see docs/parallel.md)."""
    a = (agent or DEFAULT_AGENT).lower()
    if a == "gemini":
        return os.environ.get("GEMINI_CMD", "gemini --yolo -p").split() + [prompt]
    if a == "claude":
        return os.environ.get("CLAUDE_CMD", "claude -p").split() + [prompt]
    if a == "gemma":
        return ["pi", "--provider", "cliproxy", "--model", "gemma-31b",
                "--thinking", thinking, "--print", prompt]
    # kimi / implementer / default: the configured pi provider/model
    return ["pi", "--provider", provider, "--model", model,
            "--thinking", thinking, "--print", prompt]


def run_task(step, project, feature, provider, model):
    """Run one step in its own worktree + branch, push it, return (num, status, branch)."""
    num = step["num"]
    branch = f"{feature}--s{num}"
    base = git(project, "rev-parse", "HEAD").strip()
    wt = os.path.join(tempfile.gettempdir(),
                      f"orch-{feature.replace('/', '-')}-s{num}")

    with _WORKTREE_LOCK:
        # idempotent re-run: drop any stale worktree/branch first
        subprocess.run(["git", "-C", project, "worktree", "remove", wt, "--force"],
                       capture_output=True)
        subprocess.run(["git", "-C", project, "branch", "-D", branch],
                       capture_output=True)
        git(project, "worktree", "add", "-b", branch, wt, base)

    try:
        thinking = EFFORT_TO_THINKING.get(step["effort"], "medium")
        cmd = agent_cmd(step["agent"], thinking, build_prompt(step), provider, model)
        agent = (step["agent"] or DEFAULT_AGENT).lower()
        print(f"  [s{num} -> {agent}] start: {step['desc']}", flush=True)
        rc = subprocess.run(cmd, cwd=wt).returncode
        if rc != 0:
            return (num, "failed", branch)
        if (pathlib.Path(wt) / ".ai" / "BLOCKED.md").is_file():
            return (num, "blocked", branch)
        if not git(wt, "status", "--porcelain").strip():
            return (num, "empty", branch)  # agent made no changes
        git(wt, "add", "-A")
        git(wt, "commit", "-m", f"step {num}: {step['desc'][:60]}")
        git(wt, "push", "-f", "origin", branch)
        return (num, "done", branch)
    finally:
        with _WORKTREE_LOCK:
            subprocess.run(["git", "-C", project, "worktree", "remove", wt, "--force"],
                           capture_output=True)


def run_parallel(steps, project, provider, model):
    """Run steps grouped by agent: groups concurrent, same-agent serial."""
    feature = git(project, "rev-parse", "--abbrev-ref", "HEAD").strip()
    groups = defaultdict(list)
    for s in steps:
        groups[(s["agent"] or DEFAULT_AGENT).lower()].append(s)

    print(f"Parallel: {len(steps)} step(s) across {len(groups)} agent(s): "
          f"{', '.join(sorted(groups))}")

    def run_group(group_steps):
        return [run_task(s, project, feature, provider, model) for s in group_steps]

    results = []
    with ThreadPoolExecutor(max_workers=len(groups)) as ex:
        futures = [ex.submit(run_group, g) for g in groups.values()]
        for f in as_completed(futures):
            results.extend(f.result())

    print("\n--- parallel results ---")
    for num, status, branch in sorted(results):
        print(f"  step {num}: {status:8} {branch}")

    if any(st == "blocked" for _, st, _ in results):
        return EXIT_BLOCKED
    if any(st == "failed" for _, st, _ in results):
        return 1
    return 0


def run_step(step, project, model, provider, gemini_review, dry_run):
    thinking = EFFORT_TO_THINKING.get(step["effort"], "medium")
    prompt = build_prompt(step)
    cmd = [
        "pi", "--provider", provider, "--model", model,
        "--thinking", thinking, "--print", prompt,
    ]
    print(f"\n=== Step {step['num']} [{step['effort']} -> thinking={thinking}] ===")
    print(f"    {step['desc']}")
    if dry_run:
        print("    (dry-run: not executed)")
        return 0

    proc = subprocess.run(cmd, cwd=project)
    if proc.returncode != 0:
        return proc.returncode

    if is_blocked(project):
        print(f"\nStep {step['num']} is BLOCKED — implementer left a question in .ai/BLOCKED.md")
        return EXIT_BLOCKED

    if gemini_review:
        gemini_cmd = os.environ.get("GEMINI_CMD", "gemini --yolo -p")
        review_prompt = build_review_prompt(step, project)
        print(f"\n--- Gemini review for step {step['num']} ---")
        review_proc = subprocess.run(
            gemini_cmd.split() + [review_prompt], cwd=project
        )
        if review_proc.returncode != 0:
            print("(gemini review failed — continuing anyway)")

    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", help="project dir containing .ai/STATE.md")
    ap.add_argument("--step", type=int, help="run only this step number")
    ap.add_argument("--model", default="kimi-code")
    ap.add_argument("--provider", default="kimi")
    ap.add_argument("--gemini-review", action="store_true",
                    help="run gemini after each step to verify the diff")
    ap.add_argument("--parallel", action="store_true",
                    help="run independent steps in parallel, one worktree+branch "
                         "each, routed by per-step agent (see docs/parallel.md)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    project = pathlib.Path(args.project).expanduser().resolve()
    state = project / ".ai" / "STATE.md"
    if not state.is_file():
        sys.exit(f"No .ai/STATE.md in {project} — run orchestra-plan first.")

    steps = parse_steps(state.read_text())
    todo = [s for s in steps if s["executor"] == "implementer" and not s["done"]]
    if args.step is not None:
        todo = [s for s in todo if s["num"] == args.step]

    skipped = [s for s in steps if s["executor"] != "implementer"]
    if skipped:
        nums = ", ".join(str(s["num"]) for s in skipped)
        print(f"Skipping non-implementer steps (handled by human/Claude): {nums}")
    if not todo:
        sys.exit("No implementer steps to run.")

    print(f"Project: {project}")
    print(f"Model:   {args.provider}/{args.model}")
    if args.gemini_review:
        print(f"Gemini review: enabled")

    if args.parallel:
        if args.dry_run:
            for s in todo:
                agent = (s["agent"] or DEFAULT_AGENT).lower()
                print(f"  (dry-run) step {s['num']} -> {agent}: {s['desc']}")
            return
        rc = run_parallel(todo, str(project), args.provider, args.model)
        if rc == EXIT_BLOCKED:
            sys.exit(EXIT_BLOCKED)
        if rc != 0:
            sys.exit(f"\nParallel dispatch had failures (code {rc}). "
                     "Stopping for human review.")
        print("\nAll parallel steps dispatched to feat/<feature>--sN branches. "
              "Next: audit + merge on the orchestrator.")
        return

    print(f"Running {len(todo)} implementer step(s) sequentially.")

    for s in todo:
        rc = run_step(s, str(project), args.model, args.provider,
                      args.gemini_review, args.dry_run)
        if rc == EXIT_BLOCKED:
            sys.exit(EXIT_BLOCKED)
        if rc != 0:
            sys.exit(f"\nStep {s['num']} exited with code {rc}. Stopping for human review.")

    print("\nAll implementer steps dispatched. Next: audit the diff (orchestra-audit).")


if __name__ == "__main__":
    main()
