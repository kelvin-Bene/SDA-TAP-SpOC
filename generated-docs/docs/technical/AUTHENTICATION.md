# Authentication

## Overview

The UCT Benchmark platform uses Supabase for authentication. Login, signup, and logout are handled entirely client-side by the Supabase JS SDK. The backend validates JWTs on every request using ES256 asymmetric keys fetched from Supabase's JWKS endpoint.

## Architecture

```
Browser (React)                    Backend (FastAPI)
┌──────────────┐                   ┌──────────────────────────┐
│ Supabase JS  │                   │ backend_api/auth.py      │
│ SDK handles: │                   │                          │
│ - signIn     │                   │ ES256 JWKS verification  │
│ - signUp     │  JWT in header    │ ┌──────────────────────┐ │
│ - signOut    │ ────────────────> │ │ _get_jwks_client()   │ │
│ - refresh    │                   │ │ _decode_jwt()        │ │
│              │                   │ │ _build_current_user() │ │
└──────────────┘                   │ └──────────────────────┘ │
                                   └──────────────────────────┘
```

## JWT Verification Flow

### Production (ES256 JWKS)

When `SUPABASE_URL` is set, the backend uses ES256 asymmetric key verification:

1. The JWKS client fetches public keys from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
2. Keys are cached after the first fetch
3. Each request's JWT is verified against the JWKS public key
4. The JWT must have:
   - Algorithm: `ES256`
   - Audience: `authenticated`
   - Valid issuer: `{SUPABASE_URL}/auth/v1`
   - Valid expiration

### HS256 Fallback

When only `SUPABASE_JWT_SECRET` is set (and `ALLOW_HS256_FALLBACK=true` with no `SUPABASE_URL`):

1. JWT is verified using the symmetric secret with HS256
2. This path is intended for local development only
3. In production, HS256 fallback is blocked when `SUPABASE_URL` is set

### Development Bypass

When `ENVIRONMENT=development` and neither `SUPABASE_URL` nor `SUPABASE_JWT_SECRET` is set:

1. A stub user is returned: `id="dev-user"`, `email="dev@localhost"`, `role="authenticated"`
2. This bypass is blocked if `SUPABASE_URL` is configured (prevents accidental production use)

## Role Extraction

User roles are extracted exclusively from `app_metadata.role` in the JWT payload:

```python
# backend_api/auth.py
role = "user"
app_metadata = payload.get("app_metadata", {})
if isinstance(app_metadata, dict) and "role" in app_metadata:
    role = app_metadata["role"]
```

`app_metadata` is server-side only and cannot be modified by the client via `supabase.auth.updateUser()`. The top-level `role` claim and `user_metadata` are intentionally ignored for authorization decisions.

### Role Values

| Role | Description |
|------|-------------|
| `user` | Default role, standard access |
| `admin` | Full access, can view all submissions, manage feedback |

Admin role is set via Supabase dashboard or SQL: `UPDATE auth.users SET raw_app_meta_data = jsonb_set(raw_app_meta_data, '{role}', '"admin"') WHERE email = '...'`

## FastAPI Dependencies

### `get_current_user`

Required authentication. Returns an `AuthUser` (or `CurrentUser` in the production auth module) or raises `401 Unauthorized`.

```python
from backend_api.middleware.auth import AuthUser, get_current_user

@router.get("/protected")
async def protected_endpoint(user: AuthUser = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}
```

### `get_optional_user`

Optional authentication. Returns `AuthUser` if a valid token is present, `None` if no token.

```python
from backend_api.middleware.auth import get_optional_user

@router.post("/public-with-optional-auth")
async def public_endpoint(user: Optional[AuthUser] = Depends(get_optional_user)):
    if user:
        # Authenticated request
    else:
        # Anonymous request
```

### `require_admin`

Requires both authentication and admin role. Raises `403 Forbidden` for non-admin users.

```python
from backend_api.middleware.auth import require_admin

@router.delete("/admin-only")
async def admin_route(user: AuthUser = Depends(require_admin)):
    ...
```

## Frontend Token Management

The frontend API client (`frontend/src/api/client.ts`) handles authentication automatically:

1. **Request interceptor**: Before each API request, the interceptor calls `supabase.auth.getSession()` and injects the access token into the `Authorization` header.

2. **Response interceptor (401 handling)**: On a 401 response, the interceptor:
   - Uses a mutex to prevent multiple parallel refresh attempts
   - Calls `supabase.auth.refreshSession()` to get a new token
   - Queues other in-flight requests behind the refresh
   - Retries the original request with the new token
   - Signs out after 3 consecutive refresh failures within 60 seconds

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Production | Supabase project URL (enables ES256 JWKS) |
| `SUPABASE_JWT_SECRET` | Dev/fallback | JWT secret for HS256 verification |
| `ALLOW_HS256_FALLBACK` | No | Set to `true` to allow HS256 in non-production |
| `ENVIRONMENT` | No | Set to `development` for dev-mode auth bypass |

## Related Documentation

- [Backend API](BACKEND_API.md) - API endpoint reference
- [Configuration](CONFIGURATION.md) - Full environment variable reference
- [Deployment](../guides/DEPLOYMENT.md) - Production deployment guide
