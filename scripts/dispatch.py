#!/usr/bin/env python3
"""dispatch.py — run the implementer steps of an orchestra plan through Pi.

Reads <project>/.ai/STATE.md, then runs each unchecked `executor: implementer`
step through Pi (headless, agentic) against the configured provider/model.
Steps run sequentially — no parallel provider spam (flow.md step 4).

Audit and the plan/push gates are NOT this script's job: the human (or Claude
wearing the reviewer hat) gates the plan before dispatch and audits the diff
after. This script only drives the implementer.

Usage:
  dispatch.py <project-dir> [--step N] [--model gemma-31b] [--provider cliproxy]
              [--dry-run]

Examples:
  dispatch.py ~/Developer/personal-assistant            # run all implementer steps
  dispatch.py ~/Developer/personal-assistant --step 4   # run only Step 4
  dispatch.py ~/Developer/personal-assistant --dry-run  # show plan, run nothing
"""
import argparse
import pathlib
import re
import subprocess
import sys

EFFORT_TO_THINKING = {"low": "low", "standard": "medium", "high": "high"}

STEP_RE = re.compile(r"^- \[( |x)\] (Step (\d+):.*)$")
FIELD_RE = re.compile(r"^\s*(executor|effort):\s*(\S+)")


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
        "First read .ai/STATE.md and the relevant design files under docs-md/ "
        "for the goal, constraints, and files in scope.\n\n"
        f"Execute ONLY this step, nothing else:\n\n  {step['desc']}\n\n"
        "Follow the constraints in STATE.md and the project's CLAUDE.md/AGENTS.md.\n\n"
        "Plan-execution discipline (follow exactly):\n"
        "1. Do this one step only. Do not start, peek at, or 'prepare for' other steps.\n"
        "2. Stay surgical: change only what THIS step requires. No refactors, "
        "renames, or cleanups the step didn't ask for.\n"
        "3. Write tests before production code where the step calls for it, "
        "then VERIFY: run the tests/build and confirm they pass before declaring done. "
        "If you cannot verify, say so explicitly.\n"
        "4. If the step is ambiguous, blocked, or needs a decision that is NOT in "
        "the plan, STOP and report what's missing — do not guess or invent scope.\n\n"
        "When finished, print a one-paragraph summary of exactly which files you "
        "created or changed, and the result of the verification you ran."
    )


def run_step(step, project, model, provider, dry_run):
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
    return proc.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", help="project dir containing .ai/STATE.md")
    ap.add_argument("--step", type=int, help="run only this step number")
    ap.add_argument("--model", default="gemma-31b")
    ap.add_argument("--provider", default="cliproxy")
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
    print(f"Running {len(todo)} implementer step(s) sequentially.")

    for s in todo:
        rc = run_step(s, str(project), args.model, args.provider, args.dry_run)
        if rc != 0:
            sys.exit(f"\nStep {s['num']} exited with code {rc}. Stopping for human review.")

    print("\nAll implementer steps dispatched. Next: audit the diff (orchestra-audit).")


if __name__ == "__main__":
    main()
