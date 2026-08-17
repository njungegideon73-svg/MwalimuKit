import { useState } from 'react';
import { Clock, MessageSquare, ChevronDown, ChevronUp, Send } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';
import type { PromptHistoryEntry } from '@mwalimukit/types';

interface PromptHistoryPanelProps {
  onUsePrompt?: (entry: PromptHistoryEntry) => void;
}

export function PromptHistoryPanel({ onUsePrompt }: PromptHistoryPanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const queryClient = useQueryClient();

  const { data: history = [] } = useQuery<PromptHistoryEntry[]>({
    queryKey: ['history'],
    queryFn: () => apiFetch('/history'),
    staleTime: 60_000,
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ id, feedback }: { id: string; feedback: string }) =>
      apiFetch(`/history/${id}/feedback`, { method: 'POST', json: { feedback } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['history'] });
      toast.success('Feedback saved');
      setFeedbackText('');
      setExpanded(null);
    },
    onError: () => toast.error('Failed to save feedback'),
  });

  if (history.length === 0) {
    return null;
  }

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2">
        <Clock className="h-4 w-4 text-gray-500" />
        <h3 className="font-semibold text-gray-900 text-sm">Recent generations</h3>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {history.map((entry) => (
          <div key={entry.id} className="rounded-lg border border-gray-100 p-3 text-sm">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800 truncate">
                  {entry.learning_area_code} — {entry.strand_code}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {entry.grade_level} · {entry.provider} · {entry.item_count} items
                </p>
                {entry.teacher_prompt && (
                  <p className="text-xs text-gray-600 mt-1 italic truncate">
                    &ldquo;{entry.teacher_prompt}&rdquo;
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1 ml-2 shrink-0">
                {onUsePrompt && (
                  <button
                    type="button"
                    onClick={() => onUsePrompt(entry)}
                    className="text-xs text-emerald-600 hover:text-emerald-800 px-2 py-1"
                  >
                    Reuse
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setExpanded(expanded === entry.id ? null : entry.id)}
                  className="p-1 text-gray-400 hover:text-gray-600"
                >
                  {expanded === entry.id ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                </button>
              </div>
            </div>

            {expanded === entry.id && (
              <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                {entry.feedback && (
                  <div className="bg-blue-50 rounded p-2 text-xs text-blue-800">
                    <MessageSquare className="h-3 w-3 inline mr-1" />
                    {entry.feedback}
                  </div>
                )}
                <div className="flex gap-2">
                  <input
                    type="text"
                    className="flex-1 text-xs border rounded px-2 py-1"
                    placeholder="Add feedback to improve next time..."
                    value={expanded === entry.id ? feedbackText : ''}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && feedbackText.trim()) {
                        feedbackMutation.mutate({ id: entry.id, feedback: feedbackText.trim() });
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      if (feedbackText.trim()) {
                        feedbackMutation.mutate({ id: entry.id, feedback: feedbackText.trim() });
                      }
                    }}
                    disabled={!feedbackText.trim() || feedbackMutation.isPending}
                    className="p-1 text-emerald-600 hover:text-emerald-800 disabled:opacity-50"
                  >
                    <Send className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
