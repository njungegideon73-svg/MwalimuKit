import { apiFetch } from '@/lib/api';
import type { AssessmentRun } from '@mwalimukit/types';

export async function fetchLearnerReportCard(
  runId: string,
  learnerId: string,
): Promise<Blob> {
  const { access } = (() => {
    try {
      const r = localStorage.getItem('mk_auth');
      return r ? JSON.parse(r) : { access: null };
    } catch {
      return { access: null };
    }
  })();
  const res = await fetch(
    `/api/v1/reports/learner/${learnerId}/report-card?run_id=${runId}`,
    { headers: { Authorization: `Bearer ${access ?? ''}` } },
  );
  if (!res.ok) throw new Error('Report card fetch failed');
  return res.blob();
}

export async function fetchClassSummaryCsv(
  classId: string,
  runId: string,
): Promise<string> {
  const { access } = (() => {
    try {
      const r = localStorage.getItem('mk_auth');
      return r ? JSON.parse(r) : { access: null };
    } catch {
      return { access: null };
    }
  })();
  const res = await fetch(
    `/api/v1/reports/class/${classId}/summary-csv?run_id=${runId}`,
    { headers: { Authorization: `Bearer ${access ?? ''}` } },
  );
  if (!res.ok) throw new Error('CSV export failed');
  return res.text();
}

export async function fetchSbaReportCard(params: {
  learnerId: string;
  academicYear: string;
  schoolClosedDate?: string;
  nextTermBeginsDate?: string;
  classTeacherRemarks?: string;
  principalRemarks?: string;
}): Promise<Blob> {
  const { access } = (() => {
    try {
      const r = localStorage.getItem('mk_auth');
      return r ? JSON.parse(r) : { access: null };
    } catch {
      return { access: null };
    }
  })();
  const qs = new URLSearchParams({
    academic_year: params.academicYear,
    ...(params.schoolClosedDate ? { school_closed_date: params.schoolClosedDate } : {}),
    ...(params.nextTermBeginsDate ? { next_term_begins_date: params.nextTermBeginsDate } : {}),
    ...(params.classTeacherRemarks ? { class_teacher_remarks: params.classTeacherRemarks } : {}),
    ...(params.principalRemarks ? { principal_remarks: params.principalRemarks } : {}),
  }).toString();
  const res = await fetch(`/api/v1/reports/report-card/${params.learnerId}?${qs}`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('SBA report card fetch failed');
  return res.blob();
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
