import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('react-hot-toast', () => ({
  default: { error: vi.fn(), success: vi.fn(), dismiss: vi.fn() },
}));

vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
  saveTokens: vi.fn(),
  clearTokens: vi.fn(),
  getTokens: vi.fn().mockReturnValue({ access: 'mock', refresh: 'mock' }),
}));

const { mockDb } = vi.hoisted(() => ({
  mockDb: {
    delete: vi.fn(),
    learning_areas: { toArray: vi.fn().mockResolvedValue([]), clear: vi.fn(), bulkPut: vi.fn() },
    strands: { toArray: vi.fn().mockResolvedValue([]), clear: vi.fn(), bulkPut: vi.fn() },
    sub_strands: { toArray: vi.fn().mockResolvedValue([]), clear: vi.fn(), bulkPut: vi.fn() },
    assessments: { toArray: vi.fn().mockResolvedValue([]), where: vi.fn().mockReturnValue({ equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }) }) },
    classes: { toArray: vi.fn().mockResolvedValue([]) },
    learners: { toArray: vi.fn().mockResolvedValue([]) },
    runs: { add: vi.fn(), toArray: vi.fn().mockResolvedValue([]) },
    scores: {
      put: vi.fn(),
      update: vi.fn(),
      toArray: vi.fn().mockResolvedValue([]),
      where: vi.fn().mockReturnValue({
        equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }),
        and: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }),
      }),
    },
  },
}));

vi.mock('@/lib/db', () => ({
  db: mockDb,
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

import { apiFetch } from '@/lib/api';
import { LoginPage } from '@/pages/LoginPage';
import { SignupPage } from '@/pages/SignupPage';
import { AssessmentNewPage } from '@/pages/AssessmentNewPage';
import { AssessmentDetailPage } from '@/pages/AssessmentDetailPage';
import { ClassesPage } from '@/pages/ClassesPage';
import { ClassDetailPage } from '@/pages/ClassDetailPage';
import { ScoreEntryPage } from '@/pages/ScoreEntryPage';

// ── helpers ──────────────────────────────────────────────────────────

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });

function renderWithQuery(ui: React.ReactNode) {
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

const mockAssessment = {
  id: 'a1',
  owner_id: '1',
  school_id: 's1',
  name: 'Maths Check 1',
  description: 'Counting to 20',
  learning_area_code: 'MAT',
  strand_code: 'MAT-LP-01',
  sub_strand_codes: ['MAT-LP-01-01'],
  source: 'ai' as const,
  rubric: {
    levels: [
      { level: 1 as const, label: 'Beginning', descriptor: 'Needs support' },
      { level: 2 as const, label: 'Developing', descriptor: 'With help' },
    ],
    criteria: [],
  },
  items: [
    { id: 'i1', criterion: 'accuracy', stem: 'Count to 5', answer_guide: '5', max_level: 4 as const },
    { id: 'i2', criterion: 'fluency', stem: 'Count backwards from 10', answer_guide: '10,9,8...', max_level: 4 as const },
  ],
  tags: [],
  is_favourite: true,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  deleted_at: null,
};

const mockClasses = [
  { id: 'c1', name: 'Grade 1 Blue', grade_level: 'Grade 1', school_id: 's1', teacher_id: '1', learning_area_codes: [], deleted_at: null, created_at: '2025-01-01', updated_at: '2025-01-01' },
  { id: 'c2', name: 'Grade 3 Red', grade_level: 'Grade 3', school_id: 's1', teacher_id: '1', learning_area_codes: [], deleted_at: null, created_at: '2025-01-02', updated_at: '2025-01-02' },
];

const mockLearners = [
  { id: 'l1', school_id: 's1', class_id: 'c1', full_name: 'Achieng Omondi', admission_no: 'ADM001', gender: 'F', deleted_at: null },
  { id: 'l2', school_id: 's1', class_id: 'c1', full_name: 'Kipchoge Keino', admission_no: 'ADM002', gender: 'M', deleted_at: null },
];

// ── Login page ───────────────────────────────────────────────────────

describe('Login page', () => {
  beforeEach(() => { vi.clearAllMocks(); });

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

// ── Signup page ──────────────────────────────────────────────────────

describe('Signup page', () => {
  beforeEach(() => { vi.clearAllMocks(); });

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

// ── F1: Assessment new page ─────────────────────────────────────────

describe('F1: Assessment new page', () => {
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

// ── F1: Assessment detail page ──────────────────────────────────────

describe('F1: Assessment detail page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    (apiFetch as Mock).mockImplementation(async (path: string) => {
      if (path === '/assessments/a1') return mockAssessment;
      return {};
    });
  });

  it('renders assessment name and badges', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes><Route path="/assessments/:id" element={<AssessmentDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByText('MAT')).toBeInTheDocument();
    expect(screen.getByText('MAT-LP-01')).toBeInTheDocument();
    expect(screen.getByText(/AI draft/i)).toBeInTheDocument();
  });

  it('shows assessment items', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes><Route path="/assessments/:id" element={<AssessmentDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Count to 5')).toBeInTheDocument();
    });
    expect(screen.getByText('Count backwards from 10')).toBeInTheDocument();
    expect(screen.getByText(/Assessment items \(2\)/)).toBeInTheDocument();
  });

  it('shows rubric levels', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes><Route path="/assessments/:id" element={<AssessmentDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Beginning')).toBeInTheDocument();
    });
    expect(screen.getByText('Developing')).toBeInTheDocument();
  });

  it('shows duplicate and delete buttons', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes><Route path="/assessments/:id" element={<AssessmentDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /duplicate/i })).toBeInTheDocument();
    const deleteBtn = screen.getAllByRole('button').find((b) => b.querySelector('svg') && b.className.includes('text-red'));
    expect(deleteBtn).toBeDefined();
  });

  it('shows "Run against a class" link', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes><Route path="/assessments/:id" element={<AssessmentDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    const runLink = screen.getByRole('link', { name: /run against a class/i });
    expect(runLink).toHaveAttribute('href', '/classes');
  });

  it('shows back button', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/assessments/a1']}>
        <Routes><Route path="/assessments/:id" element={<AssessmentDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
  });
});

// ── F2: Classes page ────────────────────────────────────────────────

describe('F2: Classes page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    (apiFetch as Mock).mockImplementation(async (path: string) => {
      if (path === '/classes') return mockClasses;
      return {};
    });
  });

  it('renders heading and new class button', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes']}>
        <ClassesPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Classes')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /new class/i })).toBeInTheDocument();
  });

  it('lists classes with names and grade levels', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes']}>
        <ClassesPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Grade 1 Blue')).toBeInTheDocument();
    });
    expect(screen.getByText('Grade 3 Red')).toBeInTheDocument();
    expect(screen.getByText('Grade 1')).toBeInTheDocument();
    expect(screen.getByText('Grade 3')).toBeInTheDocument();
  });

  it('class items link to detail pages', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes']}>
        <ClassesPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Grade 1 Blue')).toBeInTheDocument();
    });
    const links = screen.getAllByRole('link');
    const classLink = links.find((l) => l.getAttribute('href') === '/classes/c1');
    expect(classLink).toBeDefined();
  });

  it('shows empty state when no classes', async () => {
    (apiFetch as Mock).mockImplementation(async (path: string) => {
      if (path === '/classes') return [];
      return {};
    });
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes']}>
        <ClassesPage />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/no classes yet/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /create your first class/i })).toBeInTheDocument();
  });
});

// ── F2: Class detail page ───────────────────────────────────────────

describe('F2: Class detail page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    (apiFetch as Mock).mockImplementation(async (path: string) => {
      if (path === '/classes/c1') return mockClasses[0];
      if (path === '/learners/by-class/c1') return mockLearners;
      if (path === '/assessments') return [mockAssessment];
      if (path.startsWith('/runs')) return [];
      return {};
    });
  });

  it('renders class name and learner count', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Grade 1 Blue')).toBeInTheDocument();
    });
    expect(screen.getByText(/2 learners/)).toBeInTheDocument();
  });

  it('lists learners by name', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Achieng Omondi')).toBeInTheDocument();
    });
    expect(screen.getByText('Kipchoge Keino')).toBeInTheDocument();
  });

  it('shows Add and Bulk add buttons', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Achieng Omondi')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /^add$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /bulk add/i })).toBeInTheDocument();
  });

  it('shows edit and delete buttons for each learner', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Achieng Omondi')).toBeInTheDocument();
    });
    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
    expect(editButtons.length).toBeGreaterThanOrEqual(2);
    expect(deleteButtons.length).toBeGreaterThanOrEqual(2);
  });

  it('shows assessments available to run', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
  });

  it('shows back button', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Grade 1 Blue')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
  });

  it('shows empty state for learners when none exist', async () => {
    (apiFetch as Mock).mockImplementation(async (path: string) => {
      if (path === '/classes/c1') return mockClasses[0];
      if (path === '/learners/by-class/c1') return [];
      if (path === '/assessments') return [];
      if (path.startsWith('/runs')) return [];
      return {};
    });
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1']}>
        <Routes><Route path="/classes/:id" element={<ClassDetailPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText(/no learners yet/i)).toBeInTheDocument();
    });
  });
});

// ── F3: Score entry page ────────────────────────────────────────────

describe('F3: Score entry page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    mockDb.runs.add.mockResolvedValue(undefined);
    mockDb.scores.put.mockResolvedValue(undefined);
    mockDb.scores.update.mockResolvedValue(undefined);
    mockDb.scores.where.mockReturnValue({
      equals: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }),
      and: vi.fn().mockReturnValue({ toArray: vi.fn().mockResolvedValue([]) }),
    });
    (apiFetch as Mock).mockImplementation(async (path: string) => {
      if (path === '/learners/by-class/c1') return mockLearners;
      if (path === '/assessments/a1') return mockAssessment;
      if (path === '/runs') return {
        id: 'r1', school_id: 's1', class_id: 'c1', assessment_id: 'a1',
        term: null, started_at: '2025-01-01T00:00:00Z', closed_at: null,
      };
      if (path === '/scores/batch') return { synced: 0, conflicts: 0 };
      return {};
    });
  });

  it('renders assessment name and grid dimensions', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1/scores/a1']}>
        <Routes><Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByText(/2 learners × 2 items/i)).toBeInTheDocument();
  });

  it('shows the score entry grid with learners as rows', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1/scores/a1']}>
        <Routes><Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Achieng Omondi')).toBeInTheDocument();
    });
    expect(screen.getByText('Kipchoge Keino')).toBeInTheDocument();
  });

  it('shows item column headers', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1/scores/a1']}>
        <Routes><Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByText(/Item 1/)).toBeInTheDocument();
    expect(screen.getByText(/Item 2/)).toBeInTheDocument();
  });

  it('shows level indicators (L1-L4)', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1/scores/a1']}>
        <Routes><Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getAllByText(/L1/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/L2/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/L3/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/L4/).length).toBeGreaterThanOrEqual(1);
  });

  it('shows back button', async () => {
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1/scores/a1']}>
        <Routes><Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /back/i })).toBeInTheDocument();
  });

  it('loads and renders when offline (network unavailable)', async () => {
    Object.defineProperty(navigator, 'onLine', { writable: true, value: false });
    renderWithQuery(
      <MemoryRouter initialEntries={['/classes/c1/scores/a1']}>
        <Routes><Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} /></Routes>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText('Maths Check 1')).toBeInTheDocument();
    });
    expect(screen.getByText('Achieng Omondi')).toBeInTheDocument();
    expect(screen.getByText('Kipchoge Keino')).toBeInTheDocument();
    Object.defineProperty(navigator, 'onLine', { writable: true, value: true });
  });
});
