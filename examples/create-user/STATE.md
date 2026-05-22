# Current Task

# Goal
Build a `POST /users` signup endpoint per docs-md/create-user/.

# Constraints
- Argon2id only (no bcrypt fallback)
- Password never returned or logged
- HttpOnly Secure SameSite=Lax cookie
- 10 KB body size limit
- Rate limit at middleware layer (5 / IP / hour)
- Atomic transaction for user + session insert

# Files in scope
- src/routes/users.ts  (new)
- src/lib/hash.ts      (new — argon2id wrapper)
- src/lib/session.ts   (new — token mint + store)
- src/db/migrations/0001_create_users_and_sessions.sql  (new)
- src/middleware/rate-limit.ts  (existing — verify signup route is covered)
- tests/routes/users.test.ts  (new)
- tests/lib/hash.test.ts  (new)

# Plan
- [ ] Step 1: Write migration 0001
      executor: implementer
      effort: low
- [ ] Step 2: Write src/lib/hash.ts (argon2id wrap)
      executor: implementer
      effort: low
- [ ] Step 3: Write src/lib/session.ts (token mint + DB store)
      executor: implementer
      effort: standard
- [ ] Step 4: Write tests/routes/users.test.ts from test-spec.md
      executor: implementer
      effort: standard
- [ ] Step 5: Write src/routes/users.ts to pass all tests
      executor: implementer
      effort: standard
- [ ] Step 6: Verify rate-limit middleware covers /users
      executor: implementer
      effort: low
- [ ] Step 7: Deep review of hot paths (hashing, session, transaction)
      executor: me
      effort: audit-only
- [ ] Step 8: Draft changelog entry
      executor: secretary
      effort: low
- [ ] Step 9: Pre-push audit (vbsec + AI-footprint)
      executor: me
      effort: audit-only
- [ ] Step 10: Push to feature branch `feat/create-user`
      executor: secretary
      effort: low

# Decisions
- 2026-05-22: chose argon2id over bcrypt (memory-hard resistance to GPU cracking)
- 2026-05-22: session token returned in BOTH cookie and body — needed for native mobile clients
- 2026-05-22: explicit 409 on duplicate email (over 400) for client UX clarity, mitigated by rate limit

# Open questions
- (none — all resolved at plan time)
