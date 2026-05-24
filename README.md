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

# Scaffolding only
~/model-orchestra/scripts/install.sh /path/to/your/project

# Or scaffolding + pre-push hook (recommended)
~/model-orchestra/scripts/install.sh /path/to/your/project --hook
```

This drops templates into your project, appends to `.gitignore`, and (with `--hook`) symlinks a pre-push gate that scans for AI-footprint markers and obvious secrets.

### Claude Code skills

Two slash commands ship in `skills/claude/`:

```bash
ln -s ~/model-orchestra/skills/claude/* ~/.claude/skills/
```

- `/orchestra-plan` — planner role. Scaffolds `docs-md/<feature>/` design files and `.ai/STATE.md` from a feature request.
- `/orchestra-audit` — reviewer role. Runs the pre-push security + AI-footprint gate.

### Recommended companion skills

Not bundled with this repo, but they pair well with the flow:

- [`prompt-master`](https://github.com/nidhinjs/prompt-master) — sharpens cross-model prompts. Use it when the planner briefs the implementer (or any handoff between models with different prompting styles). Profiles for Claude, GPT/Codex, Gemini, Kimi K2, Cursor, and 20+ others.
- [`semble`](https://github.com/MinishLab/semble) — semantic code search via MCP. Drop-in for any agent that supports MCP servers. Use when the planner or reviewer needs to find code by meaning ("where is X handled") rather than by exact symbol. Falls back to `grep` for known-string lookups.

## Pre-push hook

The hook enforces what a git hook can:

1. AI-footprint scrub — blocks `Co-Authored-By: <AI>`, `Generated with X`, `🤖`, etc. in commit messages and diff
2. Secret pattern scan — basic regex for AWS keys, OpenAI/Anthropic/Google tokens, private keys, `api_key = "..."` patterns
3. Reminder to run `/vbs-scan-security` (interactive — cannot auto-fire from a hook)

Override with `git push --no-verify` if needed. Use sparingly.

## Worked example

See [`examples/create-user/`](examples/create-user/) — full design contract for a typical `POST /users` signup endpoint, including plan, test spec, schema, security analysis, and `.ai/STATE.md`.

## What's NOT included

- Specific model choices — that's your stack decision
- API keys, prompts, agent configs
- A test runner — your project picks its own

## License

MIT
