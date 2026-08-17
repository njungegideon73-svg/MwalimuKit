import { Users, BookOpen, ClipboardList, Play, BarChart3 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';

interface DashboardData {
  total_learners: number;
  total_classes: number;
  total_assessments: number;
  total_runs: number;
  total_scores: number;
  recent_assessments: { id: string; name: string; created_at: string }[];
  recent_runs: { id: string; class_name: string; assessment_name: string; started_at: string }[];
}

const stats = [
  { key: 'total_learners', label: 'Total Learners', icon: Users, color: 'bg-primary-50 text-primary-600' },
  { key: 'total_classes', label: 'Total Classes', icon: BookOpen, color: 'bg-blue-50 text-blue-600' },
  { key: 'total_assessments', label: 'Total Assessments', icon: ClipboardList, color: 'bg-green-50 text-green-600' },
  { key: 'total_runs', label: 'Total Runs', icon: Play, color: 'bg-purple-50 text-purple-600' },
  { key: 'total_scores', label: 'Total Scores', icon: BarChart3, color: 'bg-amber-50 text-amber-600' },
] as const;

export function AdminDashboardPage() {
  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ['admin-dashboard'],
    queryFn: () => apiFetch('/admin/dashboard'),
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
      <div>
        <h1 className="text-2xl font-bold text-gray-900">School Dashboard</h1>
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

      {/* Recent Assessments */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Recent Assessments</h2>
        {data?.recent_assessments?.length ? (
          <div className="space-y-2">
            {data.recent_assessments.map((a) => (
              <div key={a.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5">
                <p className="font-medium text-sm text-gray-900">{a.name}</p>
                <span className="text-xs text-gray-400">{new Date(a.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No assessments yet.</p>
        )}
      </div>

      {/* Recent Runs */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Recent Runs</h2>
        {data?.recent_runs?.length ? (
          <div className="space-y-2">
            {data.recent_runs.map((r) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5">
                <div>
                  <p className="text-sm font-medium text-gray-900">{r.class_name}</p>
                  <p className="text-xs text-gray-500">{r.assessment_name}</p>
                </div>
                <span className="text-xs text-gray-400">{new Date(r.started_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No runs yet.</p>
        )}
      </div>
    </div>
  );
}
