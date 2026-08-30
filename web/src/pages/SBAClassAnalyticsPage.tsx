import { useState } from 'react';
import { ArrowLeft, BarChart3, TrendingUp, Users, Trophy } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { SchoolClass } from '@mwalimukit/types';

interface AnalyticsData {
  class_id: string;
  class_name: string;
  academic_year: string;
  subjects: string[];
  exam_types: string[];
  terms: number[];
  subject_averages: Record<string, Record<string, number>>;
  class_average: number;
  top_learners: { name: string; average: number }[];
  bottom_learners: { name: string; average: number }[];
  total_learners: number;
}

export function SBAClassAnalyticsPage() {
  const currentYear = new Date().getFullYear().toString();
  const [selectedClassId, setSelectedClassId] = useState('');
  const [academicYear, setAcademicYear] = useState(currentYear);

  const { data: classes = [] } = useQuery<SchoolClass[]>({
    queryKey: ['classes'],
    queryFn: () => apiFetch('/classes'),
  });

  const { data: analytics, isLoading } = useQuery<AnalyticsData>({
    queryKey: ['sba-analytics', selectedClassId, academicYear],
    queryFn: () => apiFetch(`/term-exams/analytics/class/${selectedClassId}?academic_year=${academicYear}`),
    enabled: !!selectedClassId && !!academicYear,
  });

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/sba" className="btn-ghost text-sm p-1">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Performance Analytics</h1>
          <p className="text-gray-500 mt-1">Class performance breakdown across SBA exams</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="label">Class</label>
            <select className="input" value={selectedClassId} onChange={(e) => setSelectedClassId(e.target.value)}>
              <option value="">Select class...</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Academic Year</label>
            <input className="input w-28" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
          </div>
        </div>
      </div>

      {isLoading && selectedClassId && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-gray-200 rounded-xl animate-pulse" />)}
        </div>
      )}

      {analytics && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="card">
              <Users className="h-5 w-5 text-blue-500 mb-2" />
              <p className="text-2xl font-bold text-gray-900">{analytics.total_learners}</p>
              <p className="text-xs text-gray-500">Learners</p>
            </div>
            <div className="card">
              <BarChart3 className="h-5 w-5 text-amber-500 mb-2" />
              <p className="text-2xl font-bold text-gray-900">{analytics.class_average}%</p>
              <p className="text-xs text-gray-500">Class Average</p>
            </div>
            <div className="card">
              <TrendingUp className="h-5 w-5 text-green-500 mb-2" />
              <p className="text-2xl font-bold text-gray-900">{analytics.subjects.length}</p>
              <p className="text-xs text-gray-500">Subjects</p>
            </div>
            <div className="card">
              <Trophy className="h-5 w-5 text-purple-500 mb-2" />
              <p className="text-2xl font-bold text-gray-900">{analytics.top_learners[0]?.average ?? 0}%</p>
              <p className="text-xs text-gray-500">Top Score</p>
            </div>
          </div>

          {/* Subject averages table */}
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-4">Subject Performance by Exam Type</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 px-3 font-medium">Subject</th>
                    {analytics.exam_types.map((et) => (
                      <th key={et} className="text-center py-2 px-3 font-medium capitalize">{et}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {analytics.subjects.map((subject) => (
                    <tr key={subject} className="border-b border-gray-100">
                      <td className="py-2 px-3 font-medium">{subject}</td>
                      {analytics.exam_types.map((et) => {
                        const avg = analytics.subject_averages[subject]?.[et];
                        // Color coding aligned with CBC grading bands:
                        // EE (Exceeding): >=75%, ME (Meeting): >=41%, AE (Approaching): >=21%, BE (Below): <21%
                        const color =
                          avg !== undefined
                            ? avg >= 75 ? 'text-green-600' : avg >= 41 ? 'text-blue-600' : avg >= 21 ? 'text-amber-600' : 'text-red-600'
                            : '';
                        return (
                          <td key={et} className={`py-2 px-3 text-center font-medium ${color}`}>
                            {avg !== undefined ? `${avg}%` : '-'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Top & Bottom learners */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="card">
              <h2 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Trophy className="h-4 w-4 text-amber-500" /> Top Performers
              </h2>
              {analytics.top_learners.length === 0 ? (
                <p className="text-sm text-gray-500">No data</p>
              ) : (
                <div className="space-y-2">
                  {analytics.top_learners.map((l, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-50">
                      <div className="flex items-center gap-2">
                        <span className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                          i === 0 ? 'bg-amber-500' : i === 1 ? 'bg-gray-400' : i === 2 ? 'bg-amber-700' : 'bg-gray-300 text-gray-600'
                        }`}>
                          {i + 1}
                        </span>
                        <span className="text-sm font-medium">{l.name}</span>
                      </div>
                      <span className="text-sm font-bold text-green-600">{l.average}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card">
              <h2 className="font-semibold text-gray-900 mb-3">Needs Improvement</h2>
              {analytics.bottom_learners.length === 0 ? (
                <p className="text-sm text-gray-500">No data</p>
              ) : (
                <div className="space-y-2">
                  {analytics.bottom_learners.map((l, i) => (
                    <div key={i} className="flex items-center justify-between py-1.5 border-b border-gray-50">
                      <span className="text-sm font-medium">{l.name}</span>
                      <span className="text-sm font-bold text-red-600">{l.average}%</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {!selectedClassId && !isLoading && (
        <div className="card text-center py-12">
          <BarChart3 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">Select a class to view performance analytics</p>
        </div>
      )}
    </div>
  );
}
