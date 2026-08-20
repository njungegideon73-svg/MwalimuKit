import { School, Users, GraduationCap, BookOpen, Shield } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';

interface SystemStats {
  total_schools: number;
  total_users: number;
  total_teachers: number;
  total_school_admins: number;
  total_super_admins: number;
  total_learners: number;
  total_classes: number;
}

const stats = [
  { key: 'total_schools', label: 'Total Schools', icon: School, color: 'bg-blue-50 text-blue-600' },
  { key: 'total_users', label: 'Total Users', icon: Users, color: 'bg-green-50 text-green-600' },
  { key: 'total_teachers', label: 'Teachers', icon: Users, color: 'bg-purple-50 text-purple-600' },
  { key: 'total_learners', label: 'Learners', icon: GraduationCap, color: 'bg-amber-50 text-amber-600' },
  { key: 'total_classes', label: 'Classes', icon: BookOpen, color: 'bg-red-50 text-red-600' },
] as const;

export function SuperAdminDashboardPage() {
  const { data, isLoading } = useQuery<SystemStats>({
    queryKey: ['super-admin-stats'],
    queryFn: () => apiFetch('/super-admin/stats'),
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-red-50 flex items-center justify-center">
          <Shield className="h-5 w-5 text-red-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">System Administration</h1>
          <p className="text-sm text-gray-500">Manage all schools, users, and system settings</p>
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
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
            href="/super-admin/schools"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <School className="h-5 w-5 text-primary-600" />
            <div>
              <p className="font-medium text-gray-900">Manage Schools</p>
              <p className="text-sm text-gray-500">Add, edit, or remove schools</p>
            </div>
          </a>
          <a
            href="/super-admin/users"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <Users className="h-5 w-5 text-primary-600" />
            <div>
              <p className="font-medium text-gray-900">Manage Users</p>
              <p className="text-sm text-gray-500">Add, edit, or remove users</p>
            </div>
          </a>
          <a
            href="/super-admin/learners"
            className="flex items-center gap-3 p-4 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors"
          >
            <GraduationCap className="h-5 w-5 text-primary-600" />
            <div>
              <p className="font-medium text-gray-900">Manage Learners</p>
              <p className="text-sm text-gray-500">Add, edit, or remove learners</p>
            </div>
          </a>
        </div>
      </div>

      {/* System Info */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">System Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-gray-50">
            <p className="text-sm text-gray-500">Super Admins</p>
            <p className="text-lg font-semibold text-gray-900">{data?.total_super_admins ?? 0}</p>
          </div>
          <div className="p-4 rounded-lg bg-gray-50">
            <p className="text-sm text-gray-500">School Admins</p>
            <p className="text-lg font-semibold text-gray-900">{data?.total_school_admins ?? 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
