import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Copy, Trash2, Play, Heart } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';
import type { Assessment } from '@mwalimukit/types';

export function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    apiFetch<Assessment>(`/assessments/${id}`)
      .then(setAssessment)
      .catch(() => toast.error('Assessment not found'))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDuplicate = async () => {
    if (!id) return;
    try {
      const result = await apiFetch<{ id: string }>(`/assessments/${id}/duplicate`, {
        method: 'POST',
      });
      toast.success('Assessment duplicated');
      navigate(`/assessments/${result.id}`);
    } catch {
      toast.error('Failed to duplicate');
    }
  };

  const handleDelete = async () => {
    if (!id || !confirm('Delete this assessment?')) return;
    try {
      await apiFetch(`/assessments/${id}`, { method: 'DELETE' });
      toast.success('Deleted');
      navigate('/assessments');
    } catch {
      toast.error('Failed to delete');
    }
  };

  if (loading) {
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
          <button onClick={handleDuplicate} className="btn-secondary text-sm">
            <Copy className="h-4 w-4" /> Duplicate
          </button>
          <button onClick={handleDelete} className="btn-ghost text-sm text-red-600 hover:bg-red-50">
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Items */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Assessment items ({assessment.items.length})</h2>
        <div className="space-y-4">
          {assessment.items.map((item, idx) => (
            <div key={item.id} className="border border-gray-100 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <span className="flex-none h-6 w-6 rounded-full bg-primary-50 text-primary-700 text-xs font-medium flex items-center justify-center">
                  {idx + 1}
                </span>
                <div className="flex-1">
                  <p className="text-gray-900">{item.stem}</p>
                  {item.answer_guide && (
                    <p className="text-sm text-gray-500 mt-2">
                      <span className="font-medium">Answer:</span> {item.answer_guide}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Rubric */}
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

      {/* Run action */}
      <div className="card">
        <Link to={`/classes`} className="btn-primary w-full">
          <Play className="h-4 w-4" /> Run against a class
        </Link>
      </div>
    </div>
  );
}
