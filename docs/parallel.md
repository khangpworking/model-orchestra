# Parallel dispatch

The base distributed flow ([distributed.md](distributed.md)) runs a branch's
implementer steps **sequentially**. This doc describes how the worker runs
independent steps **in parallel**, each on its own git worktree and branch,
routed to a per-step agent.

It does not change the gates: the planner still plans, the human still approves,
and the **audit + merge stay on the orchestrator**.

## When to use it

Parallel dispatch only pays off when steps are genuinely independent. The
planner decides this at plan time, and the rule is strict:

- **File-disjoint.** No two parallel steps may touch the same file. This is what
  makes the later merge conflict-free.
- **No data dependency.** A parallel step must not need the output of another
  step in the same batch.

Steps that depend on each other go in a *later* dispatch (or a later batch), not
the same parallel run. There is deliberately **no dependency-DAG scheduler** —
ordering is expressed by putting dependent work in a separate, sequential
dispatch.

## Marker

`.ai/DISPATCH.md` gains a `mode` field:

```
branch: feat/<feature>
steps: 1,2,3
mode: parallel        # parallel | sequential (default)
status: requested
```

`status` is the **aggregate** over all parallel tasks: `running` while any task
runs, `done` only if every task succeeded, `failed` if any failed, `blocked` if
any task left a `.ai/BLOCKED.md`.

## Per-step agent routing

Each step in `.ai/STATE.md` may carry an `agent:` field naming the concrete tool
that runs it. If omitted, the default agent is used.

```
- [ ] Step 1: Write the migration
      executor: implementer
      agent: kimi
      effort: low
- [ ] Step 2: Write the API docs
      executor: implementer
      agent: gemini
      effort: low
```

Supported agents (override the command for any of them via env):

| agent           | default command            | env override |
|-----------------|----------------------------|--------------|
| `kimi` (default)| `pi --provider … --model …`| `--provider`/`--model` flags |
| `gemma`         | `pi --provider cliproxy …` | — |
| `gemini`        | `gemini --yolo -p`         | `GEMINI_CMD` |
| `claude`        | `claude -p`                | `CLAUDE_CMD` |

`executor:` stays role-level (`implementer` / `me` / …); `agent:` is the
model/tool that does an implementer step. Only `implementer` steps are
dispatched — `me` / `planner` / `secretary` steps stay on the orchestrator.

## Worktree fan-out

For each parallel task the worker:

1. Forks a fresh branch `feat/<feature>--s<N>` from the plan branch HEAD into a
   throwaway git **worktree** (a separate directory sharing the one `.git`).
2. Runs the step's agent in that worktree. The agent reads `AGENTS.md` and
   `.ai/STATE.md` exactly as in the sequential flow.
3. Commits the result in the worktree and pushes `feat/<feature>--s<N>`.
4. Removes the worktree.

Worktrees isolate concurrent file writes — each agent has its own working
directory, so two agents writing at once never clobber each other on disk.

### TOS-safe concurrency

Tasks are grouped by agent. Different agents run **in parallel**; tasks sharing
one agent run **sequentially** within that agent's group. This honours the base
rule (no parallel calls to a single provider — TOS + rate-limit risk) while
still parallelising across providers.

So three tasks on `kimi`, `gemini`, `kimi` run as: the `gemini` task alongside
the *first* `kimi` task, then the *second* `kimi` task after the first finishes.

## Branch lifecycle

The `feat/<feature>--s<N>` branches are **ephemeral, machine-owned** fan-out
branches. The worker may force-push or delete them freely on re-run. They are
not shared feature branches, so the "never force-push" invariant does not apply
to them.

The **feature branch** (`feat/<feature>`) is still never force-pushed. The
orchestrator integrates the `--sN` branches into it:

```
git fetch origin
for b in $(git branch -r --list 'origin/feat/<feature>--s*'); do
  git merge --no-ff "$b"      # conflict-free: steps are file-disjoint
done
```

Audit happens before the merge, per the unchanged invariant: distribution moves
*labor*, never the *gate*.

## Invariants (unchanged)

- Source of truth is git; the worker holds nothing permanent.
- The audit gate runs on the orchestrator, after the worker pushes.
- Push to feature branches only; the feature branch is never force-pushed.
- The webhook secret is verified before any worker action.
