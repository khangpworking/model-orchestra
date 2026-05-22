# Current Task

_None active. This file is overwritten when a new task begins._

## How this file works

- Planner owns this file
- Each task: clears the file, writes goal/plan/executors/effort/constraints
- Implementer reads this file + `docs-md/<feature>/` before working
- Implementers write progress to `.ai/scratchpad/<name>.md` (gitignored)
- Planner merges scratchpad updates back into STATE.md

## Template

```
# Goal
<one sentence>

# Constraints
- pulled from project rules

# Files in scope
- src/...

# Plan
- [ ] Step 1: <description>
      executor: <planner | implementer | secretary | me>
      effort: <low | standard | high | audit-only>
- [ ] Step 2: ...

# Decisions
- (append-only)

# Open questions
- (TBD items)
```
