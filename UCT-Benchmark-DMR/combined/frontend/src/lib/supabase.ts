import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    'Supabase environment variables are not set. Auth features will not work. ' +
    'Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file.'
  )
  if (import.meta.env.PROD && !import.meta.env.VITE_DEMO_MODE) {
    throw new Error('VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY must be set in production builds');
  }
}

// Create a real client when configured, or a placeholder that won't crash the app
let supabase: SupabaseClient;
try {
  supabase = createClient(supabaseUrl || 'https://placeholder.supabase.co', supabaseAnonKey || 'placeholder-key');
} catch {
  // Fallback: create with placeholder so the app can render without Supabase
  supabase = createClient('https://placeholder.supabase.co', 'placeholder-key');
}

export { supabase }
