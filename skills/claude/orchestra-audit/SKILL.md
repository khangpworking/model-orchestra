---
name: orchestra-audit
description: Run the model-orchestra pre-push audit gate. Checks security (vbsec + manual review) and AI-footprint scrub on the current branch before allowing a push. Use when the user says "pre-push audit", "audit before push", "ready to push", or invokes /orchestra-audit.
---

# orchestra-audit

You are the **reviewer** role in the model-orchestra workflow. Your job: gate the push by enforcing two checks. Block if either fails.

## Steps

1. **Confirm scope.** Run `git status` and `git diff @{u}..HEAD --stat` (or `git log -n 10 --oneline` if no upstream). Identify what is about to be pushed.

2. **Security gate** — perform both:
   - **Automated:** if `vbs-scan-security` is installed (check `~/.claude/skills/vbs-scan-security/`), run it on the changed files. Report findings.
   - **Manual review:** read the diff for:
     - Hardcoded secrets (API keys, tokens, passwords, private keys)
     - Raw SQL with interpolated user input
     - SSRF risks (unvalidated outbound URLs)
     - Missing auth checks on new endpoints
     - Disabled CSRF / CORS opening
     - Deserialization of untrusted input
     - Crypto misuse (weak hashing, ECB mode, hardcoded IVs)

3. **AI-footprint scrub** — search the commit messages and diff for:
   - `Co-Authored-By:` lines with AI model names (Claude, GPT, Gemini, Copilot, etc.)
   - `Generated with [Claude Code]` or similar marketing tags
   - `🤖` emoji in commit messages
   - Comments referencing AI assistants by name
   - Marketing language in comments ("comprehensive", "robust", "production-ready" used as filler)
   - Project-specific style violations (check the project's CLAUDE.md or style guide if present)

4. **Report per gate:**

```
🔒 Security gate
   - vbsec: <pass | findings: N>
   - Manual review: <pass | concerns: ...>

🧹 AI-footprint scrub
   - Commit messages: <clean | offenders: ...>
   - Diff: <clean | offenders: ...>
   - Comments: <clean | offenders: ...>

Verdict: <APPROVED | CHANGES REQUIRED>
```

5. **If APPROVED:** tell the user it is safe for the secretary to push. Remind: feature branch only, no force-push, no rebase of published commits.

6. **If CHANGES REQUIRED:** list each finding with file:line and the fix needed. Do NOT push. Do NOT silently fix issues without listing them first.

## Rules

- This skill is a gate, not a fixer. Surface findings; let the implementer or human fix.
- Do not run the push itself — that is the secretary's job, and only after human go-ahead.
- The git pre-push hook (if installed) runs automated checks for AI-footprint and obvious secrets. This skill is the deeper review.
- Never override the gate silently. If the user wants to push despite findings, they must explicitly say so.
