# Plan: create-user

## What

A `POST /users` API endpoint that registers a new user account. Accepts email + password + display name, returns a user record (without the password hash) plus a session token.

## Why

First-touch authentication. Required before any user-scoped feature can be built (profiles, settings, etc).

## How

- Route: `POST /users`
- Validation layer: zod schema (email format, password ≥12 chars, name 1-64 chars)
- Password hashing: argon2id (parameters: memory 64 MiB, iterations 3, parallelism 1)
- Persistence: insert into `users` table with `email` unique constraint
- Session: issue a 256-bit random session token, store hash in `sessions` table, set HTTP-only Secure SameSite=Lax cookie
- Response: 201 with `{ user: {id, email, name, created_at}, sessionToken: "..." }`

## Out of scope

- Email verification flow (separate feature)
- Password reset (separate feature)
- OAuth / social login (separate feature)
- Rate limiting at the route level (handled by global middleware)

## Open questions

- Do we want a username separate from display name? Decision: no — display name only for v1.
- Should the session token also be returned in the response body or cookie-only? Decision: both for v1 (some clients are mobile and need the token explicitly).
