import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Trash2, CalendarRange } from 'lucide-react';
import { useSchemes, useDeleteScheme } from '@/features/schemes/hooks';

export function SchemesOfWorkPage() {
  const [search, setSearch] = useState('');
  const { data: schemes = [], isLoading } = useSchemes();
  const deleteMutation = useDeleteScheme();

  const filtered = schemes.filter((s) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.sub_strand_code.toLowerCase().includes(q) ||
      s.learning_area_code.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Schemes of Work</h1>
          <p className="text-gray-500 text-sm mt-1">
            Week-by-week lesson plans built from the content bank
          </p>
        </div>
        <Link to="/schemes/new" className="btn-primary">
          <Plus className="h-4 w-4" /> New scheme
        </Link>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search by name, sub-strand..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input pl-10"
        />
      </div>

      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-12">
          <CalendarRange className="h-10 w-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">
            {search ? 'No schemes match your search' : 'No schemes of work yet'}
          </p>
          {!search && (
            <Link to="/schemes/new" className="btn-primary mt-4 inline-flex">
              <Plus className="h-4 w-4" /> Create your first scheme
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between rounded-xl bg-white border border-gray-200 px-4 py-3 hover:border-primary-300 transition-colors"
            >
              <Link to={`/schemes/${s.id}/preview`} className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{s.name}</p>
                <div className="flex items-center gap-2 mt-1 flex-wrap">
                  <span className="badge-primary">{s.learning_area_code}</span>
                  <span className="badge-gray">{s.sub_strand_code}</span>
                  <span className="badge-gray">Grade {s.grade}</span>
                  <span className={`badge ${s.term_number === 3 ? 'badge-accent' : 'badge-gray'}`}>
                    Term {s.term_number}
                  </span>
                  <span className="text-xs text-gray-400">
                    {s.total_weeks} wks &middot; {s.lessons_per_week} lessons/wk
                  </span>
                </div>
              </Link>
              <button
                onClick={() => {
                  if (confirm('Delete this scheme of work?')) deleteMutation.mutate(s.id);
                }}
                className="p-2 text-gray-400 hover:text-red-600 transition-colors"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}