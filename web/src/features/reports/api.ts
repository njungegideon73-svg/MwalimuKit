import { apiFetch } from '@/lib/api';
import type { AssessmentRun } from '@mwalimukit/types';

function getAuthTokens(): { access: string | null } {
  try {
    const r = localStorage.getItem('mk_auth');
    return r ? JSON.parse(r) : { access: null };
  } catch {
    return { access: null };
  }
}

export interface ExportJob {
  id: string;
  type: string;
  status: string;
  result: { filename: string; file_path: string; size_bytes: number; content_type: string } | null;
  error: string | null;
}

async function pollJob(jobId: string, onProgress?: (status: string) => void): Promise<ExportJob> {
  const { access } = getAuthTokens();
  const maxAttempts = 60;
  const intervalMs = 2000;

  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(`/api/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${access ?? ''}` },
    });
    if (!res.ok) throw new Error('Failed to poll job status');
    const job: ExportJob = await res.json();
    onProgress?.(job.status);
    if (job.status === 'completed') return job;
    if (job.status === 'failed') throw new Error(job.error || 'Export failed');
    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error('Export timed out');
}

export async function fetchLearnerReportCard(
  runId: string,
  learnerId: string,
): Promise<Blob> {
  const { access } = getAuthTokens();
  const res = await fetch(`/api/v1/jobs/reports/learner/${learnerId}/report-card?run_id=${runId}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('Failed to start report card export');
  const job: ExportJob = await res.json();
  const completed = await pollJob(job.id);
  const downloadRes = await fetch(`/api/v1/jobs/${completed.id}/download`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!downloadRes.ok) throw new Error('Failed to download report card');
  return downloadRes.blob();
}

export async function fetchClassSummaryCsv(
  classId: string,
  runId: string,
): Promise<string> {
  const { access } = getAuthTokens();
  const res = await fetch(`/api/v1/jobs/reports/class/${classId}/summary-csv?run_id=${runId}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('Failed to start CSV export');
  const job: ExportJob = await res.json();
  const completed = await pollJob(job.id);
  const downloadRes = await fetch(`/api/v1/jobs/${completed.id}/download`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!downloadRes.ok) throw new Error('Failed to download CSV');
  return downloadRes.text();
}

export async function fetchSbaReportCard(params: {
  learnerId: string;
  academicYear: string;
  schoolClosedDate?: string;
  nextTermBeginsDate?: string;
  classTeacherRemarks?: string;
  principalRemarks?: string;
}): Promise<Blob> {
  const { access } = getAuthTokens();
  const qs = new URLSearchParams({
    academic_year: params.academicYear,
    ...(params.schoolClosedDate ? { school_closed_date: params.schoolClosedDate } : {}),
    ...(params.nextTermBeginsDate ? { next_term_begins_date: params.nextTermBeginsDate } : {}),
    ...(params.classTeacherRemarks ? { class_teacher_remarks: params.classTeacherRemarks } : {}),
    ...(params.principalRemarks ? { principal_remarks: params.principalRemarks } : {}),
  }).toString();
  const res = await fetch(`/api/v1/jobs/reports/report-card/${params.learnerId}?${qs}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('Failed to start SBA report card export');
  const job: ExportJob = await res.json();
  const completed = await pollJob(job.id);
  const downloadRes = await fetch(`/api/v1/jobs/${completed.id}/download`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!downloadRes.ok) throw new Error('Failed to download SBA report card');
  return downloadRes.blob();
}

export async function fetchRuns(classId?: string): Promise<AssessmentRun[]> {
  const url = classId
    ? `/runs?class_id=${encodeURIComponent(classId)}`
    : '/runs';
  return apiFetch<AssessmentRun[]>(url);
}

export async function createContextRun(classId: string, assessmentId: string): Promise<AssessmentRun> {
  return apiFetch<AssessmentRun>('/runs', {
    method: 'POST',
    json: { class_id: classId, assessment_id: assessmentId },
  });
}

export async function closeRun(runId: string): Promise<AssessmentRun> {
  return apiFetch<AssessmentRun>(`/runs/${runId}/close`, { method: 'POST' });
}
