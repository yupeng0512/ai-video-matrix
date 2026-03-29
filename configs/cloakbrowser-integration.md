# CloakBrowser Integration Guide (Phase 3+)

## Overview

CloakBrowser provides source-level anti-detection through 33 C++ patches to Chromium.
CloakBrowser-Manager provides multi-profile management via Docker.

## Setup

### 1. Deploy CloakBrowser-Manager

```bash
# Add to docker-compose.yml
docker run -d \
  --name cloakbrowser-manager \
  -p 8080:8080 \
  -v cloakbrowser_data:/data \
  ghcr.io/cloakhq/cloakbrowser-manager:latest
```

### 2. Create Profiles for Each Account

```bash
# Create a profile via API
curl -X POST http://localhost:8080/api/profiles \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "douyin_account_001",
    "proxy": "http://user:pass@proxy:port",
    "timezone": "Asia/Shanghai",
    "language": "zh-CN",
    "fingerprint_seed": "unique-seed-for-this-account"
  }'
```

### 3. Integrate with Publisher Service

Update `publisher/workers/worker.py` to use CloakBrowser profiles:

```python
# Instead of creating a regular Chromium context:
# ctx = await self._browser.new_context(...)

# Use CloakBrowser-Manager API to get a profile-specific browser:
async def _get_cloakbrowser_context(self, profile_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"http://cloakbrowser-manager:8080/api/profiles/{profile_id}/start"
        )
        ws_url = resp.json()["ws_endpoint"]
    
    browser = await self._playwright.chromium.connect_over_cdp(ws_url)
    return browser.contexts[0]
```

### 4. Migration Strategy

- Phase 2: Use `playwright-stealth` (JS injection)
- Phase 3: Gradually migrate accounts to CloakBrowser profiles
- Phase 3+: All new accounts use CloakBrowser by default
- Monitor bot detection scores: target > 0.9 on reCAPTCHA v3

### 5. Profile Management

Each account maps to one CloakBrowser profile:
- Independent fingerprint seed
- Independent proxy IP
- Independent cookie storage
- Independent timezone/language settings

Store profile_id in the `accounts.profile_id` column.
