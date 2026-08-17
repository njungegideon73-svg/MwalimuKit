import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, Users, Plus, BookOpen } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import type { Assessment, SchoolClass } from '@mwalimukit/types';

export function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiFetch<Assessment[]>('/assessments').catch(() => []),
      apiFetch<SchoolClass[]>('/classes').catch(() => []),
    ]).then(([a, c]) => {
      setAssessments(a);
      setClasses(c);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome{user?.full_name ? `, ${user.full_name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-gray-500 mt-1">Here's your teaching overview</p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-primary-50 flex items-center justify-center">
            <ClipboardList className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{assessments.length}</p>
            <p className="text-xs text-gray-500">Assessments</p>
          </div>
        </div>
        <div className="card flex items-center gap-4">
          <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
            <Users className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{classes.length}</p>
            <p className="text-xs text-gray-500">Classes</p>
          </div>
        </div>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          to="/assessments/new"
          className="card group hover:border-primary-300 hover:shadow-md transition-all flex items-center gap-4"
        >
          <div className="h-12 w-12 rounded-xl bg-primary-500 flex items-center justify-center group-hover:bg-primary-600 transition-colors">
            <Plus className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">New assessment</p>
            <p className="text-sm text-gray-500">Generate from a KICD strand or use a template</p>
          </div>
        </Link>
        <Link
          to="/classes"
          className="card group hover:border-primary-300 hover:shadow-md transition-all flex items-center gap-4"
        >
          <div className="h-12 w-12 rounded-xl bg-accent-400 flex items-center justify-center group-hover:bg-accent-500 transition-colors">
            <BookOpen className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Manage classes</p>
            <p className="text-sm text-gray-500">Add learners, enter scores, track progress</p>
          </div>
        </Link>
      </div>

      {/* Recent assessments */}
      {assessments.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Recent assessments</h2>
          <div className="space-y-2">
            {assessments.slice(0, 5).map((a) => (
              <Link
                key={a.id}
                to={`/assessments/${a.id}`}
                className="flex items-center justify-between rounded-lg bg-white border border-gray-200 px-4 py-3 hover:border-primary-300 transition-colors"
              >
                <div>
                  <p className="font-medium text-gray-900">{a.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="badge-primary">{a.learning_area_code}</span>
                    {a.strand_code && <span className="badge-gray">{a.strand_code}</span>}
                    <span className={`badge ${a.source === 'ai' ? 'badge-accent' : 'badge-gray'}`}>
                      {a.source === 'ai' ? 'AI' : 'Manual'}
                    </span>
                  </div>
                </div>
                <span className="text-xs text-gray-400">
                  {new Date(a.created_at).toLocaleDateString()}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {assessments.length === 0 && classes.length === 0 && (
        <div className="card text-center py-12">
          <ClipboardList className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No assessments yet</p>
          <Link to="/assessments/new" className="btn-primary mt-4 inline-flex">
            <Plus className="h-4 w-4" /> Create your first assessment
          </Link>
        </div>
      )}
    </div>
  );
}
