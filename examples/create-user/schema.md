# Schema: create-user

## Request shape

```typescript
type CreateUserRequest = {
  email: string;          // RFC 5322, max 254 chars
  password: string;       // min 12, max 256
  name: string;           // min 1, max 64
}
```

## Response shape (201)

```typescript
type CreateUserResponse = {
  user: {
    id: string;           // UUID v4
    email: string;
    name: string;
    created_at: string;   // ISO 8601
  };
  sessionToken: string;   // 64-char hex
}
```

## Error responses

```typescript
type ErrorResponse =
  | { error: "validation_error"; fields: Record<string, string> }
  | { error: "email_in_use" }
  | { error: "internal" };
```

## DB tables

### `users`

| column | type | notes |
|---|---|---|
| id | TEXT | PRIMARY KEY, UUID v4 |
| email | TEXT | UNIQUE NOT NULL, lowercased |
| password_hash | TEXT | NOT NULL, argon2id encoded |
| name | TEXT | NOT NULL |
| created_at | TEXT | NOT NULL, ISO 8601, DEFAULT (datetime('now')) |

Index: `idx_users_email_unique` on `email`.

### `sessions`

| column | type | notes |
|---|---|---|
| token_hash | TEXT | PRIMARY KEY, SHA-256 of the token |
| user_id | TEXT | NOT NULL, FK → users.id |
| created_at | TEXT | NOT NULL |
| expires_at | TEXT | NOT NULL, default 30 days |

Index: `idx_sessions_user` on `user_id`.

## Validation rules

- `email`: trim, lowercase, RFC 5322 check, max 254 chars
- `password`: 12-256 chars, no other constraints (NIST 800-63B)
- `name`: 1-64 chars, no leading/trailing whitespace

## Migration notes

- Migration `0001_create_users_and_sessions.sql` creates both tables
- Rollback: `DROP TABLE sessions; DROP TABLE users;` (safe — no foreign refs to these yet)
