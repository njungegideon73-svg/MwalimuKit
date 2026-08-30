import { useState } from 'react';
import { ThumbsUp, Plus, Newspaper, Lightbulb, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import toast from 'react-hot-toast';

interface NewsItem {
  id: string;
  title: string;
  content: string;
  category: string;
  is_active: boolean;
  school_id?: string | null;
  created_by: string;
  created_at: string;
}

interface FeatureRequest {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'planned' | 'done';
  vote_count: number;
  created_by?: string | null;
  user_has_voted: boolean;
}

interface School {
  id: string;
  name: string;
  code: string;
}

const statusStyles: Record<string, string> = {
  open: 'bg-gray-100 text-gray-700',
  planned: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
};

const categoryStyles: Record<string, string> = {
  news: 'bg-blue-100 text-blue-700',
  update: 'bg-green-100 text-green-700',
  suggestion: 'bg-amber-100 text-amber-700',
  announcement: 'bg-purple-100 text-purple-700',
};

function NewsCard({ item, onDelete }: { item: NewsItem; onDelete?: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = item.content.length > 200;

  return (
    <div className="card">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <Newspaper className="h-4 w-4 text-blue-500 flex-shrink-0" />
            <h3 className="font-semibold text-gray-900">{item.title}</h3>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${categoryStyles[item.category] || categoryStyles.news}`}>
              {item.category}
            </span>
          </div>
          <div className="text-sm text-gray-600 whitespace-pre-wrap">
            {isLong && !expanded ? `${item.content.slice(0, 200)}...` : item.content}
          </div>
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-primary-600 hover:text-primary-700 mt-1 flex items-center gap-1"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? 'Show less' : 'Read more'}
            </button>
          )}
          <p className="text-xs text-gray-400 mt-2">
            {new Date(item.created_at).toLocaleDateString('en-KE', {
              year: 'numeric', month: 'long', day: 'numeric',
            })}
          </p>
        </div>
        {onDelete && (
          <button
            onClick={() => onDelete(item.id)}
            className="p-1.5 text-gray-400 hover:text-red-600 transition-colors flex-shrink-0"
            aria-label="Delete news item"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

export function RoadmapPage() {
  const queryClient = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const isSuperAdmin = user?.role === 'super_admin';

  // News state
  const [newsTitle, setNewsTitle] = useState('');
  const [newsContent, setNewsContent] = useState('');
  const [newsCategory, setNewsCategory] = useState('news');
  const [newsSchoolId, setNewsSchoolId] = useState('');
  const [showNewsForm, setShowNewsForm] = useState(false);

  // Suggestion state
  const [suggestionTitle, setSuggestionTitle] = useState('');
  const [suggestionDescription, setSuggestionDescription] = useState('');
  const [showSuggestionForm, setShowSuggestionForm] = useState(false);

  // Fetch schools for super admin
  const { data: schools = [] } = useQuery<School[]>({
    queryKey: ['super-admin-schools-list'],
    queryFn: () => apiFetch('/super-admin/schools?limit=200'),
    enabled: isSuperAdmin,
  });

  // Fetch news
  const { data: newsItems = [], isLoading: loadingNews } = useQuery<NewsItem[]>({
    queryKey: ['news'],
    queryFn: () => apiFetch('/news'),
  });

  // Fetch suggestions (feature requests)
  const { data: suggestions = [], isLoading: loadingSuggestions } = useQuery<FeatureRequest[]>({
    queryKey: ['roadmap'],
    queryFn: () => apiFetch('/admin/roadmap'),
  });

  // Filter suggestions based on role
  const visibleSuggestions = isSuperAdmin
    ? suggestions
    : suggestions.filter(s => !s.created_by || s.created_by === user?.id);

  // News mutations (super admin only)
  const createNewsMutation = useMutation({
    mutationFn: () =>
      apiFetch('/news', {
        method: 'POST',
        json: {
          title: newsTitle.trim(),
          content: newsContent.trim(),
          category: newsCategory,
          is_active: true,
          school_id: newsSchoolId || undefined,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['news'] });
      setNewsTitle('');
      setNewsContent('');
      setNewsCategory('news');
      setNewsSchoolId('');
      setShowNewsForm(false);
      toast.success('News item posted');
    },
    onError: () => toast.error('Failed to post news item'),
  });

  const deleteNewsMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/news/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['news'] });
      toast.success('News item removed');
    },
    onError: () => toast.error('Failed to remove news item'),
  });

  // Suggestion mutations
  const createSuggestionMutation = useMutation({
    mutationFn: () =>
      apiFetch('/admin/roadmap', {
        method: 'POST',
        json: { title: suggestionTitle.trim(), description: suggestionDescription.trim() },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roadmap'] });
      setSuggestionTitle('');
      setSuggestionDescription('');
      setShowSuggestionForm(false);
      toast.success('Suggestion submitted');
    },
    onError: () => toast.error('Failed to submit suggestion'),
  });

  const voteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/admin/roadmap/${id}/vote`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roadmap'] }),
    onError: () => toast.error('Failed to vote'),
  });

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">News & Suggestions</h1>
        <p className="text-gray-500 text-sm mt-1">
          {isSuperAdmin
            ? 'Post news and manage feature suggestions from the community'
            : 'Stay updated with the latest news and suggest new features'}
        </p>
      </div>

      {/* News Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-blue-500" />
            News & Announcements
          </h2>
          {isSuperAdmin && (
            <button
              onClick={() => setShowNewsForm(!showNewsForm)}
              className="btn-secondary text-sm"
            >
              <Plus className="h-4 w-4" />
              {showNewsForm ? 'Cancel' : 'Post News'}
            </button>
          )}
        </div>

        {/* News form (super admin only) */}
        {isSuperAdmin && showNewsForm && (
          <div className="card mb-4 border-primary-200 bg-primary-50/30">
            <h3 className="font-medium text-gray-900 mb-3">New Announcement</h3>
            <div className="space-y-3">
              <div>
                <label className="label">Title</label>
                <input
                  className="input"
                  value={newsTitle}
                  onChange={(e) => setNewsTitle(e.target.value)}
                  placeholder="Announcement title"
                />
              </div>
              <div>
                <label className="label">Category</label>
                <select
                  className="input"
                  value={newsCategory}
                  onChange={(e) => setNewsCategory(e.target.value)}
                >
                  <option value="news">News</option>
                  <option value="update">Platform Update</option>
                  <option value="announcement">Announcement</option>
                  <option value="suggestion">Suggestion</option>
                </select>
              </div>
              <div>
                <label className="label">Target School</label>
                <select
                  className="input"
                  value={newsSchoolId}
                  onChange={(e) => setNewsSchoolId(e.target.value)}
                >
                  <option value="">All Schools (Global)</option>
                  {schools.map((s: any) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Content</label>
                <textarea
                  className="input"
                  rows={4}
                  value={newsContent}
                  onChange={(e) => setNewsContent(e.target.value)}
                  placeholder="Write your announcement..."
                />
              </div>
              <button
                onClick={() => createNewsMutation.mutate()}
                disabled={createNewsMutation.isPending || !newsTitle.trim() || !newsContent.trim()}
                className="btn-primary"
              >
                {createNewsMutation.isPending ? 'Posting...' : 'Post Announcement'}
              </button>
            </div>
          </div>
        )}

        {/* News list */}
        {loadingNews ? (
          <div className="space-y-3 animate-pulse">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-28 bg-gray-200 rounded-xl" />
            ))}
          </div>
        ) : newsItems.length === 0 ? (
          <div className="card text-center py-8">
            <Newspaper className="h-10 w-10 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500 text-sm">No news items yet{isSuperAdmin ? '. Post the first one!' : ''}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {newsItems.map((item) => (
              <NewsCard
                key={item.id}
                item={item}
                onDelete={isSuperAdmin ? (id) => deleteNewsMutation.mutate(id) : undefined}
              />
            ))}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-gray-200" />

      {/* Suggestions Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-amber-500" />
            Feature Suggestions
          </h2>
          {!isSuperAdmin && (
            <button
              onClick={() => setShowSuggestionForm(!showSuggestionForm)}
              className="btn-secondary text-sm"
            >
              <Plus className="h-4 w-4" />
              {showSuggestionForm ? 'Cancel' : 'Suggest Feature'}
            </button>
          )}
        </div>

        {/* Suggestion form */}
        {!isSuperAdmin && showSuggestionForm && (
          <div className="card mb-4 border-amber-200 bg-amber-50/30">
            <h3 className="font-medium text-gray-900 mb-3">Suggest a Feature</h3>
            <div className="space-y-3">
              <div>
                <label className="label">Title</label>
                <input
                  className="input"
                  value={suggestionTitle}
                  onChange={(e) => setSuggestionTitle(e.target.value)}
                  placeholder="Short feature name"
                />
              </div>
              <div>
                <label className="label">Description</label>
                <textarea
                  className="input"
                  rows={3}
                  value={suggestionDescription}
                  onChange={(e) => setSuggestionDescription(e.target.value)}
                  placeholder="What should it do? Why is it useful?"
                />
              </div>
              <button
                onClick={() => createSuggestionMutation.mutate()}
                disabled={createSuggestionMutation.isPending || !suggestionTitle.trim()}
                className="btn-primary"
              >
                <Plus className="h-4 w-4" />
                {createSuggestionMutation.isPending ? 'Submitting...' : 'Submit Suggestion'}
              </button>
            </div>
          </div>
        )}

        {/* Suggestions list */}
        {loadingSuggestions ? (
          <div className="space-y-3 animate-pulse">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-xl" />
            ))}
          </div>
        ) : visibleSuggestions.length === 0 ? (
          <div className="card text-center py-8">
            <Lightbulb className="h-10 w-10 text-gray-300 mx-auto mb-2" />
            <p className="text-gray-500 text-sm">
              {isSuperAdmin ? 'No suggestions yet.' : 'No suggestions yet. Be the first to suggest one!'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {visibleSuggestions.map((f) => (
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
    </div>
  );
}
