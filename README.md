# model-orchestra

A reusable orchestration pattern for multi-model AI development workflows.

Designed for teams using two or more LLMs in handoff — a planner model that designs, an implementer model that writes code, and a secretary model that maintains hygiene (commits, changelogs, pushes). The pattern is model-agnostic: swap in any LLMs that fit each role.

Core idea: **disk is memory, model is compute.** Permanent feature designs live in `docs-md/`. Ephemeral task state lives in `.ai/STATE.md`. Models come and go; files persist.

## The flow

1. Human gives task
2. **Planner** writes `docs-md/<feature>/` (plan + test spec + schema) and `.ai/STATE.md` (steps, executor, effort)
3. Human reviews & approves plan ← gate
4. **Implementer** writes tests from spec, then production code (sequential calls only — no parallel spam)
5. **Reviewer** verifies diffs in scope, deep-reads hot paths (auth, money, schema, secrets)
6. Bug? Implementer retries up to 3x. Still broken → human steps in.
7. **Secretary** drafts changelog, optionally adds WHY-comments (default to no comments)
8. **Reviewer runs pre-push audit:**
   - Security scan (e.g. [vbsec](https://github.com/tanviet12/vbsec))
   - AI-footprint scrub (no Co-Authored-By, no generic "Generated with X" tags, no model-name comments)
   - Either fails → push blocked
9. **Secretary** pushes to **feature branch only** (never main, never force-push)
10. **Planner** updates `docs-md/` if design evolved

See [docs/flow.md](docs/flow.md) for the full role + step reference.

## Install

In a new project:

```bash
git clone https://github.com/khangpworking/model-orchestra ~/model-orchestra
~/model-orchestra/scripts/install.sh /path/to/your/project
```

This drops the templates into your project and appends to `.gitignore`.

## What's NOT included

- Specific model choices — that's your stack decision
- API keys, prompts, agent configs
- A test runner — your project picks its own

## Status

MVP. Phase 2 ships: Claude Code skills (`/orchestra-plan`, `/orchestra-audit`), a pre-push hook that enforces the security gate, and worked examples.

## License

MIT
