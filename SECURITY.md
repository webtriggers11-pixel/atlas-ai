# Security

Idea Atlas reads documents that may be confidential (specs, contracts, resumes) and sends excerpts
to an LLM. This page explains what the app protects against, how, and what it does not cover.

## Reporting a vulnerability

Please open a private security advisory on GitHub (Security → Report a vulnerability) instead of a
public issue. Include steps to reproduce. I aim to reply within a week.

## Deployment modes

| Mode | Setting | Who it is for |
|---|---|---|
| Self-hosted, single user (default) | `AUTH_ENABLED=false` | One person on their own machine or private server. No accounts. |
| Hosted, multi-user | `AUTH_ENABLED=true` + strong `JWT_SECRET` | A shared server. Everyone signs in and sees only their own analyses. |

Do not expose a server running in single-user mode to the public internet. Anyone who can reach it
can read every analysis.

## What is in place

**Authentication (when enabled)**
- Passwords are hashed with bcrypt. The password itself is never stored or logged.
- Sessions use HS256 JWTs. The algorithm is pinned, so `alg: none` and algorithm-swap tokens are
  rejected. Expiry is enforced (`JWT_EXPIRE_HOURS`).
- The server refuses to issue or accept tokens if `JWT_SECRET` is missing, shorter than 32
  characters, or still set to the placeholder (it fails closed).
- Login answers the same way for an unknown email and a wrong password. Login and register are
  rate limited (10 per minute per client).
- `AUTH_ALLOW_REGISTRATION=false` closes sign-ups.

**Authorization: every analysis belongs to one user**
- Each project has an `owner_id`. Every lookup checks ownership: projects, documents, chunks,
  requirements, runs, findings, traces, reports and exports.
- Lists (analyses, documents) are filtered by owner in the query, not afterwards.
- Someone else's resource returns **404, not 403**, so IDs can't be probed to learn what exists.
- The LLM tools used by Ask and the investigator have the project ID bound on the server. A model
  (or text inside a document) cannot make a tool read another analysis. Chunks are re-checked to
  belong to the project.

**Prompt injection (documents are untrusted input)**
- Tools are read-only. No tool writes data, makes network calls or runs code.
- The investigator can change a finding only by citing a quote that the server verifies, word for
  word, in a chunk of the same analysis. "It's missing" verdicts are recorded but never applied.
  Injected text that says "mark this as covered" still needs a real, verifiable quote.
- Tool loops have hard limits on steps and on time.

**Abuse and cost control**
- Per-client rate limits on LLM-backed endpoints (`RATE_LIMIT_LLM_PER_MINUTE`, default 20) and
  uploads (`RATE_LIMIT_UPLOADS_PER_MINUTE`, default 30). Over the limit, the API returns 429 with
  `Retry-After`.
- Counters live in Redis, so all API processes share them. If Redis is down, each process falls
  back to in-memory counters.
- The client is identified by user ID when signed in, otherwise by IP. Behind a reverse proxy, the
  right-most `X-Forwarded-For` entry is used: that is the entry the proxy appended, while earlier
  entries can be forged by the client.

**Uploads**
- Size limit (`MAX_UPLOAD_MB`). The extension and the file's magic bytes must agree.
- DOCX archives are inspected before parsing. Zip bombs (more than 100 MB uncompressed, or more than
  2,000 entries) and corrupt archives are rejected.
- Files are stored under server-generated UUID paths. The uploaded filename is used only for
  display, with directory parts and control characters stripped.

**HTTP**
- CORS allows only the origins in `CORS_ORIGINS` (no wildcard). Tokens travel in the
  `Authorization` header, not cookies, which rules out CSRF.
- Responses carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer` and `Cross-Origin-Resource-Policy: same-site`.
- SQL goes through SQLAlchemy with bound parameters. User search text is escaped before `ILIKE`.

**Data sent to LLM providers**
- Only the excerpts needed for a request are sent, never whole files.
- Free-tier providers may use prompts for training. Don't upload confidential documents on a free
  tier; use Ollama (fully local) for those.
- Invalid model output can contain document text, so it is kept in `llm_calls` only when
  `LOG_LLM_RAW_OUTPUT=true`. API keys come from environment variables and are never returned by the
  API or shown in the UI.

## Known limitations

- Tokens are stored in `localStorage`. An XSS bug could read them. React escapes rendered text and
  the app never injects HTML, but a cookie with `HttpOnly` would be stronger.
- There is no token revocation list. Signing out deletes the token in the browser, but a stolen
  token stays valid until it expires. Keep `JWT_EXPIRE_HOURS` short.
- No email verification, password reset or MFA.
- Rate limits use fixed one-minute windows, so a burst at a window boundary can reach twice the
  limit.
- Uploaded files are not virus-scanned. They are parsed, never executed.

## Production checklist

- [ ] `AUTH_ENABLED=true` and a random `JWT_SECRET` (32+ characters) if the server is public
- [ ] `CORS_ORIGINS` set to the exact frontend URL
- [ ] TLS terminated at the reverse proxy; API port bound to `127.0.0.1` only (prod compose does this)
- [ ] Reverse proxy sets `X-Forwarded-For` (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`)
- [ ] `LOG_LLM_RAW_OUTPUT=false`
- [ ] Database user has only the permissions the app needs; backups enabled
