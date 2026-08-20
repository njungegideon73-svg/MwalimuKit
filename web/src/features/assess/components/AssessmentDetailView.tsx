import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  duplicateAssessment,
  deleteAssessment,
  exportAssessmentPdf,
  exportAssessmentDocx,
  exportAnswerKeyPdf,
} from '@/features/assess/api';
import {
  Heart,
  Copy,
  Download,
  FileText,
  Trash2,
  Pencil,
} from 'lucide-react';
import type { Assessment, AssessmentItem } from '@mwalimukit/types';
import { MermaidChart } from '@/components/MermaidChart';
import { SimpleChart } from '@/components/SimpleChart';
import toast from 'react-hot-toast';

export function AssessmentHeader({ assessment }: { assessment: Assessment }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const duplicateMutation = useMutation({
    mutationFn: () => duplicateAssessment(assessment.id),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Assessment duplicated');
      navigate(`/assessments/${result.id}`);
    },
    onError: () => toast.error('Failed to duplicate'),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteAssessment(assessment.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Deleted');
      navigate('/assessments');
    },
    onError: () => toast.error('Failed to delete'),
  });

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExportPdf = async () => {
    try {
      const blob = await exportAssessmentPdf(assessment.id);
      downloadBlob(blob, `assessment-${assessment.name.replace(/\s+/g, '-').toLowerCase()}.pdf`);
      toast.success('PDF downloaded');
    } catch {
      toast.error('Failed to export PDF');
    }
  };

  const handleExportDocx = async () => {
    try {
      const blob = await exportAssessmentDocx(assessment.id);
      downloadBlob(blob, `assessment-${assessment.name.replace(/\s+/g, '-').toLowerCase()}.docx`);
      toast.success('Word document downloaded');
    } catch (e: any) {
      toast.error(e.message || 'Failed to export Word document');
    }
  };

  const handleExportAnswerKey = async () => {
    try {
      const blob = await exportAnswerKeyPdf(assessment.id);
      downloadBlob(blob, `answer-key-${assessment.name.replace(/\s+/g, '-').toLowerCase()}.pdf`);
      toast.success('Answer key downloaded');
    } catch {
      toast.error('Failed to export answer key');
    }
  };

  return (
    <div className="flex items-start justify-between">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">{assessment.name}</h1>
          {assessment.is_favourite && <Heart className="h-5 w-5 text-amber-400 fill-amber-400" />}
        </div>
        {assessment.description && <p className="text-gray-500 mt-1">{assessment.description}</p>}
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
        <button type="button" onClick={handleExportPdf} className="btn-secondary text-sm">
          <Download className="h-4 w-4" /> PDF
        </button>
        <button type="button" onClick={handleExportAnswerKey} className="btn-secondary text-sm">
          <Download className="h-4 w-4" /> Answer Key
        </button>
        <button type="button" onClick={handleExportDocx} className="btn-secondary text-sm">
          <FileText className="h-4 w-4" /> Word
        </button>
        <button type="button" onClick={() => { if (confirm('Delete this assessment?')) deleteMutation.mutate(); }}
          disabled={deleteMutation.isPending}
          className="btn-ghost text-sm text-red-600 hover:bg-red-50">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export function AssessmentItemList({
  items,
  onItemsChange,
}: {
  items: AssessmentItem[];
  onItemsChange: (items: AssessmentItem[]) => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<AssessmentItem | null>(null);

  const removeItem = (itemId: string) => {
    onItemsChange(items.filter((it) => it.id !== itemId));
  };

  const startEdit = (item: AssessmentItem) => {
    setEditingId(item.id);
    setEditDraft({ ...item });
  };

  const saveEdit = () => {
    if (!editDraft) return;
    const updated = items.map((it) => (it.id === editDraft.id ? editDraft : it));
    onItemsChange(updated);
    setEditingId(null);
    setEditDraft(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditDraft(null);
  };

  return (
    <div className="space-y-4">
      {items.map((item, idx) => (
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
  );
}
