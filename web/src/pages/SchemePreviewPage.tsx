import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, Loader2 } from 'lucide-react';
import { useSchemePreview, useUpdateLessonCell } from '@/features/schemes/hooks';
import { SchemePreviewTable } from '@/features/schemes/components/SchemePreviewTable';
import { exportSchemePdf, downloadSchemePdf } from '@/features/schemes/api';
import toast from 'react-hot-toast';

export function SchemePreviewPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading, isError } = useSchemePreview(id);
  const updateCell = useUpdateLessonCell(id ?? '');

  const handleCommitCell = (
    week: number,
    lesson: number,
    field: 'learning_outcomes' | 'key_inquiry_questions' | 'learning_experiences' | 'resources' | 'assessment_methods' | 'topic',
    lines: string[],
  ) => {
    updateCell.mutate({ week, lesson, patch: { [field]: lines } as never });
  };

  const handleCommitNotes = (week: number, lesson: number, note: string) => {
    updateCell.mutate({ week, lesson, patch: { notes: note } as never });
  };

  const handleExport = async () => {
    if (!id || !data) return;
    toast('Starting PDF export...');
    try {
      const blob = await exportSchemePdf(id, (status) => {
        if (status === 'completed') toast.success('PDF ready');
        if (status === 'failed') toast.error('PDF export failed');
      });
      downloadSchemePdf(blob, data.scheme.name);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Export failed');
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="h-16 bg-gray-200 rounded-xl" />
        <div className="h-96 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Scheme of work not found</p>
        <button onClick={() => navigate('/schemes')} className="btn-secondary mt-4 text-sm">
          Back to schemes
        </button>
      </div>
    );
  }

  const { scheme, lessons } = data;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/schemes')} className="btn-ghost text-sm">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <div>
            <h1 className="text-xl font-bold text-gray-900 truncate">{scheme.name}</h1>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className="badge-primary">{scheme.learning_area_code}</span>
              <span className="badge-gray">{scheme.sub_strand_code}</span>
              <span className="badge-gray">Grade {scheme.grade}</span>
              <span className="badge-gray">Term {scheme.term_number}</span>
              <span className="badge-gray">
                {scheme.lessons_per_week} lessons/wk &middot; {scheme.total_weeks} weeks
              </span>
              <span className="text-xs text-gray-400">
                {lessons.filter((l) => !l.is_break).length} lessons scheduled
              </span>
            </div>
          </div>
        </div>
        <button onClick={handleExport} className="btn-accent">
          <FileText className="h-4 w-4" /> Export PDF
        </button>
      </div>

      <div className="rounded-lg bg-primary-50 border border-primary-200 px-4 py-3 text-sm text-gray-700">
        Click any cell to edit it. Press <span className="font-medium">Enter</span> to move to the
        next cell and <span className="font-medium">Shift+Enter</span> to add a new line. Edits save
        automatically.
      </div>

      <SchemePreviewTable
        lessons={lessons}
        onCommitCell={handleCommitCell}
        onCommitNotes={handleCommitNotes}
      />

      <div className="flex items-center justify-between text-xs text-gray-400 px-1">
        <span>
          {lessons.filter((l) => !l.is_break).length} lessons &middot; lessons repeat from the
          content bank when the term has more slots than content entries
        </span>
        {updateCell.isPending && (
          <span className="inline-flex items-center gap-1">
            <Loader2 className="h-3.5 w-3.5 animate-spin" /> saving...
          </span>
        )}
      </div>
    </div>
  );
}