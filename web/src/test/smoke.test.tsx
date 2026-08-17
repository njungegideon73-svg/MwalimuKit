import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn(), dismiss: vi.fn() },
}));

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn().mockResolvedValue({}),
  saveTokens: vi.fn(),
  clearTokens: vi.fn(),
  getTokens: vi.fn().mockReturnValue({ access: 'mock', refresh: 'mock' }),
}));

vi.mock('@/lib/db', () => ({
  db: {
    delete: vi.fn(),
    learning_areas: { toArray: vi.fn().mockResolvedValue([]), clear: vi.fn(), bulkPut: vi.fn() },
    strands: { toArray: vi.fn().mockResolvedValue([]), clear: vi.fn(), bulkPut: vi.fn() },
    sub_strands: { toArray: vi.fn().mockResolvedValue([]), clear: vi.fn(), bulkPut: vi.fn() },
    assessments: { toArray: vi.fn().mockResolvedValue([]), where: vi.fn().mockReturnValue({ equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }) }) },
    classes: { toArray: vi.fn().mockResolvedValue([]) },
    learners: { toArray: vi.fn().mockResolvedValue([]) },
    runs: { add: vi.fn(), toArray: vi.fn().mockResolvedValue([]) },
    scores: { put: vi.fn(), where: vi.fn().mockReturnValue({ equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }) }) },
  },
  syncCurriculum: vi.fn(),
}));

const mockAuthState = {
  user: { id: '1', school_id: 's1', email: 'teacher@test.com', full_name: 'Test Teacher', role: 'teacher' as const },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(),
  signup: vi.fn(),
  logout: vi.fn(),
  hydrate: vi.fn(),
};

vi.mock('@/lib/auth-store', () => ({
  useAuthStore: vi.fn((selector: unknown) => (typeof selector === 'function' ? selector(mockAuthState) : mockAuthState)),
}));

vi.mock('@/lib/feature-flags', () => ({
  useFeatureFlags: vi.fn((selector: unknown) =>
    typeof selector === 'function'
      ? selector({ paywall_enabled: false, ai_generation_enabled: true, max_classes: null, max_learners_per_class: null, loaded: true, setFlags: vi.fn() })
      : { paywall_enabled: false, ai_generation_enabled: true, max_classes: null, max_learners_per_class: null, loaded: true, setFlags: vi.fn() }
  ),
}));

vi.mock('@/lib/curriculum', () => ({
  getCurriculum: vi.fn().mockResolvedValue({
    learning_areas: [{ code: 'MAT', name: 'Mathematics', level: 'lower_primary', sort_order: 1 }],
    strands: [{ code: 'MAT-LP-01', learning_area_code: 'MAT', name: 'Numbers', sort_order: 1 }],
    sub_strands: [{ code: 'MAT-LP-01-01', strand_code: 'MAT-LP-01', name: 'Counting', sort_order: 1 }],
  }),
  getCachedCurriculum: vi.fn(),
  invalidateCurriculumCache: vi.fn(),
}));

import { LoginPage } from '@/pages/LoginPage';
import { SignupPage } from '@/pages/SignupPage';
import { AssessmentNewPage } from '@/pages/AssessmentNewPage';

describe('Login page', () => {
  it('renders the login form with email, password, submit button', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('shows sign up link', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: /sign up/i });
    expect(link).toHaveAttribute('href', '/signup');
  });

  it('shows the MwalimuKit logo/brand', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <LoginPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('MK')).toBeInTheDocument();
    expect(screen.getByText('Sign in to MwalimuKit')).toBeInTheDocument();
  });
});

describe('Signup page', () => {
  it('renders signup form with name, email, password, school code fields', () => {
    render(
      <MemoryRouter initialEntries={['/signup']}>
        <SignupPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Full name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
    expect(screen.getByText('Password')).toBeInTheDocument();
    expect(screen.getByText('School code')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('shows offline warning when navigator.onLine is false', () => {
    Object.defineProperty(navigator, 'onLine', { writable: true, value: false });
    render(
      <MemoryRouter initialEntries={['/signup']}>
        <SignupPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/sign-up needs internet/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /offline/i })).toBeDisabled();
    Object.defineProperty(navigator, 'onLine', { writable: true, value: true });
  });

  it('shows sign in link', () => {
    render(
      <MemoryRouter initialEntries={['/signup']}>
        <SignupPage />
      </MemoryRouter>,
    );
    const link = screen.getByRole('link', { name: /sign in/i });
    expect(link).toHaveAttribute('href', '/login');
  });
});

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

function renderWithQuery(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

describe('Assessment new page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  it('renders the form with learning area, strand, sub-strand selects', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/new']}>
        <AssessmentNewPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Choose strand/)).toBeInTheDocument();
    });
    expect(screen.getByText('Learning area')).toBeInTheDocument();
    expect(screen.getByText('Strand')).toBeInTheDocument();
    expect(screen.getByText('Sub-strand')).toBeInTheDocument();
  });

  it('shows mode selector (AI + Manual)', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/new']}>
        <AssessmentNewPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Choose strand/)).toBeInTheDocument();
    });
    expect(screen.getByText('AI draft')).toBeInTheDocument();
    expect(screen.getByText('Structured template')).toBeInTheDocument();
  });

  it('shows search input for strands', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/new']}>
        <AssessmentNewPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/Choose strand/)).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText(/search strands/i)).toBeInTheDocument();
  });
});
