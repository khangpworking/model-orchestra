# The Flow

Detailed walkthrough of the 10-step model-orchestra pattern.

## Roles

The pattern uses four roles. A single model can wear multiple hats; most teams use 2-3 models with one role each plus the human as final reviewer.

### Planner
- Designs features end-to-end before any code is written
- Writes `docs-md/<feature>/plan.md`, `test-spec.md`, optionally `schema.md`
- Updates `.ai/STATE.md` with steps, executor assignments, and effort levels
- Updates docs after implementation if design evolved

Good fit: large-context, reasoning-strong models.

### Implementer
- Writes tests from the test spec first
- Writes production code to pass tests
- Sequential calls only — no parallel spam (provider TOS risk + rate limits)
- Retries up to 3 times on bug; escalates to human on failure

Good fit: code-strong models with long context.

### Reviewer
- Verifies test pass + lint on every diff
- Reads diffs in scope
- Deep-reads hot paths only (auth, money, schema, ingest, secrets)
- Runs pre-push audit (security + AI-footprint)

Good fit: the human, or a high-precision reasoning model the human trusts.

### Secretary
- Drafts changelogs
- Adds WHY-comments sparingly (default: no comments)
- Pushes to feature branch only after reviewer approval

Good fit: small/fast/cheap models — this is mechanical work.

## The 10 steps

### 1. Human gives task

Plain description. The smaller the task, the smaller the overhead — for one-line tweaks, skip the protocol.

### 2. Planner writes design

Create `docs-md/<feature>/`:
- `plan.md` — what + why + how (architecture, dataflow)
- `test-spec.md` — inputs, outputs, edge cases, what should NOT happen
- `schema.md` — data shapes (if relevant)
- `security.md` — threats, guards, audit notes (if relevant)

Create or overwrite `.ai/STATE.md`:
- Goal (one sentence)
- Files in scope
- Plan with `executor:` and `effort:` per step
- Constraints pulled from project rules

### 3. Human approves plan ← gate

Cheapest place to catch misalignment. If the plan is wrong, fixing it before any code is written costs minutes; fixing it after costs hours.

### 4. Implementer writes code

- Read `docs-md/<feature>/` and `.ai/STATE.md` first
- Write unit tests from test spec
- Write production code to pass tests
- Sequential calls; add 1-2s jitter between provider hits if calling the same provider in a loop

### 5. Reviewer verifies diffs

- Tests pass + lint clean
- Diff is in scope (no out-of-band changes)
- Deep-read hot paths
- Run vbsec or similar security scan

### 6. Bug loop

- Implementer retries 3 times max
- Still broken → human fixes manually

This limit matters — letting an implementer model loop indefinitely on a stuck bug burns tokens and rarely converges.

### 7. Secretary drafts changelog

- One-line summary per logical change
- WHY notes for non-obvious decisions
- Default: no inline code comments (the diff is the doc)

### 8. Reviewer pre-push audit

**Security gate:**
- Run a vulnerability scanner (e.g. [vbsec](https://github.com/tanviet12/vbsec))
- Manual check: no secrets in code, raw SQL only on server-constant strings, SSRF guards intact, auth checks present

**AI-footprint scrub:**
- No `Co-Authored-By: <AI-model>` lines
- No "Generated with ..." or marketing tags in commits
- No model names in code comments
- No em-dashes (if project style avoids them)
- No emoji bullet lists in production prose

Either gate fails → push blocked. Fix and re-audit.

### 9. Secretary pushes to feature branch

- Never to main/master/trunk
- Never force-push, amend, or rebase published commits
- Push only after explicit reviewer approval

### 10. Planner updates docs

If implementation revealed design changes, update `docs-md/<feature>/`. The docs are the contract — drift kills the system.

## Why it works

- Context windows stay small per role → cheap + accurate
- Role specialization matches model strengths
- Human gate on plan = cheapest misalignment catch
- Cross-model review catches single-model echo-chamber bugs
- Pre-push audit keeps repos clean and secure

## What this is NOT

- Not a model-selection guide — pick whatever fits each role
- Not a CI/CD pipeline — those are project-specific
- Not auto-enforced — phase 2 ships a pre-push hook

## Anti-patterns to avoid

- Skipping the plan gate to "save time"
- Parallel calls to the same provider (TOS risk + rate limits)
- Force-push or rebase on shared branches
- AI-marketing comments and commit metadata
- Documenting AFTER instead of BEFORE
