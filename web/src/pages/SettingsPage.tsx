import { useState } from 'react';
import { useAuthStore } from '@/lib/auth-store';
import { Download, LogOut, Shield, Brain, Key, Building2 } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { Assessment, SchoolClass, Learner } from '@mwalimukit/types';

export function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [changingPw, setChangingPw] = useState(false);

  const [schoolPw, setSchoolPw] = useState('');
  const [newSchoolCode, setNewSchoolCode] = useState('');
  const [changingSchool, setChangingSchool] = useState(false);

  const handleChangePassword = async () => {
    if (newPw !== confirmPw) {
      toast.error('Passwords do not match');
      return;
    }
    if (newPw.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    setChangingPw(true);
    try {
      await apiFetch('/auth/change-password', {
        method: 'POST',
        json: { current_password: currentPw, new_password: newPw },
      });
      toast.success('Password changed');
      setCurrentPw('');
      setNewPw('');
      setConfirmPw('');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to change password');
    } finally {
      setChangingPw(false);
    }
  };

  const handleChangeSchoolCode = async () => {
    if (!newSchoolCode.trim()) {
      toast.error('Enter a school code');
      return;
    }
    setChangingSchool(true);
    try {
      await apiFetch<{ school_id: string }>('/auth/change-school-code', {
        method: 'POST',
        json: { current_password: schoolPw, new_school_code: newSchoolCode.trim() },
      });
      toast.success('School code updated');
      setSchoolPw('');
      setNewSchoolCode('');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to change school code');
    } finally {
      setChangingSchool(false);
    }
  };

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

      {/* Change Password */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Key className="h-4 w-4" /> Change password
        </h2>
        <div className="space-y-3">
          <div>
            <label className="label">Current password</label>
            <input
              type="password"
              className="input"
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              placeholder="Enter current password"
            />
          </div>
          <div>
            <label className="label">New password</label>
            <input
              type="password"
              className="input"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label className="label">Confirm new password</label>
            <input
              type="password"
              className="input"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              placeholder="Repeat new password"
            />
          </div>
          <button
            onClick={handleChangePassword}
            disabled={changingPw || !currentPw || !newPw}
            className="btn-primary"
          >
            {changingPw ? 'Changing...' : 'Change password'}
          </button>
        </div>
      </div>

      {/* Change School Code */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Building2 className="h-4 w-4" /> Change school
        </h2>
        <div className="space-y-3">
          <p className="text-xs text-gray-500">
            Move your account to a different school. Ask your new school admin for the code.
          </p>
          <div>
            <label className="label">New school code</label>
            <input
              className="input"
              value={newSchoolCode}
              onChange={(e) => setNewSchoolCode(e.target.value)}
              placeholder="e.g. NAIROBI01"
            />
          </div>
          <div>
            <label className="label">Confirm password</label>
            <input
              type="password"
              className="input"
              value={schoolPw}
              onChange={(e) => setSchoolPw(e.target.value)}
              placeholder="Enter your password"
            />
          </div>
          <button
            onClick={handleChangeSchoolCode}
            disabled={changingSchool || !newSchoolCode.trim() || !schoolPw}
            className="btn-primary"
          >
            {changingSchool ? 'Updating...' : 'Update school'}
          </button>
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
