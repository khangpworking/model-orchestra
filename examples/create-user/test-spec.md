# Test Spec: create-user

## Happy path

### Test: valid signup creates user and returns session

- Input: `{ email: "alice@example.com", password: "correcthorsebattery", name: "Alice" }`
- Expected:
  - Response: `201` with body `{ user: { id, email, name, created_at }, sessionToken: <64-char hex> }`
  - DB: one row in `users` with the email, `password_hash` starts with `$argon2id$`
  - DB: one row in `sessions` linked to the new user
  - Cookie: `session=<token>; HttpOnly; Secure; SameSite=Lax`

## Edge cases

### Test: duplicate email returns 409

- Input: same email as an existing user
- Expected: `409 Conflict` with `{ error: "email_in_use" }`. No new row in `users`. No session created.

### Test: weak password rejected

- Input: password length < 12
- Expected: `400 Bad Request` with `{ error: "validation_error", fields: { password: "min_length_12" } }`

### Test: invalid email format rejected

- Input: `email: "not-an-email"`
- Expected: `400` with `fields: { email: "invalid_email" }`

### Test: missing fields rejected

- Input: empty body
- Expected: `400` with all required fields listed in `fields`

### Test: oversized name rejected

- Input: `name` length > 64
- Expected: `400` with `fields: { name: "max_length_64" }`

## What should NOT happen

- The endpoint MUST NOT return the password hash in the response
- The endpoint MUST NOT log the raw password
- The endpoint MUST NOT use a fast hash like SHA-256 or bcrypt with default cost — argon2id only
- The endpoint MUST NOT accept JSON bodies larger than 10 KB
- The endpoint MUST NOT issue a session if the user row insert fails (atomic transaction)

## Performance / non-functional

- p95 latency ≤ 300ms under nominal load (argon2id dominates)
- Should handle 50 concurrent signups without race-condition double-inserts

## Test framework

This project uses: `vitest`. Run with `pnpm test`. Database tests use a per-test SQLite tmpfile.
