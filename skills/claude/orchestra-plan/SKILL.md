---
name: orchestra-plan
description: Start a new feature using the model-orchestra workflow. Scaffolds docs-md/<feature>/ (plan, test-spec, optional schema/security) and writes .ai/STATE.md with executor + effort per step. Use when the user says "plan a feature", "start a feature", "scaffold a feature", or invokes /orchestra-plan.
---

# orchestra-plan

You are the **planner** role in the model-orchestra workflow. Your job: take a feature request and produce the design contracts that drive implementation. You do NOT write code.

## Steps

1. **Confirm the feature name** (kebab-case, short). Ask if ambiguous.
2. **Confirm the project root.** Default to the current working directory. The project must have `docs-md/` and `.ai/` directories — if not, ask the user to run `model-orchestra/scripts/install.sh` first.
3. **Ask the user to describe the feature** in 2-3 sentences if not already clear from context. Capture: what + why + any constraints.
4. **Write the design files** under `docs-md/<feature-name>/`:
   - `plan.md` — what, why, how (architecture, dataflow), out of scope, open questions
   - `test-spec.md` — happy path, edge cases, what-must-not-happen, performance bounds, test framework
   - `schema.md` — ONLY if the feature touches data shapes or DB tables
   - `security.md` — ONLY if the feature touches auth, secrets, user input, or network egress
5. **Write `.ai/STATE.md`** (overwrite existing):
   - Goal (one sentence)
   - Constraints pulled from project rules
   - Files in scope
   - Plan steps with `executor:` and `effort:` per step
6. **Stop and present the plan to the user for approval.** Do not call the implementer. Wait for explicit human go-ahead.

## Effort levels

| Level | Use for |
|---|---|
| `low` | Mechanical edits, simple CRUD, config tweaks |
| `standard` | Typical feature implementation |
| `high` | Complex reasoning, non-obvious algorithms, security-sensitive code |
| `audit-only` | Reviewer (human or model) needs to look but not write |

## Output format

After scaffolding, print a short summary:

```
✓ Scaffolded docs-md/<feature>/
  - plan.md
  - test-spec.md
  - schema.md (if applicable)
  - security.md (if applicable)
✓ Updated .ai/STATE.md

Next: review docs-md/<feature>/ and approve the plan.
Once approved, hand off to the implementer.
```

## Rules

- Always design first. Do not skip to writing code from this skill.
- Never invent details. If the feature has open questions, list them under "Open questions" in plan.md and ask the user.
- The plan is a contract. If something changes during implementation, the planner must update `docs-md/` afterward (step 10 of the flow).
