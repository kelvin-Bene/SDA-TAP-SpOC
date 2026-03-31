import { create } from 'zustand';
import { supabase } from '@/lib/supabase';
import type { User } from '@/types';
import type { Session, Provider, AuthError, AuthChangeEvent } from '@supabase/supabase-js';

interface AuthState {
  user: User | null;
  session: Session | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  error: string | null;

  // Actions
  initialize: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  loginWithOAuth: (provider: Provider) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  clearError: () => void;
}

function mapSupabaseUser(
  supabaseUser: { id: string; email?: string; user_metadata?: Record<string, unknown>; created_at?: string }
): User {
  const metadata = supabaseUser.user_metadata ?? {};
  return {
    id: supabaseUser.id,
    username: (metadata.display_name as string) ?? (metadata.full_name as string) ?? supabaseUser.email?.split('@')[0] ?? 'user',
    email: supabaseUser.email ?? '',
    organization: (metadata.organization as string) ?? '',
    role: (metadata.role as User['role']) ?? 'developer',
    createdAt: supabaseUser.created_at ?? new Date().toISOString(),
    submissionCount: 0,
  };
}

function formatAuthError(error: AuthError): string {
  switch (error.message) {
    case 'Invalid login credentials':
      return 'Invalid email or password. Please try again.';
    case 'Email not confirmed':
      return 'Please check your email and confirm your account before signing in.';
    case 'User already registered':
      return 'An account with this email already exists. Try signing in instead.';
    default:
      return error.message;
  }
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  user: null,
  session: null,
  isAuthenticated: false,
  isLoading: true,
  isAdmin: false,
  error: null,

  initialize: async () => {
    try {
      // Demo mode: skip Supabase session check, preserve existing auth
      if (import.meta.env.VITE_DEMO_MODE === 'true') {
        const current = get();
        if (!current.isAuthenticated) {
          set({ isLoading: false });
        }
        return;
      }

      const { data: { session }, error } = await supabase.auth.getSession();

      if (error) {
        console.error('Failed to get session:', error.message);
        set({ isLoading: false, isAuthenticated: false });
        return;
      }

      if (session?.user) {
        const user = mapSupabaseUser(session.user);
        set({
          user,
          session,
          isAuthenticated: true,
          isAdmin: user.role === 'admin',
          isLoading: false,
        });
      } else {
        set({ isLoading: false, isAuthenticated: false });
      }

      // Listen for auth state changes (sign in, sign out, token refresh)
      supabase.auth.onAuthStateChange((_event: AuthChangeEvent, newSession: Session | null) => {
        if (newSession?.user) {
          const user = mapSupabaseUser(newSession.user);
          set({
            user,
            session: newSession,
            isAuthenticated: true,
            isAdmin: user.role === 'admin',
            isLoading: false,
          });
        } else {
          set({
            user: null,
            session: null,
            isAuthenticated: false,
            isAdmin: false,
            isLoading: false,
          });
        }
      });
    } catch (err) {
      console.error('Auth initialization failed:', err);
      set({ isLoading: false, isAuthenticated: false });
    }
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      // Demo mode: bypass Supabase, set mock user directly
      if (import.meta.env.VITE_DEMO_MODE === 'true') {
        set({
          user: {
            id: 'dev-user',
            email: 'demo@spoc-benchmark.org',
            username: 'Demo User',
            organization: 'SpOC Demo',
            role: 'developer',
            createdAt: new Date().toISOString(),
            submissionCount: 0,
          },
          session: null,
          isAuthenticated: true,
          isAdmin: false,
          isLoading: false,
        });
        return;
      }
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) {
        set({ isLoading: false, error: formatAuthError(error) });
        return;
      }
      // Session will be set by onAuthStateChange listener
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      set({ isLoading: false, error: message });
    }
  },

  loginWithOAuth: async (provider: Provider) => {
    set({ isLoading: true, error: null });
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      });
      if (error) {
        set({ isLoading: false, error: formatAuthError(error) });
      }
      // OAuth redirects the browser; loading state will persist until redirect
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      set({ isLoading: false, error: message });
    }
  },

  signup: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          emailRedirectTo: `${window.location.origin}/login`,
        },
      });
      if (error) {
        set({ isLoading: false, error: formatAuthError(error) });
        return;
      }
      set({
        isLoading: false,
        error: null,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      set({ isLoading: false, error: message });
    }
  },

  logout: async () => {
    set({ isLoading: true, error: null });
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Logout error:', error.message);
      }
      // State will be cleared by onAuthStateChange listener
    } catch (err) {
      console.error('Logout failed:', err);
      // Force clear state even if signOut fails
      set({
        user: null,
        session: null,
        isAuthenticated: false,
        isAdmin: false,
        isLoading: false,
      });
    }
  },

  resetPassword: async (email: string) => {
    set({ isLoading: true, error: null });
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/login`,
      });
      if (error) {
        set({ isLoading: false, error: formatAuthError(error) });
        return;
      }
      set({ isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred';
      set({ isLoading: false, error: message });
    }
  },

  clearError: () => set({ error: null }),
}));
