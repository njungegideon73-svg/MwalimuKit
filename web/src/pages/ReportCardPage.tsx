import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Download, Eye, FileText, AlertCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { fetchLearnerReportCard, fetchClassSummaryCsv } from '@/features/reports/api';
import toast from 'react-hot-toast';

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

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [csvDownloading, setCsvDownloading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const { data: learner, isLoading } = useQuery<LearnerInfo>({
    queryKey: ['learner-info', learnerId],
    queryFn: () => apiFetch(`/learners/${learnerId}`),
    enabled: !!learnerId,
  });

  const handleDownloadPdf = async () => {
    if (!learnerId || !runId) return;
    setDownloading(true);
    try {
      const blob = await fetchLearnerReportCard(runId, learnerId);
      const filename = `report_card_${learner?.full_name?.replace(/\s+/g, '_') || 'learner'}.pdf`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Report card downloaded');
    } catch (err: any) {
      toast.error(err.message || 'Failed to download report card');
    } finally {
      setDownloading(false);
    }
  };

  const handleDownloadCsv = async () => {
    if (!learner?.class_id || !runId) return;
    setCsvDownloading(true);
    try {
      const text = await fetchClassSummaryCsv(learner.class_id, runId);
      const blob = new Blob([text], { type: 'text/csv' });
      const filename = `class_summary_${learner.class_name.replace(/\s+/g, '_') || 'class'}.csv`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Class summary downloaded');
    } catch (err: any) {
      toast.error(err.message || 'Failed to download class summary');
    } finally {
      setCsvDownloading(false);
    }
  };

  const handlePreview = async () => {
    if (!learnerId || !runId) return;
    setFetchError(null);
    try {
      const blob = await fetchLearnerReportCard(runId, learnerId);
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch (err: any) {
      setFetchError(err.message || 'Failed to load report card');
      setPreviewUrl(null);
    }
  };

  // Auto-preview when learner and run are available
  useEffect(() => {
    if (learnerId && runId && !fetchError) {
      handlePreview();
    }
  }, [learnerId, runId]);

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6 animate-pulse">
        <div className="h-8 w-32 bg-gray-200 rounded" />
        <div className="h-48 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
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

      {/* Action buttons */}
      <div className="card flex flex-wrap gap-3">
        {learnerId && runId ? (
          <button onClick={handleDownloadPdf} disabled={downloading} className="btn-primary">
            <Download className="h-4 w-4" /> {downloading ? 'Downloading...' : 'Download PDF'}
          </button>
        ) : (
          <button disabled className="btn-primary opacity-50">
            <Download className="h-4 w-4" /> Download PDF (select a run)
          </button>
        )}

        {learner?.class_id && runId ? (
          <button onClick={handleDownloadCsv} disabled={csvDownloading} className="btn-secondary">
            <Download className="h-4 w-4" /> {csvDownloading ? 'Downloading...' : 'Download Class CSV'}
          </button>
        ) : (
          <button disabled className="btn-secondary opacity-50">
            <Download className="h-4 w-4" /> Download Class CSV
          </button>
        )}
      </div>

      {/* Error state */}
      {fetchError && (
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-800">Unable to load report card</p>
              <p className="text-sm text-red-600 mt-1">{fetchError}</p>
              <p className="text-sm text-red-600 mt-1">
                Make sure scores have been entered for this learner in the selected assessment run.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* PDF Preview */}
      {previewUrl && !fetchError && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Eye className="h-4 w-4 text-gray-500" />
            <h2 className="font-semibold text-gray-900">Preview</h2>
          </div>
          <div className="border border-gray-200 rounded-lg overflow-hidden bg-gray-100">
            <iframe
              src={previewUrl}
              title="Report Card Preview"
              className="w-full h-[600px]"
            />
          </div>
        </div>
      )}

      {/* Loading preview */}
      {learnerId && runId && !previewUrl && !fetchError && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-4 w-4 text-gray-400 animate-pulse" />
            <h2 className="font-semibold text-gray-500">Loading preview...</h2>
          </div>
          <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" />
          </div>
        </div>
      )}
    </div>
  );
}
