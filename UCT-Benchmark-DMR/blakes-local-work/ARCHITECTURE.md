# SpOC Frontend Architecture

## Overview

The SpOC frontend follows a modern React architecture with clear separation of concerns, type safety, and scalable patterns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     React App (Vite)                      │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   Pages     │  │  Components │  │    Hooks        │  │  │
│  │  │             │  │             │  │                 │  │  │
│  │  │ - Dashboard │  │ - UI (20+)  │  │ - useDatasets   │  │  │
│  │  │ - Datasets  │  │ - Layout    │  │ - useSubmissions│  │  │
│  │  │ - Submit    │  │ - Dashboard │  │ - useLeaderboard│  │  │
│  │  │ - Results   │  │ - Datasets  │  │ - useToast      │  │  │
│  │  │ - Leaderbd  │  │ - Cesium    │  │                 │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │  │
│  │         │                │                   │           │  │
│  │         └────────────────┼───────────────────┘           │  │
│  │                          │                               │  │
│  │  ┌───────────────────────┴───────────────────────────┐  │  │
│  │  │              State Management                      │  │  │
│  │  │                                                    │  │  │
│  │  │  ┌────────────────┐    ┌────────────────────┐    │  │  │
│  │  │  │  React Query   │    │      Zustand       │    │  │  │
│  │  │  │ (Server State) │    │  (Client State)    │    │  │  │
│  │  │  │                │    │                    │    │  │  │
│  │  │  │ - datasets     │    │ - auth             │    │  │  │
│  │  │  │ - submissions  │    │ - theme            │    │  │  │
│  │  │  │ - leaderboard  │    │ - ui preferences   │    │  │  │
│  │  │  └────────────────┘    └────────────────────┘    │  │  │
│  │  └────────────────────────┬──────────────────────────┘  │  │
│  │                           │                              │  │
│  │  ┌────────────────────────┴─────────────────────────┐   │  │
│  │  │                 API Client (Axios)                │   │  │
│  │  │  - Request/Response interceptors                  │   │  │
│  │  │  - Auth token injection                           │   │  │
│  │  │  - Error handling                                 │   │  │
│  │  └────────────────────────┬─────────────────────────┘   │  │
│  │                           │                              │  │
│  └───────────────────────────┼──────────────────────────────┘  │
│                              │                                  │
└──────────────────────────────┼──────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Backend API      │
                    │  (FastAPI - TBD)    │
                    └─────────────────────┘
```

## Design Patterns

### 1. Component Composition

Components are built using composition patterns with clear boundaries:

```typescript
// Page-level component
function DatasetBrowserPage() {
  return (
    <div>
      <DatasetFilters />        {/* Filter controls */}
      <DatasetGrid>             {/* Layout container */}
        {datasets.map(d => (
          <DatasetCard />       {/* Presentation component */}
        ))}
      </DatasetGrid>
      <DatasetPreviewDialog />  {/* Modal component */}
    </div>
  );
}
```

### 2. Custom Hooks for Data Fetching

All API calls are encapsulated in custom hooks:

```typescript
// hooks/useDatasets.ts
export function useDatasets(filters?: DatasetFilters) {
  return useQuery({
    queryKey: ['datasets', filters],
    queryFn: () => api.getDatasets(filters),
  });
}

// Usage in components
function DatasetBrowserPage() {
  const { data, isLoading, error } = useDatasets(filters);
  // ...
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

function DatasetCard({ dataset, onPreview, onDownload }: DatasetCardProps) {
  // ...
}
```

### 4. Controlled Forms

Forms use React Hook Form with Zod validation:

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
  // ...
}
```

## State Management Strategy

### Server State (React Query)

For data that comes from the API:
- Automatic caching with configurable stale times
- Background refetching
- Optimistic updates for mutations
- Query invalidation on related mutations

### Client State (Zustand)

For UI and auth state:
- Persisted to localStorage (auth token, theme)
- Simple, minimal stores
- No boilerplate

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

## Routing Architecture

```typescript
// App.tsx - Route configuration
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/" element={<MainLayout />}>
    <Route index element={<DashboardPage />} />
    <Route path="datasets">
      <Route index element={<DatasetBrowserPage />} />
      <Route path="generate" element={<DatasetGeneratorPage />} />
      <Route path="my-datasets" element={<MyDatasetsPage />} />
    </Route>
    <Route path="submit">
      <Route index element={<SubmitPage />} />
      <Route path="my-submissions" element={<MySubmissionsPage />} />
    </Route>
    <Route path="results/:submissionId" element={<ResultsPage />} />
    <Route path="leaderboard" element={<LeaderboardPage />} />
    <Route path="docs" element={<DocumentationPage />} />
    <Route path="profile" element={<ProfilePage />} />
  </Route>
</Routes>
```

## Styling Architecture

### Tailwind CSS + CSS Variables

```css
/* Global CSS variables for theming */
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 221.2 83.2% 53.3%;
  /* ... */
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  /* ... */
}
```

### Component Styling with CVA

```typescript
// Class Variance Authority for component variants
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

## Build & Bundle

### Vite Configuration

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react(), cesium()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
});
```

### Path Aliases

Using `@/` prefix for clean imports:
```typescript
import { Button } from '@/components/ui/button';
import { useDatasets } from '@/hooks/useDatasets';
import type { Dataset } from '@/types';
```

## Error Handling

### API Errors

Centralized error handling in Axios interceptors:
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

React Query provides loading/error states:
```typescript
const { data, isLoading, error } = useDatasets();

if (isLoading) return <Skeleton />;
if (error) return <ErrorMessage error={error} />;
return <DatasetList data={data} />;
```

## Performance Considerations

1. **Code Splitting** - Route-based lazy loading (to be implemented)
2. **Memoization** - useMemo/useCallback for expensive operations
3. **Virtual Lists** - For large data tables (TanStack Table)
4. **Image Optimization** - Lazy loading, proper sizing
5. **Bundle Analysis** - Vite build analyzer

## Testing Strategy (To Be Implemented)

1. **Unit Tests** - Vitest for hooks and utilities
2. **Component Tests** - React Testing Library
3. **E2E Tests** - Playwright for critical flows
4. **Visual Regression** - Storybook + Chromatic
