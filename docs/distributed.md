# Distributed execution

The base flow ([flow.md](flow.md)) describes *what* each role does. This doc
describes *where* each role runs when you split them across more than one
machine.

## Why split machines at all

Roles are processes; the models they call are usually remote (a proxy or a
hosted API). So a role's local cost is the **agent runtime**, not the model.
That means you can move a role to a different machine purely for resources —
more RAM, a spare box, an idle laptop — without moving any model.

Two situations make this worth doing:

- The orchestrator box is resource-starved and OOM-kills a second agent runtime
  at startup, even though the model itself is remote.
- You have a beefier or simply idle machine that can run the implementer faster.

## Topology: orchestrator + disposable worker

Split the four roles across two node types.

```
  ┌─────────────────────────┐         git          ┌──────────────────────────┐
  │   ORCHESTRATOR NODE      │   (truth + trigger)  │      WORKER NODE          │
  │   always-on, holds state │ ───────────────────► │   disposable compute      │
  │                          │ ◄─────────────────── │                           │
  │  • Planner               │   plan branch out    │  • Implementer            │
  │  • Reviewer (audit gate) │   result branch in   │  • optional 2nd reviewer  │
  │  • Secretary (push)      │                      │    model                  │
  └─────────────────────────┘                      └──────────────────────────┘
```

**Orchestrator node** — always-on. Holds the repo as source of truth, runs the
plan gate, runs the pre-push audit, owns the push to the feature branch. Never
disposable.

**Worker node** — disposable compute. Runs the implementer (the file-writing).
Holds nothing permanent: no secret, no database, no service another machine
depends on. If it vanishes, you lose a worker, not data.

The split is deliberate: planning and the audit gate are *judgment* and stay
where the trust and the source of truth live; implementation is *labor* and goes
wherever there's capacity.

## Channels

### Git is both the code channel and the trigger

Code never travels over a chat surface. The orchestrator pushes a plan branch;
the worker reads that branch and writes a result branch. Git carries the bytes.

Do **not** design around bot-to-bot chat messaging to kick the worker — most
platforms (Telegram included) block bots from receiving messages sent by other
bots, so a "planner bot pings worker bot" trigger silently never fires. Use git
as the trigger instead.

### The dispatch marker

A small committed file is the trigger payload. Keep it minimal:

```
# .ai/DISPATCH.md
branch: feat/<feature>
steps: 4,5          # which STATE.md steps the worker should run
status: requested   # requested | running | done | failed
```

The worker flips `status` as it goes and commits the change back, so the
orchestrator can see progress from git alone.

## Trigger: webhook vs poll

Two ways the worker learns a dispatch exists.

**Webhook (push, instant).** The orchestrator pushes the marker; the git host
fires a webhook through a tunnel to a small endpoint on the worker, which kicks
off the run. Instant. Cost: the worker exposes a persistent inbound endpoint —
acceptable on a machine you control, a real surface to think about on a borrowed
one.

A minimal worker-side receiver (sketch — adapt to the worker's stack):

```
POST /dispatch  ──► verify the webhook secret
                ──► git fetch + checkout the marker's branch
                ──► read .ai/DISPATCH.md, set status: running, push
                ──► run scripts/dispatch.py for the listed steps
                ──► set status: done|failed, push result branch
                ──► notify the human (the worker's own chat, not the orchestrator's)
```

Always verify the webhook secret before acting — an unauthenticated dispatch
endpoint is a remote code-execution hole.

**Poll (pull, simple).** The worker runs a scheduled job that fetches and checks
for a marker with `status: requested`. No inbound endpoint. Cost: latency equal
to the poll interval. Prefer this when the worker shouldn't expose anything.

## Invariants

These keep a distributed run safe and reversible:

- **Source of truth is git, never the worker's disk.** The worker reads a
  branch and writes a branch; it is never the only copy of anything.
- **The worker is stateless and disposable.** No secret, no service dependency,
  no permanent data. Losing it costs a worker, not the project.
- **Push to feature branches only**, from either node. Never main, never
  force-push — same rule as the single-machine secretary.
- **The audit gate runs on the orchestrator**, after the worker pushes, before
  anything merges. Distribution moves *labor*, never the *gate*.
- **Verify webhook authenticity** before any worker action.
