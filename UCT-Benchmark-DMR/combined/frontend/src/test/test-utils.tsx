import React from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/components/theme-provider'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

interface TestProvidersProps {
  children: React.ReactNode
}

function TestProviders({ children }: TestProvidersProps) {
  const queryClient = createTestQueryClient()

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider defaultTheme="light" storageKey="test-theme">
          {children}
        </ThemeProvider>
      </QueryClientProvider>
    </BrowserRouter>
  )
}

function customRender(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  return render(ui, { wrapper: TestProviders, ...options })
}

// Re-export everything from testing library
export * from '@testing-library/react'
export { customRender as render }

// Mock data factories
export function createMockDataset(overrides: Partial<any> = {}) {
  return {
    id: 1,
    name: 'Test Dataset',
    code: 'LEO_T1',
    tier: 'T1',
    orbital_regime: 'LEO',
    status: 'available',
    observation_count: 1000,
    satellite_count: 5,
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function createMockSubmission(overrides: Partial<any> = {}) {
  return {
    id: 1,
    dataset_id: 1,
    algorithm_name: 'TestAlgo',
    version: '1.0',
    status: 'completed',
    created_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

export function createMockResult(overrides: Partial<any> = {}) {
  return {
    id: 1,
    submission_id: 1,
    true_positives: 850,
    false_positives: 50,
    false_negatives: 100,
    true_negatives: 20,
    precision: 0.944,
    recall: 0.895,
    f1_score: 0.919,
    position_rms_km: 12.5,
    velocity_rms_km_s: 0.025,
    ...overrides,
  }
}

export function createMockUser(overrides: Partial<any> = {}) {
  return {
    id: 'test-user-id',
    email: 'test@example.com',
    role: 'user',
    display_name: 'Test User',
    organization: 'Test Org',
    ...overrides,
  }
}
