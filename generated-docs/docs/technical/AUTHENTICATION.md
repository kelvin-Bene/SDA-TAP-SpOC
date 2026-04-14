# Authentication

> **Last updated:** 2026-04-14

## Overview

The UCT Benchmark platform uses **Supabase Auth** for all user-facing authentication. Login, signup, logout, password reset, and OAuth are handled entirely on the frontend by the Supabase JS SDK. The backend never manages sessions or credentials directly -- it only **verifies JWTs** issued by Supabase and extracts user identity from the token claims.

---

## Architecture

```
Browser (React + Zustand)                Backend (FastAPI)
+----------------------------+           +-------------------------------+
|                            |           |                               |
|  Supabase JS SDK           |           |  backend_api/auth.py          |
|  - signInWithPassword()    |           |  (production ES256 JWKS)      |
|  - signInWithOAuth()       |           |                               |
|  - signUp()                |           |  backend_api/middleware/       |
|  - signOut()               |           |    auth.py                    |
|  - refreshSession()        |           |  (HS256 fallback + dev bypass)|
|                            |           |                               |
|  authStore (Zustand)       |  Bearer   |  Endpoints:                   |
|  - stores User + Session   |  JWT in   |  POST /api/v1/auth/verify     |
|  - mapSupabaseUser()       |  header   |  GET  /api/v1/auth/me         |
|                            | --------> |  PATCH /api/v1/auth/me        |
|  Axios interceptors        |           |                               |
|  - attach JWT to requests  |           |  Dependencies:                |
|  - refresh on 401          |           |  get_current_user             |
|                            |           |  get_optional_user            |
+----------------------------+           |  require_admin                |
                                         +-------------------------------+
```

---

## Authentication Flow

### 1. Frontend: User Signs In

All sign-in methods go through the Supabase JS SDK (`@/lib/supabase.ts`). The `useAuthStore` (Zustand) exposes these actions:

| Action              | Supabase SDK Call                        |
|---------------------|------------------------------------------|
| Email/password      | `supabase.auth.signInWithPassword()`     |
| OAuth (e.g. Google) | `supabase.auth.signInWithOAuth()`        |
| Sign up             | `supabase.auth.signUp()`                 |
| Logout              | `supabase.auth.signOut()`                |
| Password reset      | `supabase.auth.resetPasswordForEmail()`  |

On success, Supabase returns a `Session` containing the JWT (`access_token`) and user object.

### 2. Frontend: Session Stored in Zustand

The `onAuthStateChange` listener in `authStore.ts` reacts to all Supabase auth events (sign-in, sign-out, token refresh). On each event it calls `mapSupabaseUser()` to convert the Supabase user into the internal `User` type and updates the store:

```typescript
set({
  user,             // Internal User type
  session,          // Supabase Session (contains access_token)
  isAuthenticated,
  isAdmin,          // user.role === 'admin'
});
```

### 3. Frontend: JWT Attached via Axios Interceptors

The API client (`frontend/src/api/client.ts`) uses Axios interceptors to manage authentication headers:

**Request interceptor** -- before every API call:
1. Calls `supabase.auth.getSession()` to get the current access token
2. Sets `Authorization: Bearer <token>` on the request

**Response interceptor** -- on 401 responses:
1. Uses a mutex (`isRefreshing`) to prevent parallel refresh attempts
2. Calls `supabase.auth.refreshSession()` to obtain a new token
3. Queues other in-flight requests behind the refresh
4. Retries the original request with the new token
5. Signs out after 3 consecutive refresh failures within 60 seconds

### 4. Backend: JWT Verification

The backend validates JWTs using a two-tier strategy depending on environment configuration.

#### Production Path (ES256 JWKS)

When `SUPABASE_URL` is set, `backend_api/auth.py` handles verification:

1. A `PyJWKClient` fetches public keys from `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`
2. Keys are cached after the first fetch
3. JWT is verified with these requirements:
   - **Algorithm:** ES256
   - **Audience:** `authenticated`
   - **Issuer:** `{SUPABASE_URL}/auth/v1`
   - **Expiration:** must be valid

#### HS256 Fallback Path

When ES256 verification fails, the backend may fall back to HS256 under these conditions:
- `SUPABASE_JWT_SECRET` is set
- Either `TESTING=true` or (`ALLOW_HS256_FALLBACK=true` and `SUPABASE_URL` is not set)

When only `SUPABASE_JWT_SECRET` is set (no `SUPABASE_URL`), `backend_api/middleware/auth.py` handles verification directly via HS256.

#### Development Bypass

When `ENVIRONMENT=development` and no `SUPABASE_JWT_SECRET` is configured, the middleware returns a stub user without enforcing authentication. Safety guards prevent this bypass in production:

- Blocked if `SUPABASE_URL` is set
- Blocked if `DATABASE_BACKEND` is `postgres` or `supabase`
- Stub user: `id="dev-user"`, `email="dev@localhost"`, `role="authenticated"`

#### Demo Mode

When `DEMO_MODE=true` and no `SUPABASE_JWT_SECRET` is configured, a read-only demo user is returned:
- `id="demo-user"`, `email="demo@uct-benchmark.example"`, `role="authenticated"`

### 5. Backend: Role Extraction

User roles are extracted from `app_metadata.role` in the JWT payload. The `app_metadata` claim is server-side only and cannot be modified by clients via `supabase.auth.updateUser()`. The top-level `role` claim and `user_metadata` are intentionally ignored for authorization decisions.

```python
# backend_api/auth.py — _build_current_user()
role = "authenticated"
app_metadata = payload.get("app_metadata", {})
if isinstance(app_metadata, dict) and "role" in app_metadata:
    role = app_metadata["role"]
```

---

## Backend API Endpoints

The backend auth router is mounted at `/api/v1/auth`. There are **no login, logout, or refresh endpoints** -- those operations happen entirely on the frontend via the Supabase SDK.

### `POST /api/v1/auth/verify`

Verify the JWT and return the authenticated user's profile. Creates a profile record in the database on first login.

- **Auth:** Required (Bearer JWT)
- **Rate limit:** 10/minute
- **Response:** `{ authenticated: true, user: UserProfile }`

### `GET /api/v1/auth/me`

Return the current authenticated user's profile.

- **Auth:** Required (Bearer JWT)
- **Response:** `UserProfile`

### `PATCH /api/v1/auth/me`

Update the current user's profile fields.

- **Auth:** Required (Bearer JWT)
- **Rate limit:** 10/minute
- **Updatable fields:** `display_name`, `organization`, `udl_token`, `esa_token`
- **Token validation:** UDL and ESA tokens are validated before saving
- **Token storage:** Tokens are encrypted at rest, masked in responses
- **Audit:** Profile updates and token changes are logged

### Response Model: `UserProfile`

```json
{
  "id": "string",
  "email": "string",
  "role": "string",
  "display_name": "string | null",
  "organization": "string | null",
  "udl_token": "****abcd | null",
  "esa_token": "****efgh | null",
  "created_at": "datetime | null",
  "updated_at": "datetime | null"
}
```

---

## Frontend: `mapSupabaseUser()`

The `mapSupabaseUser()` function in `frontend/src/stores/authStore.ts` converts a Supabase user object into the internal `User` type used throughout the frontend:

```typescript
function mapSupabaseUser(supabaseUser): User {
  const metadata = supabaseUser.user_metadata ?? {};
  const appMetadata = supabaseUser.app_metadata ?? {};
  return {
    id: supabaseUser.id,
    username: metadata.display_name ?? metadata.full_name
              ?? supabaseUser.email?.split('@')[0] ?? 'user',
    email: supabaseUser.email ?? '',
    organization: metadata.organization ?? '',
    role: appMetadata.role ?? 'authenticated',
    createdAt: supabaseUser.created_at ?? new Date().toISOString(),
    submissionCount: 0,
  };
}
```

**Field mapping:**

| Internal `User` field | Source                                                     |
|-----------------------|------------------------------------------------------------|
| `id`                  | `supabaseUser.id`                                          |
| `username`            | `user_metadata.display_name` > `full_name` > email prefix  |
| `email`               | `supabaseUser.email`                                       |
| `organization`        | `user_metadata.organization`                               |
| `role`                | `app_metadata.role` (defaults to `'authenticated'`)        |
| `createdAt`           | `supabaseUser.created_at`                                  |
| `submissionCount`     | Always `0` (populated later from API)                      |

**Role values** (frontend `User['role']` type):

| Role            | Description                                    |
|-----------------|------------------------------------------------|
| `authenticated` | Default role, standard access                  |
| `evaluator`     | Evaluation permissions                         |
| `admin`         | Full access, manage all submissions/feedback   |

Admin role is set via Supabase dashboard or SQL:

```sql
UPDATE auth.users
SET raw_app_meta_data = jsonb_set(raw_app_meta_data, '{role}', '"admin"')
WHERE email = 'target@example.com';
```

---

## FastAPI Dependencies

### `get_current_user`

Required authentication. Returns a `CurrentUser` dataclass or raises 401.

```python
from backend_api.auth import CurrentUser, get_current_user

@router.get("/protected")
async def protected_endpoint(user: CurrentUser = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}
```

### `get_optional_user`

Optional authentication. Returns `CurrentUser` if a valid token is present, `None` if no token.

```python
from backend_api.middleware.auth import get_optional_user

@router.post("/public-with-optional-auth")
async def public_endpoint(user: Optional[CurrentUser] = Depends(get_optional_user)):
    if user:
        # Authenticated request
    else:
        # Anonymous request
```

### `require_admin`

Requires both authentication and admin role. Raises 403 for non-admin users.

```python
from backend_api.middleware.auth import require_admin

@router.delete("/admin-only")
async def admin_route(user: CurrentUser = Depends(require_admin)):
    ...
```

### `CurrentUser` Dataclass

```python
@dataclass
class CurrentUser:
    id: str      # Supabase user UUID (from JWT "sub" claim)
    email: str   # User email
    role: str    # From app_metadata.role

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
```

---

## Environment Variables

| Variable               | Required     | Description                                              |
|------------------------|--------------|----------------------------------------------------------|
| `SUPABASE_URL`         | Production   | Supabase project URL (enables ES256 JWKS verification)   |
| `SUPABASE_JWT_SECRET`  | Dev/fallback | JWT secret for HS256 verification                        |
| `SUPABASE_JWKS_URL`    | No           | Override JWKS endpoint URL (default: auto from SUPABASE_URL) |
| `ALLOW_HS256_FALLBACK` | No           | Set to `true` to allow HS256 fallback in non-production  |
| `ENVIRONMENT`          | No           | Set to `development` for dev-mode auth bypass            |
| `DEMO_MODE`            | No           | Set to `true` for read-only demo user                    |
| `DATABASE_BACKEND`     | No           | Blocks dev bypass when set to `postgres` or `supabase`   |
| `TESTING`              | No           | Set to `true` to enable HS256 fallback in tests          |

**Frontend environment variables** (set in `.env`):

| Variable               | Required   | Description                        |
|------------------------|------------|------------------------------------|
| `VITE_SUPABASE_URL`    | Yes        | Supabase project URL               |
| `VITE_SUPABASE_ANON_KEY` | Yes     | Supabase anonymous/public API key  |
| `VITE_API_BASE_URL`    | No         | Backend API base URL (default: `/api/v1`) |

---

## Key Source Files

| File                                          | Purpose                                       |
|-----------------------------------------------|-----------------------------------------------|
| `backend_api/auth.py`                         | Production ES256 JWKS verification + CurrentUser |
| `backend_api/middleware/auth.py`              | HS256 fallback, dev bypass, FastAPI dependencies |
| `backend_api/routers/auth.py`                 | Auth API endpoints (verify, me, profile update) |
| `frontend/src/lib/supabase.ts`               | Supabase client initialization                 |
| `frontend/src/stores/authStore.ts`            | Zustand auth store + mapSupabaseUser()         |
| `frontend/src/api/client.ts`                  | Axios interceptors for JWT + token refresh     |
| `frontend/src/types/index.ts`                | User interface definition                      |

---

## Related Documentation

- [Backend API](BACKEND_API.md) -- API endpoint reference
- [Configuration](CONFIGURATION.md) -- Full environment variable reference
- [Deployment](../guides/DEPLOYMENT.md) -- Production deployment guide
