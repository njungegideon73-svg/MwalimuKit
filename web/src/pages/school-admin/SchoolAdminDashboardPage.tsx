import { Users, GraduationCap, BookOpen, Shield } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

interface SchoolStats {
  total_teachers: number;
  total_learners: number;
  total_classes: number;
}

const stats = [
  { key: 'total_teachers', label: 'Teachers', icon: Users, color: 'bg-blue-50 text-blue-600' },
  { key: 'total_learners', label: 'Learners', icon: GraduationCap, color: 'bg-green-50 text-green-600' },
  { key: 'total_classes', label: 'Classes', icon: BookOpen, color: 'bg-purple-50 text-purple-600' },
] as const;

export function SchoolAdminDashboardPage() {
  const user = useAuthStore((s) => s.user);

  const { data, isLoading } = useQuery<SchoolStats>({
    queryKey: ['school-admin-stats'],
    queryFn: () => apiFetch('/school-admin/stats'),
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
          <Shield className="h-5 w-5 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">School Dashboard</h1>
          <p className="text-sm text-gray-500">Manage teachers, learners, and classes for your school</p>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((s) => (
          <div key={s.key} className="card flex items-center gap-3">
            <div className={`h-10 w-10 rounded-lg flex items-center justify-center ${s.color}`}>
              <s.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{data?.[s.key] ?? 0}</p>
              <p className="text-xs text-gray-500">{s.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="/school-admin/teachers"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <Users className="h-5 w-5 text-primary-600" />
            <div>
              <p className="font-medium text-gray-900">Manage Teachers</p>
              <p className="text-sm text-gray-500">Add, edit, or remove teachers</p>
            </div>
          </a>
          <a
            href="/school-admin/learners"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <GraduationCap className="h-5 w-5 text-primary-600" />
            <div>
              <p className="font-medium text-gray-900">Manage Learners</p>
              <p className="text-sm text-gray-500">Add, edit, or remove learners</p>
            </div>
          </a>
          <a
            href="/school-admin/classes"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <BookOpen className="h-5 w-5 text-primary-600" />
            <div>
              <p className="font-medium text-gray-900">Manage Classes</p>
              <p className="text-sm text-gray-500">Add, edit, or remove classes</p>
            </div>
          </a>
        </div>
      </div>

      {/* School Info */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">School Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-gray-50">
            <p className="text-sm text-gray-500">School Name</p>
            <p className="text-lg font-semibold text-gray-900">{user?.school_id ? 'Your School' : 'Not Assigned'}</p>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <p className="text-sm text-gray-500">Your Role</p>
            <p className="text-lg font-semibold text-gray-900">School Administrator</p>
          </div>
        </div>
      </div>
    </div>
  );
}
