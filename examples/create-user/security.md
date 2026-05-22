# Security: create-user

## Threats

| # | Threat | Impact | Mitigation |
|---|---|---|---|
| T1 | Password cracking via offline attack on stolen DB | Account takeover | argon2id with memory 64 MiB / iter 3 |
| T2 | Account enumeration via signup endpoint | User PII leak | Same 400/409 status on duplicate as on validation error? **No — explicit 409 for usability; rate-limit instead** |
| T3 | Mass signup / spam accounts | Resource exhaustion + abuse | Global rate limit middleware: 5 signups / IP / hour |
| T4 | Session token leak via XSS | Account takeover | HttpOnly cookie; only also return in body for native clients |
| T5 | Session token leak via referer / logs | Account takeover | Never log full token; store SHA-256 hash, not raw |
| T6 | Oversized request DoS | Memory exhaustion | 10 KB max JSON body |
| T7 | Slow Argon2 → request pile-up | Latency / DoS | Per-IP rate limit + concurrency cap on signup route |
| T8 | Timing attack on email lookup | Account enumeration | Use constant-time SQL lookup or skip — duplicate already returns 409 |
| T9 | CSRF on signup | Cross-site forced signup | SameSite=Lax cookie + check Origin header |

## Guards (checklist for implementer)

- [ ] Zod schema validates ALL fields before any DB call
- [ ] Body size limit enforced at HTTP layer (10 KB)
- [ ] argon2id hashing only — no fallback
- [ ] Password never logged, never returned, never stored raw
- [ ] Session token: random via `crypto.randomBytes(32)`, hex-encoded; only the SHA-256 hash stored
- [ ] Atomic transaction: user insert + session insert succeed together or both roll back
- [ ] Cookie flags: `HttpOnly; Secure; SameSite=Lax; Path=/`
- [ ] Rate limit applied (5 / IP / hour)
- [ ] Origin header check for CSRF

## Audit notes

- Argon2id parameters chosen for ~250ms latency on a 1 vCPU server. Re-tune if hardware changes.
- If sessions table grows large, add a cleanup job for expired rows (out of scope for v1).
- Email lowercasing happens at write AND at lookup — both must use the same normalization.
