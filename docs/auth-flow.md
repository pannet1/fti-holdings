# Authentication Flow — Finvasia / Shoonya

## Architecture

```
auth.yaml ──► main.py ──► AuthenticateBrokerHandler ──► Finvasia.authenticate()
                              │                              │
                              │                         ┌────┴────┐
                              │                      QuickAuth  GenAcsTok
                              │                     (trade.)   (api.)
                              │                         │         │
                              │                         └────┬────┘
                              │                          set_session()
                              │                          injectOAuthHeader()
                              │                              │
                              └── result["session"] ──────────┘
```

## Two-package system

The broker-ai package contains two NorenApi implementations:

| File | Set session signature | Purpose |
|------|----------------------|---------|
| `NorenApi.py` | `set_session(userid, password, usertoken)` | Old flat-trade base |
| `NewNorenApi.py` | `set_session(userid, password, usertoken, accesstoken)` | Shoonya OAuth-enabled |

`api_helper.py` imports from `NewNorenApi.py`:
```python
from broker_ai.finvasia.NewNorenApi import NorenApi  # <-- NOT NorenApi.py
```

So `ShoonyaApiPy` (used by `Finvasia`) gets the `NewNorenApi` version that accepts both
`usertoken` AND `accesstoken` kwargs in `set_session`.

## Auth flow (authenticate method)

### Step 1 — QuickAuth

POST to `https://trade.shoonya.com/NorenWClientAPI/QuickAuth`

Payload:
```json
{
  "apkversion": "1.0.0",
  "uid": "FN137030",
  "pwd": "<sha256(password)>",
  "factor2": "<TOTP.now()>",
  "appkey": "<app_key_hash or ''>",
  "imei": "<uuid>",
  "addldivinf": "Mozilla/5.0",
  "source": "API",
  "vc": "NOREN_API",
  "app_key": "<api_key>"
}
```

Success response includes `code` (auth code).

### Step 2 — GenAcsTok

POST to `https://api.shoonya.com/NorenWClientAPI/GenAcsTok`

Headers: `Authorization: Bearer <sha256(api_key + api_secret + code)>`

Payload:
```json
{
  "code": "<auth_code_from_QuickAuth>",
  "checksum": "<sha256(api_key + api_secret + code)>",
  "uid": "FN137030"
}
```

Success response contains `access_token`, `USERID`, `refresh_token`, `actid`.

### Step 3 — set_session + injectOAuthHeader

```python
self.broker.set_session(
    userid=usrid, password=self._password,
    usertoken=acc_tok, accesstoken=acc_tok,  # both required by NewNorenApi
)
self.broker.injectOAuthHeader(acc_tok, usrid, actid)
```

### Step 4 — Return

Returns dict with `access_token`, `user_id`, `refresh_token`, `account_id`.

## Key files

| File | Role |
|------|------|
| `apps/backend/app/main.py` | Entry point, passes creds + calls handler |
| `apps/backend/app/features/broker/AuthenticateBroker/Handler.py` | Creates Finvasia, calls authenticate(), saves token |
| `.venv/.../broker_ai/finvasia/finvasia.py` | Finvasia class with authenticate() implementing QuickAuth→GenAcsTok |
| `.venv/.../broker_ai/finvasia/NewNorenApi.py` | Shoonya API wrapper, set_session accepts `usertoken` + `accesstoken` |
| `.venv/.../broker_ai/finvasia/api_helper.py` | Imports NorenApi from NewNorenApi (not NorenApi.py!) |
| `data/auth.yaml` | Credentials file (600 permissions) |

## Common pitfalls

### set_session kwarg mismatch
`NewNorenApi.set_session` accepts BOTH `usertoken` and `accesstoken`. If you pass only one,
or use the wrong kwarg name, Python raises `TypeError`.

Fix: always pass both:
```python
self.broker.set_session(
    userid=..., password=...,
    usertoken=token, accesstoken=token,
)
```

### Import from wrong NorenApi
`api_helper.py` must import from `NewNorenApi.py`, not `NorenApi.py`:
```python
# CORRECT:
from broker_ai.finvasia.NewNorenApi import NorenApi

# WRONG:
from broker_ai.finvasia.NorenApi import NorenApi
```

The old `NorenApi.set_session` only accepts `(userid, password, usertoken)` — passing
`accesstoken` to it will crash.

### get_auth_code_automated is broken
The `session.py` module's `get_auth_code_automated()` POSTs credentials to an OAuth URL
as a form login. This does NOT work with Shoonya's auth flow. Use QuickAuth → GenAcsTok
instead (direct Shoonya API endpoints).

### Token reuse is removed
The current `Handler.py` does NOT reuse stored tokens. Every startup does fresh
QuickAuth → GenAcsTok. The saved token file is informational only.

Reason: the new `Finvasia.__init__` doesn't accept `access_token`/`refresh_token` params.
Token reuse was removed because it adds complexity (stale tokens, kwarg mismatches)
with no real benefit — QuickAuth is fast and reliable.

### IP whitelisting
GenAcsTok returns `INVALID_IP` if the server IP is not whitelisted in the Shoonya
Prism portal. This is a deployment concern, not a code bug.

## When auth fails

1. Check `auth.yaml` has `userid`, `password`, `totp_secret`, `api_key`, `api_secret`, `imei`, `oauth_url`
2. Check `app_key_hash` is the SHA256 of the user ID (from Shoonya Prism API settings)
3. Check vendor code is `NOREN_API` (default) or the one from Prism
4. Check server IP is whitelisted at `trade.shoonya.com` → Profile → API Key
5. Check TOTP secret is correct and synced (use `pyotp.TOTP(secret).now()` to verify)
