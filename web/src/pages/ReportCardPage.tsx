import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';

interface LearnerInfo {
  id: string;
  full_name: string;
  class_name: string;
  class_id: string;
}

export function ReportCardPage() {
  const { learnerId } = useParams<{ learnerId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const runId = searchParams.get('runId');

  const { data: learner, isLoading } = useQuery<LearnerInfo>({
    queryKey: ['learner-info', learnerId],
    queryFn: () => apiFetch(`/learners/${learnerId}`),
    enabled: !!learnerId,
  });

  const API_BASE = '/api/v1';

  const pdfUrl = learnerId && runId
    ? `${API_BASE}/reports/learner/${learnerId}/report-card?runId=${runId}`
    : null;

  const csvUrl = learner?.class_id && runId
    ? `${API_BASE}/reports/class/${learner.class_id}/summary-csv?runId=${runId}`
    : null;

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6 animate-pulse">
        <div className="h-8 w-32 bg-gray-200 rounded" />
        <div className="h-48 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="btn-ghost text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Report Card</h1>
        {learner && (
          <p className="text-gray-500 mt-1">
            {learner.full_name} — {learner.class_name}
          </p>
        )}
        {!runId && (
          <p className="text-amber-600 text-sm mt-2">
            No run selected. Please select an assessment run from the class detail page.
          </p>
        )}
      </div>

      <div className="card flex flex-wrap gap-3">
        {pdfUrl ? (
          <a
            href={pdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary"
          >
            <Download className="h-4 w-4" /> Download PDF
          </a>
        ) : (
          <button disabled className="btn-primary opacity-50">
            <Download className="h-4 w-4" /> Download PDF (select a run)
          </button>
        )}

        {csvUrl ? (
          <a
            href={csvUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary"
          >
            <Download className="h-4 w-4" /> Download Class CSV
          </a>
        ) : (
          <button disabled className="btn-secondary opacity-50">
            <Download className="h-4 w-4" /> Download Class CSV
          </button>
        )}
      </div>
    </div>
  );
}
