---
title: Frontend Architecture
last_updated: 2026-04-14
---

# Frontend Architecture

## Overview

The UCT Benchmark frontend is a React 18 single-page application built with Vite. It uses lazy-loaded routes, Supabase authentication, and a layered component architecture with shadcn/ui as the design system.

---

## Technology Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| Framework | React | ^18.3.1 | UI Components |
| Build Tool | Vite | ^5.4.6 | Dev server & production bundling |
| Language | TypeScript | ^5.6.2 | Type safety |
| Styling | Tailwind CSS | ^3.4.12 | Utility-first CSS |
| Component Library | shadcn/ui + Radix UI | -- | Accessible, themed primitives |
| Server State | TanStack React Query | ^5.56.2 | Caching, fetching, mutations |
| Client State | Zustand | ^4.5.5 | Auth, theme, UI preferences |
| Routing | React Router DOM | ^6.26.2 | SPA navigation |
| Forms | React Hook Form + Zod | ^7.53 / ^3.23 | Validation & form state |
| Tables | TanStack React Table | ^8.20.5 | Virtual/sortable data tables |
| 3D Visualization | Cesium + Resium | ^1.122 / ^1.18 | Orbit viewer (globe) |
| Charts | Recharts | ^2.12.7 | Dashboard charts |
| HTTP Client | Axios | ^1.7.7 | API requests |
| Auth Provider | Supabase JS | ^2.100.0 | Authentication & session |
| Error Tracking | Sentry React | ^8.55.0 | Runtime error reporting |
| Testing | Vitest + Testing Library | ^2.1 / ^16.0 | Unit & component tests |

---

## Dev Server

```
Port:   3000          (configured in vite.config.ts)
Proxy:  /api  -->  http://localhost:8000
URL:    http://localhost:3000
```

Start commands:

```bash
cd UCT-Benchmark-DMR/combined/frontend

npm install        # install dependencies
npm run dev        # start dev server on port 3000
npm run build      # production build (tsc && vite build)
npm run test       # run vitest
npm run lint       # eslint
```

---

## Routing Architecture

All routes are **flat** (no nested `<Route>` groups for datasets/submit). Three top-level categories exist: standalone pages, the `MainLayout` wrapper (public + authenticated), and a catch-all.

```
App
 |
 |-- ThemeProvider
 |    |-- ErrorBoundary
 |         |-- FeedbackProvider
 |              |-- <Routes>
 |
 |  STANDALONE (no MainLayout)
 |  ────────────────────────────────────────
 |  /                          LandingPage
 |  /welcome                   --> redirect to /
 |  /login                     LoginPage
 |
 |  INSIDE MainLayout
 |  ────────────────────────────────────────
 |  PUBLIC
 |  /docs                      DocumentationPage
 |
 |  AUTHENTICATED (AuthGuard)
 |  /dashboard                 DashboardPage
 |  /leaderboard               LeaderboardPage
 |  /datasets                  DatasetBrowserPage
 |  /datasets/:id              DatasetDetailPage
 |  /datasets/generate         DatasetGeneratorPage
 |  /datasets/my-datasets      MyDatasetsPage
 |  /submit                    SubmitPage
 |  /submit/my-submissions     MySubmissionsPage
 |  /results/:submissionId     ResultsPage
 |  /profile                   ProfilePage
 |  /settings                  SettingsPage
 |
 |  CATCH-ALL
 |  /*                         NotFoundPage
```

Every page component is **lazy-loaded** via `React.lazy()` and wrapped in `<Suspense>` + `<RouteErrorBoundary>` for code splitting and per-route error isolation.

---

## Page Components (15 total)

| # | Component | Route | Auth | Description |
|---|-----------|-------|------|-------------|
| 1 | `LandingPage` | `/` | No | Public landing / marketing page |
| 2 | `LoginPage` | `/login` | No | Supabase authentication |
| 3 | `DocumentationPage` | `/docs` | No | Platform documentation |
| 4 | `DashboardPage` | `/dashboard` | Yes | Overview stats, quick actions |
| 5 | `LeaderboardPage` | `/leaderboard` | Yes | Algorithm rankings |
| 6 | `DatasetBrowserPage` | `/datasets` | Yes | Browse & filter all datasets |
| 7 | `DatasetDetailPage` | `/datasets/:id` | Yes | Single dataset detail view |
| 8 | `DatasetGeneratorPage` | `/datasets/generate` | Yes | Generate new datasets |
| 9 | `MyDatasetsPage` | `/datasets/my-datasets` | Yes | User's own datasets |
| 10 | `SubmitPage` | `/submit` | Yes | Upload algorithm submissions |
| 11 | `MySubmissionsPage` | `/submit/my-submissions` | Yes | User's submission history |
| 12 | `ResultsPage` | `/results/:submissionId` | Yes | Submission scoring results |
| 13 | `ProfilePage` | `/profile` | Yes | User profile |
| 14 | `SettingsPage` | `/settings` | Yes | App & credential settings |
| 15 | `NotFoundPage` | `/*` | No | 404 catch-all |

---

## Component Tree

```
src/
 |-- components/
 |    |-- ui/                        # shadcn/ui primitives (Radix-based)
 |    |    |-- button, input, dialog, select, tabs, toast,
 |    |    |   card, badge, progress, skeleton, table,
 |    |    |   dropdown-menu, tooltip, scroll-area, ...
 |    |
 |    |-- layout/                    # App shell
 |    |    |-- MainLayout.tsx        # Sidebar + Header + <Outlet />
 |    |    |-- Header.tsx            # Top nav bar
 |    |    |-- Sidebar.tsx           # Collapsible side navigation
 |    |
 |    |-- dashboard/                 # Dashboard widgets
 |    |    |-- StatCard.tsx          # Stat with trend indicator
 |    |    |-- QuickActions.tsx      # Primary action buttons
 |    |    |-- RecentSubmissions.tsx # Submission activity feed
 |    |    |-- LeaderboardSnapshot.tsx # Top-5 rankings
 |    |
 |    |-- datasets/                  # Dataset-related
 |    |    |-- DatasetCard.tsx       # Preview card
 |    |    |-- DatasetFilters.tsx    # Filter controls
 |    |    |-- DatasetPreviewDialog.tsx # Detail modal
 |    |
 |    |-- cesium/                    # 3D visualization
 |    |    |-- OrbitViewer.tsx       # Cesium globe + orbit tracks
 |    |
 |    |-- settings/                  # Settings page components
 |    |    |-- CredentialFormDialog.tsx
 |    |    |-- ServiceCredentialCard.tsx
 |    |
 |    |-- generator/                 # Dataset generator
 |    |    |-- DataSourceStatusIndicator.tsx
 |    |
 |    |-- pipeline/                  # Pipeline visualization
 |    |    |-- PipelineVisualizer.tsx
 |    |
 |    |-- feedback/                  # User feedback system
 |    |    |-- FeedbackProvider.tsx  # Context provider
 |    |    |-- FeedbackWidget.tsx    # Floating feedback UI
 |    |
 |    |-- AuthGuard.tsx              # Redirects unauthenticated users
 |    |-- AdminGuard.tsx             # Restricts to admin role
 |    |-- ErrorBoundary.tsx          # App-wide + per-route error boundaries
 |    |-- theme-provider.tsx         # Dark/light theme context
 |
 |-- pages/                         # 15 page components (see table above)
 |-- hooks/                         # Custom React hooks
 |-- stores/                        # Zustand stores
 |-- lib/                           # Utilities, API client
 |-- types/                         # TypeScript type definitions
```

---

## Design Patterns

### 1. Lazy Loading with Error Isolation

Every route is wrapped in `LazyRoute` which combines `<Suspense>` (loading spinner) with `<RouteErrorBoundary>` (per-route crash recovery):

```typescript
function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        {children}
      </Suspense>
    </RouteErrorBoundary>
  );
}
```

### 2. Custom Hooks for Data Fetching

All API calls are encapsulated in custom hooks using React Query:

```typescript
// hooks/useDatasets.ts
export function useDatasets(filters?: DatasetFilters) {
  return useQuery({
    queryKey: ['datasets', filters],
    queryFn: () => api.getDatasets(filters),
  });
}
```

### 3. Type-Safe Props

All components use TypeScript interfaces:

```typescript
interface DatasetCardProps {
  dataset: Dataset;
  onPreview?: (dataset: Dataset) => void;
  onDownload?: (dataset: Dataset) => void;
}
```

### 4. Controlled Forms with Zod

Forms use React Hook Form with Zod schema validation:

```typescript
const schema = z.object({
  algorithmName: z.string().min(1),
  version: z.string().min(1),
  datasetId: z.string().min(1),
});

function SubmitForm() {
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  });
}
```

---

## State Management

### Server State -- React Query

- Automatic caching with configurable stale times
- Background refetching
- Optimistic updates for mutations
- Query invalidation on related mutations

### Client State -- Zustand

- Auth session (user, token) persisted to localStorage
- Theme preference (dark/light)
- UI preferences

```typescript
// stores/authStore.ts
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      login: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
);
```

---

## Styling Architecture

### Tailwind CSS + CSS Variables (theming)

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 221.2 83.2% 53.3%;
}
.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
}
```

### Class Variance Authority (CVA)

Component variants are defined declaratively:

```typescript
const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        outline: 'border border-input bg-background',
        ghost: 'hover:bg-accent',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-8',
      },
    },
  }
);
```

---

## Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(version || 'unknown'),
  },
  plugins: [react(), cesium()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: ['e2e/**', 'node_modules/**'],
  },
});
```

Path alias `@/` maps to `src/` for clean imports:

```typescript
import { Button } from '@/components/ui/button';
import { useDatasets } from '@/hooks/useDatasets';
import type { Dataset } from '@/types';
```

---

## Error Handling

### API Errors

Centralized in Axios interceptors -- 401 responses trigger redirect to login:

```typescript
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
    }
    return Promise.reject(error);
  }
);
```

### UI Error States

React Query provides per-query loading/error states:

```typescript
const { data, isLoading, error } = useDatasets();

if (isLoading) return <Skeleton />;
if (error) return <ErrorMessage error={error} />;
return <DatasetList data={data} />;
```

---

## Performance

1. **Code Splitting** -- Every page is `React.lazy()` loaded; heavy deps (Cesium ~1.4 MB, Recharts ~260 KB) only load when their route is visited
2. **Memoization** -- `useMemo` / `useCallback` for expensive computations
3. **Virtual Tables** -- TanStack Table for large data sets
4. **Bundle Output** -- `dist/` with source maps disabled in production

---

## Related Documentation

- [Backend API](BACKEND_API.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Getting Started](../getting-started.md)
