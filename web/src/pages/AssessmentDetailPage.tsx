import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Copy, Trash2, Play, Heart, Download, FileText, Pencil } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { useState } from 'react';
import toast from 'react-hot-toast';
import type { Assessment, AssessmentItem } from '@mwalimukit/types';
import { MermaidChart } from '@/components/MermaidChart';
import { SimpleChart } from '@/components/SimpleChart';

export function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: assessment, isLoading } = useQuery<Assessment>({
    queryKey: ['assessment', id],
    queryFn: () => apiFetch(`/assessments/${id}`),
    enabled: !!id,
  });

  const [localItems, setLocalItems] = useState<AssessmentItem[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<AssessmentItem | null>(null);

  const duplicateMutation = useMutation({
    mutationFn: () => apiFetch<{ id: string }>(`/assessments/${id}/duplicate`, { method: 'POST' }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Assessment duplicated');
      navigate(`/assessments/${result.id}`);
    },
    onError: () => toast.error('Failed to duplicate'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiFetch(`/assessments/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Deleted');
      navigate('/assessments');
    },
    onError: () => toast.error('Failed to delete'),
  });

  const updateItemsMutation = useMutation({
    mutationFn: (items: AssessmentItem[]) =>
      apiFetch(`/assessments/${id}`, {
        method: 'PATCH',
        json: { items },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessment', id] });
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Items updated');
    },
    onError: () => toast.error('Failed to update items'),
  });

  const removeItem = (itemId: string) => {
    const updated = localItems.filter((it) => it.id !== itemId);
    setLocalItems(updated);
    updateItemsMutation.mutate(updated);
  };

  const startEdit = (item: AssessmentItem) => {
    setEditingId(item.id);
    setEditDraft({ ...item });
  };

  const saveEdit = () => {
    if (!editDraft) return;
    const updated = localItems.map((it) => (it.id === editDraft.id ? editDraft : it));
    setLocalItems(updated);
    setEditingId(null);
    setEditDraft(null);
    updateItemsMutation.mutate(updated);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft(null);
  };

  // Sync local items when assessment loads
  if (assessment && localItems.length === 0 && assessment.items.length > 0) {
    setLocalItems(assessment.items);
  }

  const exportPdf = async () => {
    if (!id) return;
    try {
      const token = (() => { try { const r = localStorage.getItem('mk_auth'); return r ? JSON.parse(r).access_token : ''; } catch { return ''; } })();
      const res = await fetch(`/api/v1/assessments/${id}/export/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('PDF export failed');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `assessment-${assessment?.name?.replace(/\s+/g, '-').toLowerCase() || id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('PDF downloaded');
    } catch {
      toast.error('Failed to export PDF');
    }
  };

  const exportDocx = async () => {
    if (!id) return;
    try {
      const token = (() => { try { const r = localStorage.getItem('mk_auth'); return r ? JSON.parse(r).access_token : ''; } catch { return ''; } })();
      const res = await fetch(`/api/v1/assessments/${id}/export/docx`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        if (res.status === 501) throw new Error('DOCX export not available on this server');
        throw new Error('DOCX export failed');
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `assessment-${assessment?.name?.replace(/\s+/g, '-').toLowerCase() || id}.docx`;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success('Word document downloaded');
    } catch (e: any) {
      toast.error(e.message || 'Failed to export Word document');
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse max-w-3xl mx-auto">
        <div className="h-8 w-32 bg-gray-200 rounded" />
        <div className="h-48 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  if (!assessment) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Assessment not found</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="btn-ghost text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">{assessment.name}</h1>
            {assessment.is_favourite && <Heart className="h-5 w-5 text-amber-400 fill-amber-400" />}
          </div>
          {assessment.description && (
            <p className="text-gray-500 mt-1">{assessment.description}</p>
          )}
          <div className="flex items-center gap-2 mt-2">
            <span className="badge-primary">{assessment.learning_area_code}</span>
            {assessment.strand_code && <span className="badge-gray">{assessment.strand_code}</span>}
            <span className={`badge ${assessment.source === 'ai' ? 'badge-accent' : 'badge-gray'}`}>
              {assessment.source === 'ai' ? 'AI draft' : assessment.source}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => duplicateMutation.mutate()} disabled={duplicateMutation.isPending}
            className="btn-secondary text-sm">
            <Copy className="h-4 w-4" /> {duplicateMutation.isPending ? 'Copying...' : 'Duplicate'}
          </button>
          <button type="button" onClick={exportPdf} className="btn-secondary text-sm">
            <Download className="h-4 w-4" /> PDF
          </button>
          <button type="button" onClick={exportDocx} className="btn-secondary text-sm">
            <FileText className="h-4 w-4" /> Word
          </button>
          <button type="button" onClick={() => { if (confirm('Delete this assessment?')) deleteMutation.mutate(); }}
            disabled={deleteMutation.isPending}
            className="btn-ghost text-sm text-red-600 hover:bg-red-50">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Assessment items ({localItems.length})</h2>
        <div className="space-y-4">
          {localItems.map((item, idx) => (
            <div key={item.id} className="border border-gray-100 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="flex-none h-6 w-6 rounded-full bg-primary-50 text-primary-700 text-xs font-medium flex items-center justify-center">
                  {idx + 1}
                </span>
                <div className="flex-1">
                  {editingId === item.id && editDraft ? (
                    <div className="space-y-2">
                      <textarea
                        value={editDraft.stem}
                        onChange={(e) => setEditDraft({ ...editDraft, stem: e.target.value })}
                        className="input"
                        rows={2}
                      />
                      <input
                        value={editDraft.answer_guide ?? ''}
                        onChange={(e) => setEditDraft({ ...editDraft, answer_guide: e.target.value })}
                        className="input"
                        placeholder="Answer guide"
                      />
                      {editDraft.diagram_type && editDraft.diagram_type !== 'none' && editDraft.diagram_data && (
                        <div className="border border-blue-100 rounded-lg p-2 bg-blue-50/30">
                          <p className="text-xs font-medium text-blue-700 mb-1">Diagram ({editDraft.diagram_type})</p>
                          {editDraft.diagram_type === 'flowchart' && (
                            <MermaidChart code={editDraft.diagram_data} />
                          )}
                          {editDraft.diagram_type === 'chart' && (
                            <SimpleChart data={editDraft.diagram_data} />
                          )}
                          {editDraft.diagram_type === 'diagram' && (
                            <p className="text-sm text-gray-600 italic">{editDraft.diagram_data}</p>
                          )}
                        </div>
                      )}
                      <textarea
                        value={editDraft.diagram_description ?? ''}
                        onChange={(e) => setEditDraft({ ...editDraft, diagram_description: e.target.value })}
                        className="input"
                        rows={1}
                        placeholder="Diagram description"
                      />
                      <div className="flex gap-2">
                        <button type="button" onClick={saveEdit} className="btn-primary text-sm">Save</button>
                        <button type="button" onClick={cancelEdit} className="btn-secondary text-sm">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p className="text-gray-900">{item.stem}</p>
                      {item.answer_guide && (
                        <p className="text-sm text-gray-500 mt-2">
                          <span className="font-medium">Answer:</span> {item.answer_guide}
                        </p>
                      )}
                      {item.diagram_type && item.diagram_type !== 'none' && item.diagram_data && (
                        <div className="mt-3 border border-blue-100 rounded-lg p-3 bg-blue-50/30">
                          <p className="text-xs font-medium text-blue-700 mb-2">Diagram ({item.diagram_type})</p>
                          {item.diagram_type === 'flowchart' && (
                            <MermaidChart code={item.diagram_data} />
                          )}
                          {item.diagram_type === 'chart' && (
                            <SimpleChart data={item.diagram_data} />
                          )}
                          {item.diagram_type === 'diagram' && (
                            <p className="text-sm text-gray-600 italic">{item.diagram_data}</p>
                          )}
                        </div>
                      )}
                      {item.diagram_description && !item.diagram_data && (
                        <p className="text-sm text-blue-600 mt-2">
                          <span className="font-medium">Diagram / Visual:</span> {item.diagram_description}
                        </p>
                      )}
                    </>
                  )}
                </div>
                <div className="flex gap-1">
                  {editingId !== item.id && (
                    <button type="button" onClick={() => startEdit(item)} className="text-gray-400 hover:text-primary-600">
                      <Pencil className="h-4 w-4" />
                    </button>
                  )}
                  <button type="button" onClick={() => removeItem(item.id)} className="text-gray-400 hover:text-red-600">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Rubric</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {assessment.rubric.levels.map((level) => (
            <div key={level.level} className="border border-gray-100 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="h-6 w-6 rounded-full bg-primary-100 text-primary-700 text-xs font-bold flex items-center justify-center">
                  {level.level}
                </span>
                <span className="font-medium text-sm text-gray-900">{level.label}</span>
              </div>
              {level.descriptor && (
                <p className="text-sm text-gray-600 ml-8">{level.descriptor}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <Link to={`/classes`} className="btn-primary w-full">
          <Play className="h-4 w-4" /> Run against a class
        </Link>
      </div>
    </div>
  );
}
