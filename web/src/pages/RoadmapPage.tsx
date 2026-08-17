import { useState } from 'react';
import { ThumbsUp, Plus } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';

interface FeatureRequest {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'planned' | 'done';
  vote_count: number;
  user_has_voted: boolean;
}

const statusStyles: Record<string, string> = {
  open: 'bg-gray-100 text-gray-700',
  planned: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
};

export function RoadmapPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  const { data: features = [], isLoading } = useQuery<FeatureRequest[]>({
    queryKey: ['roadmap'],
    queryFn: () => apiFetch('/admin/roadmap'),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch('/admin/roadmap', {
        method: 'POST',
        json: { title: title.trim(), description: description.trim() },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roadmap'] });
      setTitle('');
      setDescription('');
      toast.success('Feature request submitted');
    },
    onError: () => toast.error('Failed to submit feature request'),
  });

  const voteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/admin/roadmap/${id}/vote`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roadmap'] }),
    onError: () => toast.error('Failed to vote'),
  });

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Feature Roadmap</h1>
        <p className="text-gray-500 text-sm mt-1">Suggest features and vote on what matters most</p>
      </div>

      {/* Suggest a feature form */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-3">Suggest a feature</h2>
        <div className="space-y-3">
          <div>
            <label className="label">Title</label>
            <input
              className="input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Short feature name"
            />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea
              className="input"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What should it do? Why is it useful?"
            />
          </div>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || !title.trim()}
            className="btn-primary"
          >
            <Plus className="h-4 w-4" />
            {createMutation.isPending ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>

      {/* Feature list */}
      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-xl" />
          ))}
        </div>
      ) : features.length === 0 ? (
        <div className="card text-center py-10">
          <p className="text-gray-500">No feature requests yet. Be the first to suggest one!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {features.map((f) => (
            <div key={f.id} className="card flex items-start gap-4">
              <button
                onClick={() => voteMutation.mutate(f.id)}
                disabled={voteMutation.isPending}
                className={`flex flex-col items-center gap-0.5 pt-1 transition-colors ${
                  f.user_has_voted ? 'text-primary-600' : 'text-gray-400 hover:text-primary-500'
                }`}
              >
                <ThumbsUp className={`h-5 w-5 ${f.user_has_voted ? 'fill-primary-500' : ''}`} />
                <span className="text-xs font-semibold">{f.vote_count}</span>
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-medium text-gray-900">{f.title}</h3>
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusStyles[f.status]}`}>
                    {f.status}
                  </span>
                </div>
                {f.description && (
                  <p className="text-sm text-gray-600 mt-1">{f.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
