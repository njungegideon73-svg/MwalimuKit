import { useAuthStore } from '@/lib/auth-store';
import { Download, LogOut, Shield, Brain } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { Assessment, SchoolClass, Learner } from '@mwalimukit/types';

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const handleExport = async () => {
    try {
      const [assessments, classes] = await Promise.all([
        apiFetch<Assessment[]>('/assessments').catch(() => [] as Assessment[]),
        apiFetch<SchoolClass[]>('/classes').catch(() => [] as SchoolClass[]),
      ]);

      const allLearners: Learner[] = [];
      for (const cls of classes) {
        try {
          const l = await apiFetch<Learner[]>(`/learners/by-class/${cls.id}`);
          allLearners.push(...l);
        } catch {
          // skip
        }
      }

      const data = {
        exported_at: new Date().toISOString(),
        user: { id: user?.id, email: user?.email, full_name: user?.full_name },
        assessments,
        classes,
        learners: allLearners,
      };

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mwalimukit-export-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Data exported');
    } catch {
      toast.error('Export failed');
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 text-sm mt-1">Manage your account and data</p>
      </div>

      {/* Profile */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Profile</h2>
        <div className="space-y-3">
          <div>
            <label className="label">Name</label>
            <p className="text-sm text-gray-900">{user?.full_name}</p>
          </div>
          <div>
            <label className="label">Email</label>
            <p className="text-sm text-gray-900">{user?.email}</p>
          </div>
          <div>
            <label className="label">Role</label>
            <p className="text-sm text-gray-900 capitalize">{user?.role?.replace('_', ' ')}</p>
          </div>
        </div>
      </div>

      {/* Data */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Your data</h2>
        <button onClick={handleExport} className="btn-secondary">
          <Download className="h-4 w-4" /> Export all my data (JSON)
        </button>
        <p className="text-xs text-gray-500 mt-2">
          Download all your assessments, classes, learners, and scores.
        </p>
      </div>

      {/* Sign out */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Account</h2>
        <button onClick={logout} className="btn-danger">
          <LogOut className="h-4 w-4" /> Sign out
        </button>
      </div>

      {/* Legal & transparency */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Legal & transparency</h2>
        <div className="space-y-2">
          <Link to="/privacy" className="flex items-center gap-2 text-sm text-primary-600 hover:underline">
            <Shield className="h-4 w-4" /> Privacy Policy
          </Link>
          <Link to="/ai-transparency" className="flex items-center gap-2 text-sm text-primary-600 hover:underline">
            <Brain className="h-4 w-4" /> AI Transparency
          </Link>
        </div>
      </div>
    </div>
  );
}
