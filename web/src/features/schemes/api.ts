import { apiFetch, API_BASE } from '@/lib/api';
import type {
  LessonContent,
  SchemeLesson,
  SchemeOfWork,
  SchemeOfWorkCreate,
  SchemeOfWorkDetail,
  SchemePreviewResponse,
} from '@mwalimukit/types';

export async function fetchSchemes(): Promise<SchemeOfWork[]> {
  return apiFetch<SchemeOfWork[]>('/schemes');
}

export async function fetchScheme(id: string): Promise<SchemeOfWorkDetail> {
  return apiFetch<SchemeOfWorkDetail>(`/schemes/${id}`);
}

export async function createScheme(payload: SchemeOfWorkCreate): Promise<SchemeOfWork> {
  return apiFetch<SchemeOfWork>('/schemes', { method: 'POST', json: payload });
}

export async function fetchSchemePreview(id: string): Promise<SchemePreviewResponse> {
  return apiFetch<SchemePreviewResponse>(`/schemes/${id}/preview`);
}

export async function updateLessonCell(
  schemeId: string,
  weekNumber: number,
  lessonNumber: number,
  patch: Partial<SchemeLesson>,
): Promise<{ updated: boolean; key: string }> {
  return apiFetch(`/schemes/${schemeId}/lessons/W${weekNumber}-L${lessonNumber}`, {
    method: 'PATCH',
    json: patch,
  });
}

export async function deleteScheme(id: string): Promise<void> {
  return apiFetch(`/schemes/${id}`, { method: 'DELETE' });
}

export async function fetchLessonContent(
  subStrandCode: string,
  termNumber?: number,
): Promise<LessonContent[]> {
  const q = termNumber ? `?term_number=${termNumber}` : '';
  return apiFetch<LessonContent[]>(`/schemes/content/${subStrandCode}${q}`);
}

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
  result: { filename: string; size_bytes: number; content_type: string } | null;
  error: string | null;
}

async function pollJob(jobId: string, onProgress?: (status: string) => void): Promise<ExportJob> {
  const { access } = getAuthTokens();
  const maxAttempts = 90;
  const intervalMs = 2000;

  for (let i = 0; i < maxAttempts; i++) {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${access ?? ''}` },
    });
    if (!res.ok) throw new Error('Failed to poll job status');
    const job: ExportJob = await res.json();
    onProgress?.(job.status);
    if (job.status === 'completed') return job;
    if (job.status === 'failed') throw new Error(job.error || 'Export failed');
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error('Export timed out');
}

export async function exportSchemePdf(
  schemeId: string,
  onProgress?: (status: string) => void,
): Promise<Blob> {
  const { access } = getAuthTokens();
  const res = await fetch(`${API_BASE}/schemes/${schemeId}/export/pdf`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('Failed to start PDF export');
  const job: ExportJob = await res.json();
  const completed = await pollJob(job.id, onProgress);
  const downloadRes = await fetch(`${API_BASE}/jobs/${completed.id}/download`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!downloadRes.ok) throw new Error('Failed to download PDF');
  return downloadRes.blob();
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function downloadSchemePdf(blob: Blob, schemeName: string) {
  const safe = schemeName.replace(/\s+/g, '-').toLowerCase();
  downloadBlob(blob, `scheme_of_work_${safe}.pdf`);
}