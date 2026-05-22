# Example: `create-user` feature

A complete walked-through example of the model-orchestra design phase for a typical feature: a `POST /users` API endpoint.

This shows what the four design files look like *before any code is written*. It is the artifact you should hand to your implementer.

## Files

- [`plan.md`](plan.md) — what + why + how
- [`test-spec.md`](test-spec.md) — happy path, edge cases, what must not happen
- [`schema.md`](schema.md) — request/response shapes + DB table
- [`security.md`](security.md) — threats and guards
- [`STATE.md`](STATE.md) — the `.ai/STATE.md` snapshot at planning time

## How this would be used

1. Planner produces these files
2. Human reviews → approves
3. Implementer reads all 5 files, writes tests from `test-spec.md`, then writes code to pass them
4. Reviewer + secretary follow the rest of the flow
