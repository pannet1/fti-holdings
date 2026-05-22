# BrokerAuthenticate — Broker Authentication Spec

## Overview

Authenticates with the Finvasia (Shoonya) broker API using credentials from `apps/backend/data/auth.yaml`.

## Flow

1. Controller receives credentials (userid, password, totp_secret, api_key, api_secret, imei, oauth_url, token_path)
2. Handler validates required fields are non-empty
3. If a session token file exists at `token_path`, return early (reuse)
4. Otherwise, initialize `Finvasia` from `broker-ai` with all params and call `authenticate()`
5. On success: save session token to `token_path`, return authenticated session
6. On failure: raise `RuntimeError` instructing user to check auth.yaml or delete stale token

## auth.yaml Format

```yaml
finvasia:
  userid: "FN137030"
  password: "secret"
  totp_secret: "ZGW67AUJV4W3F6JCATJ4QCK6YO534N64"
  api_key: "FN137030_U"
  api_secret: "qQKJKgM2iOaOlxK388BHYh4d92AckQqh6xqoHDYpBl62CiL49iZ6Z85N5PkCCd96"
  imei: "abc1234"
  oauth_url: "https://trade.shoonya.com/OAuthlogin/authorize/oauth"
```

## Error Cases

| Condition | Error | Message |
|-----------|-------|---------|
| Empty required fields | ValueError | Missing required credentials |
| Auth API returns None | RuntimeError | Authentication failed for {userid} |

## Dependencies

- `broker-ai` (Finvasia class)
- `apps/backend/data/auth.yaml`

## Code Standards

All code must use type annotations per PEP 484 (function signatures + module-level variables).
