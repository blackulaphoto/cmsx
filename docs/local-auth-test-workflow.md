# Local Firebase Auth Test Workflow

Use this workflow when testing authenticated backend endpoints from a terminal.

## Get a fresh Firebase ID token

1. Log in to the frontend in Chrome.
2. Open DevTools on the app page.
3. Run the local token-copy snippet used by the team, or call Firebase `getIdToken(true)` from the logged-in app context.
4. Paste the token into your local shell only.

PowerShell:

```powershell
$env:TEST_TOKEN = "<fresh Firebase ID token>"
```

Do not store real tokens in committed files. Do not commit `.env`, `.env.local`, terminal transcripts, screenshots, or docs containing bearer tokens.

## Curl an authenticated endpoint

```powershell
curl.exe -H "Authorization: Bearer $env:TEST_TOKEN" https://cmsx-production-088d.up.railway.app/api/ur
```

Expected result for a valid token is a normal endpoint response such as HTTP 200 JSON. If the backend returns `Missing Firebase bearer token`, the request did not include the header. If it returns `Invalid Firebase token`, refresh the Firebase token and retry.

## Local test bypass

Backend test headers are only allowed when `ENABLE_TEST_AUTH=true` and the backend environment is local/test/e2e. Production-like environments ignore test auth headers.

Frontend test auth headers are controlled by `VITE_ENABLE_TEST_AUTH=true` and are intended only for local/test runs. Do not enable frontend test auth in production deployments.
