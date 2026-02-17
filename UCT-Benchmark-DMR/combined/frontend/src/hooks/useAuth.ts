import { useState, useCallback } from 'react';
import { supabase } from '@/lib/supabase';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/api/client';
import type { User } from '@/types';

type OAuthProvider = 'google' | 'github' | 'azure';

interface UseAuthReturn {
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, username?: string, organization?: string) => Promise<void>;
  logout: () => Promise<void>;
  loginWithOAuth: (provider: OAuthProvider) => Promise<void>;
}

/**
 * Custom hook wrapping Supabase Auth with fallback to API calls.
 *
 * When the Supabase client is available (VITE_SUPABASE_URL is set),
 * authentication goes directly through the Supabase JS SDK.
 * Otherwise, it falls back to the backend API endpoints.
 */
export function useAuth(): UseAuthReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login: storeLogin, logout: storeLogout } = useAuthStore();

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);

    try {
      if (supabase) {
        const { data, error: supaError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (supaError) throw new Error(supaError.message);
        if (!data.session || !data.user) throw new Error('Login failed: no session returned.');

        const user: User = {
          id: data.user.id,
          email: data.user.email || '',
          username: data.user.user_metadata?.username || '',
          organization: data.user.user_metadata?.organization || '',
          role: (data.user.role as User['role']) || 'developer',
          createdAt: data.user.created_at || '',
          submissionCount: 0,
        };

        storeLogin(user, data.session.access_token);
      } else {
        // Fallback to API
        const { data } = await api.login({ email, password });
        const tokenData = data as { access_token: string; user: User };
        storeLogin(tokenData.user, tokenData.access_token);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed.';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [storeLogin]);

  const signup = useCallback(async (
    email: string,
    password: string,
    username?: string,
    organization?: string,
  ) => {
    setLoading(true);
    setError(null);

    try {
      if (supabase) {
        const { data, error: supaError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: { username, organization },
          },
        });

        if (supaError) throw new Error(supaError.message);
        if (!data.user) throw new Error('Signup failed.');

        // If a session is returned immediately (no email confirmation required)
        if (data.session) {
          const user: User = {
            id: data.user.id,
            email: data.user.email || '',
            username: username || '',
            organization: organization || '',
            role: 'developer',
            createdAt: data.user.created_at || '',
            submissionCount: 0,
          };
          storeLogin(user, data.session.access_token);
        }
      } else {
        // Fallback to API
        const { data } = await api.login({ email, password });
        const tokenData = data as { access_token: string; user: User };
        storeLogin(tokenData.user, tokenData.access_token);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Signup failed.';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [storeLogin]);

  const logout = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      if (supabase) {
        const { error: supaError } = await supabase.auth.signOut();
        if (supaError) throw new Error(supaError.message);
      } else {
        await api.logout();
      }
      storeLogout();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Logout failed.';
      setError(message);
      // Still clear local state even if the server call fails
      storeLogout();
    } finally {
      setLoading(false);
    }
  }, [storeLogout]);

  const loginWithOAuth = useCallback(async (provider: OAuthProvider) => {
    setLoading(true);
    setError(null);

    try {
      if (!supabase) {
        throw new Error('OAuth login requires Supabase configuration (VITE_SUPABASE_URL).');
      }

      const { error: supaError } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      });

      if (supaError) throw new Error(supaError.message);
      // OAuth redirects the browser; the AuthProvider will pick up the session on return.
    } catch (err) {
      const message = err instanceof Error ? err.message : 'OAuth login failed.';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, login, signup, logout, loginWithOAuth };
}
