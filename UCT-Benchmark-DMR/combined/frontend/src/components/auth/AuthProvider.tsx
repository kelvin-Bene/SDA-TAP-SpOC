import { useEffect } from 'react';
import { supabase } from '@/lib/supabase';
import { useAuthStore } from '@/stores/authStore';
import type { User } from '@/types';

interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * Provider component that listens for Supabase auth state changes
 * and syncs the result into the Zustand authStore.
 *
 * Place this near the root of the component tree (e.g., wrapping <App />)
 * so that auth state is available everywhere.
 *
 * When the Supabase client is not configured (supabase === null),
 * this component simply renders its children with no side effects.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const { login, logout, setUser, setToken } = useAuthStore();

  useEffect(() => {
    if (!supabase) return;

    // Get the current session on mount
    supabase.auth.getSession().then(({ data: { session } }: { data: { session: any } }) => {
      if (session?.user) {
        const user: User = {
          id: session.user.id,
          email: session.user.email || '',
          username: session.user.user_metadata?.username || '',
          organization: session.user.user_metadata?.organization || '',
          role: (session.user.role as User['role']) || 'developer',
          createdAt: session.user.created_at || '',
          submissionCount: 0,
        };
        login(user, session.access_token);
      }
    });

    // Subscribe to auth state changes (login, logout, token refresh, etc.)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event: any, session: any) => {
      if (event === 'SIGNED_IN' && session?.user) {
        const user: User = {
          id: session.user.id,
          email: session.user.email || '',
          username: session.user.user_metadata?.username || '',
          organization: session.user.user_metadata?.organization || '',
          role: (session.user.role as User['role']) || 'developer',
          createdAt: session.user.created_at || '',
          submissionCount: 0,
        };
        login(user, session.access_token);
      } else if (event === 'SIGNED_OUT') {
        logout();
      } else if (event === 'TOKEN_REFRESHED' && session) {
        setToken(session.access_token);
        if (session.user) {
          const user: User = {
            id: session.user.id,
            email: session.user.email || '',
            username: session.user.user_metadata?.username || '',
            organization: session.user.user_metadata?.organization || '',
            role: (session.user.role as User['role']) || 'developer',
            createdAt: session.user.created_at || '',
            submissionCount: 0,
          };
          setUser(user);
        }
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [login, logout, setUser, setToken]);

  return <>{children}</>;
}
