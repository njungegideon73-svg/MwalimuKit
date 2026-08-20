import { apiFetch } from '@/lib/api';
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

export async function exportAssessmentPdf(id: string, mode: 'questions' | 'answer-key' = 'questions'): Promise<Blob> {
  const { access } = getAuthTokens();
  const res = await fetch(`/api/v1/assessments/${id}/export/pdf?mode=${mode}`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) throw new Error('PDF export failed');
  return res.blob();
}

export async function exportAssessmentDocx(id: string, mode: 'questions' | 'answer-key' = 'questions'): Promise<Blob> {
  const { access } = getAuthTokens();
  const res = await fetch(`/api/v1/assessments/${id}/export/docx?mode=${mode}`, {
    headers: { Authorization: `Bearer ${access ?? ''}` },
  });
  if (!res.ok) {
    if (res.status === 501) throw new Error('DOCX export not available on this server');
    throw new Error('DOCX export failed');
  }
  return res.blob();
}

export async function exportAnswerKeyPdf(id: string): Promise<Blob> {
  return exportAssessmentPdf(id, 'answer-key');
}
