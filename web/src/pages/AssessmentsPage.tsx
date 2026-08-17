import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Search, Heart, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';
import type { Assessment } from '@mwalimukit/types';

export function AssessmentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [filterFav, setFilterFav] = useState(false);

  const { data: assessments = [], isLoading } = useQuery<Assessment[]>({
    queryKey: ['assessments'],
    queryFn: () => apiFetch('/assessments'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/assessments/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Assessment deleted');
    },
    onError: () => toast.error('Failed to delete'),
  });

  const filtered = assessments.filter((a) => {
    if (filterFav && !a.is_favourite) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        a.name.toLowerCase().includes(q) ||
        a.learning_area_code.toLowerCase().includes(q) ||
        a.strand_code.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Assessments</h1>
          <p className="text-gray-500 text-sm mt-1">Create, manage, and run assessments</p>
        </div>
        <Link to="/assessments/new" className="btn-primary">
          <Plus className="h-4 w-4" /> New assessment
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name, strand..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10"
          />
        </div>
        <button
          onClick={() => setFilterFav(!filterFav)}
          className={`btn ${filterFav ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'btn-secondary'}`}
        >
          <Heart className={`h-4 w-4 ${filterFav ? 'fill-amber-400' : ''}`} />
          Favourites
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-200 rounded-xl" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-gray-500">
            {search || filterFav ? 'No assessments match your filters' : 'No assessments yet'}
          </p>
          {!search && !filterFav && (
            <Link to="/assessments/new" className="btn-primary mt-4 inline-flex">
              <Plus className="h-4 w-4" /> Create assessment
            </Link>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between rounded-xl bg-white border border-gray-200 px-4 py-3 hover:border-primary-300 transition-colors"
            >
              <Link to={`/assessments/${a.id}`} className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {a.is_favourite && <Heart className="h-3.5 w-3.5 text-amber-400 fill-amber-400" />}
                  <p className="font-medium text-gray-900 truncate">{a.name}</p>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="badge-primary">{a.learning_area_code}</span>
                  {a.strand_code && <span className="badge-gray">{a.strand_code}</span>}
                  <span className={`badge ${a.source === 'ai' ? 'badge-accent' : 'badge-gray'}`}>
                    {a.source === 'ai' ? 'AI' : a.source}
                  </span>
                  <span className="text-xs text-gray-400">{a.items.length} items</span>
                </div>
              </Link>
              <button
                onClick={() => {
                  if (confirm('Delete this assessment?')) deleteMutation.mutate(a.id);
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
