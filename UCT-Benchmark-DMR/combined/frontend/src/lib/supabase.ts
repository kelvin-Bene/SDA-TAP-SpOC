import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''
const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true'

function createSupabaseClient(): SupabaseClient {
  if (isDemoMode || (!supabaseUrl && !supabaseAnonKey)) {
    if (!isDemoMode) {
      console.warn(
        'Supabase environment variables are not set. Auth features will not work. ' +
        'Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file.'
      )
    }
    // Return a no-op client that won't make network requests or trigger redirects
    return createClient('https://localhost.invalid', 'demo-placeholder', {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
        detectSessionInUrl: false,
      },
    })
  }

  return createClient(supabaseUrl, supabaseAnonKey)
}

export const supabase = createSupabaseClient()
