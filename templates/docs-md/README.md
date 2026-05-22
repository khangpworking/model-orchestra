# docs-md/

Per-feature design docs. Permanent project artifacts — committed to git.

## Convention

```
docs-md/
├── README.md            ← this file
├── <feature-name>/
│   ├── plan.md          ← what + why + how
│   ├── test-spec.md     ← inputs, outputs, edge cases
│   ├── schema.md        ← data shapes (if relevant)
│   ├── routes.md        ← API contract (if relevant)
│   └── security.md      ← threats, guards (if relevant)
```

A `_feature/` skeleton directory is provided — copy it to start a new feature.

## Rules

1. **Docs exist before code.** Design first, implement second.
2. **One folder per feature/domain.** Keep scope narrow.
3. **Update docs after implementation.** Drift kills the system.
4. **No conversation transcripts.** Designs only.
5. **No secrets.** Ever.

## Difference from `.ai/STATE.md`

| | `docs-md/` | `.ai/STATE.md` |
|---|---|---|
| Lifespan | Permanent | Per-task, wiped |
| Owner | Whole team | Planner |
| Committed to git | Yes | No (gitignored) |
| Content | Design contracts | Current checklist |
