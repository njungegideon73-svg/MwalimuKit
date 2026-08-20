import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Play } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useAssessment } from '@/features/assess/hooks';
import { useUpdateRubric } from '@/features/rubrics/hooks';
import { apiFetch } from '@/lib/api';
import { AssessmentHeader, AssessmentItemList } from '@/features/assess/components/AssessmentDetailView';
import { RubricEditor } from '@/components/RubricEditor';
import toast from 'react-hot-toast';
import type { AssessmentItem } from '@mwalimukit/types';

export function AssessmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: assessment, isLoading } = useAssessment(id ?? '');
  const [localItems, setLocalItems] = useState<AssessmentItem[]>([]);
  const [rubricEditMode, setRubricEditMode] = useState(false);

  const { mutateAsync: updateRubricAsync } = useUpdateRubric();

  useEffect(() => {
    if (assessment && localItems.length === 0 && assessment.items.length > 0) {
      setLocalItems(assessment.items);
    }
  }, [assessment, localItems.length]);

  const syncLocalItems = (updated: AssessmentItem[]) => {
    setLocalItems(updated);
  };

  const handleItemsChange = (updated: AssessmentItem[]) => {
    syncLocalItems(updated);
    apiFetch(`/assessments/${id}`, { method: 'PATCH', json: { items: updated } })
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ['assessment', id] });
        toast.success('Items updated');
      })
      .catch(() => toast.error('Failed to update items'));
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

      <AssessmentHeader assessment={assessment} />

      <div className="card">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900 mb-4">Assessment items ({localItems.length})</h2>
        </div>
        <AssessmentItemList
          items={localItems}
          onItemsChange={handleItemsChange}
        />
      </div>

      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Rubric</h2>
        {rubricEditMode ? (
          <>
            <RubricEditor value={assessment.rubric} onChange={(r) => {
              updateRubricAsync({ id: assessment.id, rubric: r });
              setRubricEditMode(false);
            }} />
            <button onClick={() => setRubricEditMode(false)} className="btn-secondary text-sm mt-2">
              Cancel
            </button>
          </>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {assessment.rubric.levels.map((level) => (
                <div key={level.level} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="h-6 w-6 rounded-full bg-primary-100 text-primary-700 text-xs font-bold flex items-center justify-center">
                      {level.level}
                    </span>
                    <span className="font-medium text-sm text-gray-900">{level.label}</span>
                  </div>
                  {level.descriptor && <p className="text-sm text-gray-600">{level.descriptor}</p>}
                </div>
              ))}
            </div>
            <button onClick={() => setRubricEditMode(true)} className="btn-secondary text-sm mt-3">
              Edit rubric
            </button>
          </>
        )}
      </div>

      <div className="card">
        <Link to={`/classes`} className="btn-primary w-full">
          <Play className="h-4 w-4" /> Run against a class
        </Link>
      </div>
    </div>
  );
}
