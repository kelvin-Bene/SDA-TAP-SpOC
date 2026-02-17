# Authentication Setup Guide

This guide explains how to configure authentication for the UCT Benchmark platform.

## Overview

The platform supports two authentication modes:
- **Disabled** (default): All endpoints work without tokens, ideal for local development
- **Enabled**: Requires valid Supabase JWT tokens for protected endpoints

## Environment Variables

### Core Auth Settings

```env
# Enable/disable authentication (default: false)
AUTH_ENABLED=false

# Supabase JWT secret (required when AUTH_ENABLED=true)
# Found in: Supabase Dashboard > Settings > API > JWT Secret
SUPABASE_JWT_SECRET=your-jwt-secret-here

# Supabase project configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Frontend Configuration

```env
# Frontend .env file
VITE_AUTH_ENABLED=false
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

## Local Development (Auth Disabled)

For local development without authentication:

1. Set `AUTH_ENABLED=false` in your `.env` file (or omit it - false is default)
2. Set `VITE_AUTH_ENABLED=false` in frontend `.env`
3. All endpoints will work without JWT tokens
4. The `get_current_user()` dependency returns a mock user

```python
# When AUTH_ENABLED=false, this mock user is returned
{
    "sub": "dev-user",
    "email": "dev@localhost",
    "user_metadata": {"full_name": "Development User"},
    "app_metadata": {"role": "admin"}
}
```

## Production Setup with Supabase

### Step 1: Enable Supabase Auth

1. Go to your Supabase project dashboard
2. Navigate to **Authentication** > **Providers**
3. Enable desired auth providers (Email, Google, GitHub, etc.)

### Step 2: Get JWT Secret

1. Go to **Settings** > **API**
2. Copy the **JWT Secret** (not the anon key)
3. Add to your backend `.env`:
   ```env
   AUTH_ENABLED=true
   SUPABASE_JWT_SECRET=your-jwt-secret
   ```

### Step 3: Configure Frontend

Update frontend `.env`:
```env
VITE_AUTH_ENABLED=true
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

### Step 4: Test Authentication

```bash
# Start the backend
cd UCT-Benchmark-DMR/combined
uvicorn backend_api.main:app --reload

# Try accessing a protected endpoint (should return 401)
curl http://localhost:8000/api/v1/auth/me

# Login through the frontend to get a token
# Then use the token:
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/auth/me
```

## JWT Configuration

### Supported Algorithms

The platform supports two JWT signing algorithms:

1. **HS256** (HMAC with SHA-256) - Supabase default
   - Uses `SUPABASE_JWT_SECRET` for verification
   - Symmetric key (same key for signing and verification)

2. **ES256** (ECDSA with P-256) - Alternative
   - Uses JWKS (JSON Web Key Set) endpoint
   - Asymmetric key (public key for verification)

The backend automatically detects the algorithm from the JWT header.

### Token Structure

Supabase JWTs contain:
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "user_metadata": {
    "full_name": "User Name"
  },
  "app_metadata": {
    "role": "user"
  },
  "exp": 1735689600,
  "iat": 1735686000
}
```

## Role-Based Access Control

### User Roles

- **user**: Default role, can access own data and public endpoints
- **admin**: Full access, can manage all users and data

### Setting User Roles

Roles are stored in `app_metadata.role`:

```sql
-- In Supabase SQL Editor
UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'
WHERE email = 'admin@example.com';
```

### Protected Endpoints

```python
# In FastAPI router
from backend_api.auth.dependencies import require_auth, require_admin

@router.get("/protected")
async def protected_endpoint(user = Depends(require_auth)):
    return {"user": user.email}

@router.delete("/admin-only")
async def admin_endpoint(user = Depends(require_admin)):
    return {"admin": user.email}
```

## Troubleshooting

### "401 Unauthorized" on all requests

1. Check `AUTH_ENABLED` is set correctly
2. Verify JWT secret matches Supabase dashboard
3. Ensure token hasn't expired
4. Check token is being sent in `Authorization: Bearer TOKEN` header

### "Invalid token" errors

1. Token may be expired - refresh via Supabase client
2. JWT secret may be incorrect
3. Token may be from wrong Supabase project

### Frontend not showing login

1. Check `VITE_AUTH_ENABLED=true`
2. Verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are set
3. Restart frontend dev server after changing env vars

### Users table not syncing

The `users` table in PostgreSQL syncs with Supabase Auth via triggers:

```sql
-- This trigger should exist in your Supabase project
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (auth_user_id, email, username)
  VALUES (NEW.id, NEW.email, split_part(NEW.email, '@', 1));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

## Related Documentation

- [Supabase Setup](../SUPABASE_SETUP.md) - Database configuration
- [Backend API](../technical/BACKEND_API.md) - Auth endpoints
- [Frontend Architecture](../technical/FRONTEND.md) - AuthProvider component
