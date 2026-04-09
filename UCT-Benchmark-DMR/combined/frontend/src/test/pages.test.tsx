import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { LoginPage } from '@/pages/LoginPage';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { useAuthStore } from '@/stores/authStore';

// Mock supabase
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null }),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
      signInWithPassword: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      resetPasswordForEmail: vi.fn(),
      signInWithOAuth: vi.fn(),
      refreshSession: vi.fn(),
    },
  },
}));

// Mock API client
vi.mock('@/api/client', () => ({
  api: {
    getLeaderboard: vi.fn().mockResolvedValue({ data: { entries: [] } }),
    getLeaderboardStatistics: vi.fn().mockResolvedValue({ data: {} }),
    getSubmissions: vi.fn().mockResolvedValue({ data: [] }),
    getDatasets: vi.fn().mockResolvedValue({ data: [] }),
  },
  apiClient: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

// Mock the __APP_VERSION__ global that LoginPage references
vi.stubGlobal('__APP_VERSION__', '2.0.0');

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      session: null,
      isAuthenticated: false,
      isLoading: false,
      isAdmin: false,
      error: null,
    });
  });

  it('renders email and password fields', () => {
    render(<LoginPage />);

    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('renders sign in button', () => {
    render(<LoginPage />);

    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('renders the platform title', () => {
    render(<LoginPage />);

    expect(screen.getByText('UCT Benchmark')).toBeInTheDocument();
  });

  it('has required attribute on email and password inputs', () => {
    render(<LoginPage />);

    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');

    expect(emailInput).toBeRequired();
    expect(passwordInput).toBeRequired();
  });

  it('shows error from auth store', () => {
    useAuthStore.setState({ error: 'Invalid email or password. Please try again.' });

    render(<LoginPage />);

    expect(screen.getByText('Invalid email or password. Please try again.')).toBeInTheDocument();
  });
});

describe('NotFoundPage', () => {
  it('renders 404 message', () => {
    render(<NotFoundPage />);

    expect(screen.getByText('404')).toBeInTheDocument();
    expect(screen.getByText('Page Not Found')).toBeInTheDocument();
  });

  it('renders descriptive text', () => {
    render(<NotFoundPage />);

    expect(
      screen.getByText('The page you are looking for does not exist or may have been moved.')
    ).toBeInTheDocument();
  });

  it('renders a link to go home', () => {
    render(<NotFoundPage />);

    expect(screen.getByRole('link')).toHaveAttribute('href', '/');
    expect(screen.getByText('Go Home')).toBeInTheDocument();
  });
});

describe('DashboardPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: {
        id: 'test-user',
        username: 'TestResearcher',
        email: 'test@example.com',
        organization: 'Test Org',
        role: 'developer',
        createdAt: '2026-01-01T00:00:00Z',
        submissionCount: 5,
      },
      session: null,
      isAuthenticated: true,
      isLoading: false,
      isAdmin: false,
      error: null,
    });
  });

  it('renders without crashing (smoke test)', () => {
    render(<DashboardPage />);

    // The dashboard should render the welcome section with the user's name
    expect(screen.getByText(/TestResearcher/)).toBeInTheDocument();
  });
});
