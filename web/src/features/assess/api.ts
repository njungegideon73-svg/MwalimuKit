import { apiFetch, API_BASE } from '@/lib/api';
import type { Assessment } from '@mwalimukit/types';

export async function fetchAssessment(id: string): Promise<Assessment> {
  return apiFetch<Assessment>(`/assessments/${id}`);
}

export async function fetchAssessments(): Promise<Assessment[]> {
  return apiFetch<Assessment[]>('/assessments');
}

export async function createAssessment(payload: Partial<Assessment>): Promise<{ id: string }> {
  return apiFetch<{ id: string }>('/assessments', {
    method: 'POST',
    json: payload,
  });
}

export async function updateAssessment(id: string, patch: Record<string, unknown>): Promise<Assessment> {
  return apiFetch<Assessment>(`/assessments/${id}`, {
    method: 'PATCH',
    json: patch,
  });
}

export async function duplicateAssessment(id: string): Promise<{ id: string }> {
  return apiFetch<{ id: string }>(`/assessments/${id}/duplicate`, { method: 'POST' });
}

export async function deleteAssessment(id: string): Promise<{ deleted: boolean }> {
  return apiFetch<{ deleted: boolean }>(`/assessments/${id}`, { method: 'DELETE' });
}

export interface GeneratePayload {
  learning_area_code: string;
  strand_code: string;
  sub_strand_codes: string[];
  grade_level: string;
  teacher_prompt?: string;
  item_count?: number;
  include_diagrams?: boolean;
}

export interface GenerateResult {
  rubric: { levels: Array<{ level: number; label: string; descriptor: string }>; criteria: Array<{ id: string; label: string }> };
  items: Array<Record<string, unknown>>;
  provider: string;
  model: string;
}

export async function generateAssessment(payload: GeneratePayload): Promise<GenerateResult> {
  return apiFetch<GenerateResult>('/assessments/generate', {
    method: 'POST',
    json: payload,
  });
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
  result: { filename: string; file_path: string; size_bytes: number; content_type: string } | null;
  error: string | null;
}

async function pollJob(jobId: string, onProgress?: (status: string) => void): Promise<ExportJob> {
  const { access } = getAuthTokens();
  const maxAttempts = 60;
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
    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error('Export timed out');
}

export async function exportAssessmentPdf(id: string, mode: 'questions' | 'answer-key' = 'questions'): Promise<Blob> {
  const { access } = getAuthTokens();
  const res = await fetch(`${API_BASE}/jobs/assessments/${id}/export/pdf?mode=${mode}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('Failed to start PDF export');
  const job: ExportJob = await res.json();
  const completed = await pollJob(job.id);
  const downloadRes = await fetch(`${API_BASE}/jobs/${completed.id}/download`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!downloadRes.ok) throw new Error('Failed to download PDF');
  return downloadRes.blob();
}

export async function exportAssessmentDocx(id: string, mode: 'questions' | 'answer-key' = 'questions'): Promise<Blob> {
  const { access } = getAuthTokens();
  const res = await fetch(`${API_BASE}/jobs/assessments/${id}/export/docx?mode=${mode}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('Failed to start DOCX export');
  const job: ExportJob = await res.json();
  const completed = await pollJob(job.id);
  const downloadRes = await fetch(`${API_BASE}/jobs/${completed.id}/download`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!downloadRes.ok) throw new Error('Failed to download DOCX');
  return downloadRes.blob();
}

export async function exportAnswerKeyPdf(id: string): Promise<Blob> {
  return exportAssessmentPdf(id, 'answer-key');
}
