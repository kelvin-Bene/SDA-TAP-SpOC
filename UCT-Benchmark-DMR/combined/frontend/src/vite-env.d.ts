/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_ENV: 'development' | 'production' | 'test';
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_SENTRY_DSN: string;
  readonly VITE_FEEDBACK_ENABLED: string;
  // DGX Spark local edition: when "true", the UI shows local-edition badges
  // and the sidebar reveals the /llm/* pages.
  readonly VITE_LOCAL_DGX_MODE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
