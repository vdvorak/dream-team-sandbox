# auth impl — python-fastapi (credentials `base`)

Vetted reference implementation of the `auth` feature `base` variant (spec: `../../spec.md`).
**Security-critical → audited once here (Heimdall); projects copy it, do not regenerate.**
Verified: `pytest` 8/8 for **both** token strategies (jwt + session).

## Structure: common + chosen strategy
```
server/src/auth/                    COMMON (oba strategie)
  models.py  passwords.py  repository.py  service.py
server/src/auth/security_jwt.py  + router_jwt.py        ← token_strategy=jwt
server/src/auth/security_session.py + router_session.py + sessions.py
                                  + contracts/.../V3__sessions.sql   ← token_strategy=session
contracts/db/migrations/V2__auth.sql   (user table — oba)
server/tests/test_auth_jwt.py | test_auth_session.py
```

## Overlay onto a python-fastapi project (Watson dle `token_strategy`)
Kopíruj **common** + soubory zvolené strategie:
- **jwt**: common + `security_jwt.py` + `router_jwt.py` + `V2__auth.sql` + `test_auth_jwt.py`
- **session**: common + `security_session.py` + `router_session.py` + `sessions.py` +
  `V2__auth.sql` + `V3__sessions.sql` + `test_auth_session.py`

Wire the router in `server/src/main.py`:
```python
from .auth.router_jwt import router as auth_router       # nebo router_session
app.include_router(auth_router)
```
Deps (recommended-libs `python-fastapi`): `passlib[bcrypt]`, `pyjwt` (jen jwt). Set `APP_SECRET_KEY`.

## Endpoints
- `POST /auth/register` (write-flow: `?validate=true` dry-run / commit) — bcrypt hash, unique email
- `POST /auth/login` — jwt → `{access_token}`; session → set httpOnly cookie. Wrong creds = generic
  `invalid_credentials` (no enumeration)
- `GET /auth/me` — jwt: Bearer header; session: cookie
- `POST /auth/logout` — **session only** (smaže session)

Layering router→service→repository, `*Data`/`*View` modely, `{code, details}` chyby.
