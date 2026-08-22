import { lazy, Suspense, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/auth-store';
import { useFeatureFlags } from '@/lib/feature-flags';
import { apiFetch } from '@/lib/api';
import { useSessionTimeout } from '@/hooks/useSessionTimeout';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { RoleBasedRoute } from '@/components/RoleBasedRoute';

// Route-level code splitting: every page is loaded on demand so the initial
// bundle stays small on low-bandwidth connections.
const LoginPage = lazy(() => import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage })));
const SignupPage = lazy(() => import('@/pages/SignupPage').then((m) => ({ default: m.SignupPage })));
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const AssessmentsPage = lazy(() => import('@/pages/AssessmentsPage').then((m) => ({ default: m.AssessmentsPage })));
const AssessmentDetailPage = lazy(() =>
  import('@/pages/AssessmentDetailPage').then((m) => ({ default: m.AssessmentDetailPage })),
);
const AssessmentNewPage = lazy(() =>
  import('@/pages/AssessmentNewPage').then((m) => ({ default: m.AssessmentNewPage })),
);
const ClassesPage = lazy(() => import('@/pages/ClassesPage').then((m) => ({ default: m.ClassesPage })));
const ClassDetailPage = lazy(() => import('@/pages/ClassDetailPage').then((m) => ({ default: m.ClassDetailPage })));
const ScoreEntryPage = lazy(() => import('@/pages/ScoreEntryPage').then((m) => ({ default: m.ScoreEntryPage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const PrivacyPolicyPage = lazy(() =>
  import('@/pages/PrivacyPolicyPage').then((m) => ({ default: m.PrivacyPolicyPage })),
);
const AITransparencyPage = lazy(() =>
  import('@/pages/AITransparencyPage').then((m) => ({ default: m.AITransparencyPage })),
);
const AdminDashboardPage = lazy(() =>
  import('@/pages/AdminDashboardPage').then((m) => ({ default: m.AdminDashboardPage })),
);
const RoadmapPage = lazy(() => import('@/pages/RoadmapPage').then((m) => ({ default: m.RoadmapPage })));
const BillingPage = lazy(() => import('@/pages/BillingPage').then((m) => ({ default: m.BillingPage })));
const ReportCardPage = lazy(() => import('@/pages/ReportCardPage').then((m) => ({ default: m.ReportCardPage })));
const SBADashboardPage = lazy(() =>
  import('@/pages/SBADashboardPage').then((m) => ({ default: m.SBADashboardPage })),
);
const SBAMarksEntryPage = lazy(() =>
  import('@/pages/SBAMarksEntryPage').then((m) => ({ default: m.SBAMarksEntryPage })),
);
const SBAReportCardPage = lazy(() =>
  import('@/pages/SBAReportCardPage').then((m) => ({ default: m.SBAReportCardPage })),
);
const SBAClassAnalyticsPage = lazy(() =>
  import('@/pages/SBAClassAnalyticsPage').then((m) => ({ default: m.SBAClassAnalyticsPage })),
);

// Admin Console Pages
const SuperAdminDashboardPage = lazy(() =>
  import('@/pages/admin/SuperAdminDashboardPage').then((m) => ({ default: m.SuperAdminDashboardPage })),
);
const SchoolsManagementPage = lazy(() =>
  import('@/pages/admin/SchoolsManagementPage').then((m) => ({ default: m.SchoolsManagementPage })),
);
const UsersManagementPage = lazy(() =>
  import('@/pages/admin/UsersManagementPage').then((m) => ({ default: m.UsersManagementPage })),
);
const LearnersManagementPage = lazy(() =>
  import('@/pages/admin/LearnersManagementPage').then((m) => ({ default: m.LearnersManagementPage })),
);
const SystemSettingsPage = lazy(() =>
  import('@/pages/admin/SystemSettingsPage').then((m) => ({ default: m.SystemSettingsPage })),
);

// School Admin Pages
const SchoolAdminDashboardPage = lazy(() =>
  import('@/pages/school-admin/SchoolAdminDashboardPage').then((m) => ({
    default: m.SchoolAdminDashboardPage,
  })),
);
const TeachersManagementPage = lazy(() =>
  import('@/pages/school-admin/TeachersManagementPage').then((m) => ({
    default: m.TeachersManagementPage,
  })),
);
const SchoolLearnersManagementPage = lazy(() =>
  import('@/pages/school-admin/SchoolLearnersManagementPage').then((m) => ({
    default: m.SchoolLearnersManagementPage,
  })),
);
const SchoolClassesManagementPage = lazy(() =>
  import('@/pages/school-admin/SchoolClassesManagementPage').then((m) => ({
    default: m.SchoolClassesManagementPage,
  })),
);

function PageFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
    </div>
  );
}

function InactivityModal() {
  const { isWarning, countdown, dismissWarning } = useSessionTimeout({
    onTimeout: () => {
      window.location.href = '/login';
    },
  });
  const logout = useAuthStore((s) => s.logout);

  if (!isWarning) return null;

  const minutes = Math.floor(countdown / 60);
  const seconds = countdown % 60;

  const handleStayLoggedIn = () => {
    dismissWarning();
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Session Timeout Warning</h2>
        <p className="text-gray-600 mb-4">
          You have been inactive for 30 minutes. For your security, you will be automatically logged out in{' '}
          <span className="font-bold text-red-600">{minutes}:{seconds.toString().padStart(2, '0')}</span>.
        </p>
        <div className="flex gap-3">
          <button onClick={handleStayLoggedIn} className="btn-primary flex-1">
            Stay Logged In
          </button>
          <button onClick={handleLogout} className="btn-secondary flex-1">
            Log Out Now
          </button>
        </div>
      </div>
    </div>
  );
}

function CapacitorBackButton() {
  const navigate = useNavigate();

  useEffect(() => {
    let removeListener: (() => void) | undefined;

    const setup = async () => {
      try {
        const capacitor = await import('@capacitor/app');
        const listener = await capacitor.App.addListener('backButton', ({ canGoBack }) => {
          if (canGoBack) {
            navigate(-1);
          } else {
            capacitor.App.exitApp();
          }
        });
        removeListener = () => { listener.remove(); };
      } catch {
        // Not in Capacitor
      }
    };

    setup();

    return () => {
      removeListener?.();
    };
  }, [navigate]);

  return null;
}

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const isLoading = useAuthStore((s) => s.isLoading);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const setFlags = useFeatureFlags((s) => s.setFlags);

  useSessionTimeout({
    onTimeout: () => {
      window.location.href = '/login';
    },
  });

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const { data: flags } = useQuery({
    queryKey: ['feature-flags'],
    queryFn: () => apiFetch('/feature-flags'),
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (flags) setFlags(flags as any);
  }, [flags, setFlags]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
      </div>
    );
  }

  return (
    <>
      <InactivityModal />
      <CapacitorBackButton />
      <Suspense fallback={<PageFallback />}>
        <Routes>
        <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/assessments" element={<AssessmentsPage />} />
                <Route path="/assessments/new" element={<AssessmentNewPage />} />
                <Route path="/assessments/:id" element={<AssessmentDetailPage />} />
                <Route path="/classes" element={<ClassesPage />} />
                <Route path="/classes/:id" element={<ClassDetailPage />} />
                <Route path="/classes/:classId/scores/:assessmentId" element={<ScoreEntryPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/privacy" element={<PrivacyPolicyPage />} />
                <Route path="/ai-transparency" element={<AITransparencyPage />} />
                <Route path="/admin" element={<AdminDashboardPage />} />
                <Route path="/roadmap" element={<RoadmapPage />} />
                <Route path="/billing" element={<BillingPage />} />
                <Route path="/reports/learner/:learnerId" element={<ReportCardPage />} />

                {/* SBA Routes */}
                <Route path="/sba" element={<SBADashboardPage />} />
                <Route path="/sba/marks/:examId" element={<SBAMarksEntryPage />} />
                <Route path="/sba/report-card" element={<SBAReportCardPage />} />
                <Route path="/sba/analytics" element={<SBAClassAnalyticsPage />} />

                {/* Super Admin Routes */}
                <Route
                  path="/super-admin"
                  element={
                    <RoleBasedRoute allowedRoles={['super_admin']}>
                      <SuperAdminDashboardPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/super-admin/schools"
                  element={
                    <RoleBasedRoute allowedRoles={['super_admin']}>
                      <SchoolsManagementPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/super-admin/users"
                  element={
                    <RoleBasedRoute allowedRoles={['super_admin']}>
                      <UsersManagementPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/super-admin/learners"
                  element={
                    <RoleBasedRoute allowedRoles={['super_admin']}>
                      <LearnersManagementPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/super-admin/settings"
                  element={
                    <RoleBasedRoute allowedRoles={['super_admin']}>
                      <SystemSettingsPage />
                    </RoleBasedRoute>
                  }
                />

                {/* School Admin Routes */}
                <Route
                  path="/school-admin"
                  element={
                    <RoleBasedRoute allowedRoles={['school_admin', 'super_admin']}>
                      <SchoolAdminDashboardPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/school-admin/teachers"
                  element={
                    <RoleBasedRoute allowedRoles={['school_admin', 'super_admin']}>
                      <TeachersManagementPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/school-admin/learners"
                  element={
                    <RoleBasedRoute allowedRoles={['school_admin', 'super_admin']}>
                      <SchoolLearnersManagementPage />
                    </RoleBasedRoute>
                  }
                />
                <Route
                  path="/school-admin/classes"
                  element={
                    <RoleBasedRoute allowedRoles={['school_admin', 'super_admin']}>
                      <SchoolClassesManagementPage />
                    </RoleBasedRoute>
                  }
                />

                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
      </Routes>
      </Suspense>
    </>
  );
}
