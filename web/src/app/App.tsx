import { useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/auth-store';
import { useFeatureFlags } from '@/lib/feature-flags';
import { apiFetch } from '@/lib/api';
import { LoginPage } from '@/pages/LoginPage';
import { SignupPage } from '@/pages/SignupPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { AssessmentsPage } from '@/pages/AssessmentsPage';
import { AssessmentDetailPage } from '@/pages/AssessmentDetailPage';
import { AssessmentNewPage } from '@/pages/AssessmentNewPage';
import { ClassesPage } from '@/pages/ClassesPage';
import { ClassDetailPage } from '@/pages/ClassDetailPage';
import { ScoreEntryPage } from '@/pages/ScoreEntryPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { PrivacyPolicyPage } from '@/pages/PrivacyPolicyPage';
import { AITransparencyPage } from '@/pages/AITransparencyPage';
import { AdminDashboardPage } from '@/pages/AdminDashboardPage';
import { RoadmapPage } from '@/pages/RoadmapPage';
import { BillingPage } from '@/pages/BillingPage';
import { ReportCardPage } from '@/pages/ReportCardPage';
import { Layout } from '@/components/Layout';
import { ProtectedRoute } from '@/components/ProtectedRoute';

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
      <CapacitorBackButton />
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
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
      </Routes>
    </>
  );
}
