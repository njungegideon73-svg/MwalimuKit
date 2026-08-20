import { apiFetch } from '@/lib/api';
import type { Learner } from '@mwalimukit/types';

export async function fetchLearnersByClass(classId: string): Promise<Learner[]> {
  return apiFetch<Learner[]>(`/learners/by-class/${classId}`);
}

export async function fetchAllLearners(): Promise<Learner[]> {
  return apiFetch<Learner[]>('/learners');
}

export interface LearnerCreate {
  full_name: string;
  admission_no?: string | null;
  gender?: string | null;
}

export async function createLearner(classId: string, payload: LearnerCreate): Promise<Learner> {
  return apiFetch<Learner>('/learners', {
    method: 'POST',
    json: { class_id: classId, ...payload },
  });
}

export async function bulkCreateLearners(classId: string, lines: string[]): Promise<Learner[]> {
  return apiFetch<Learner[]>('/learners/bulk', {
    method: 'POST',
    json: { class_id: classId, lines },
  });
}

export async function updateLearner(learnerId: string, payload: LearnerCreate): Promise<Learner> {
  return apiFetch<Learner>(`/learners/${learnerId}`, {
    method: 'PATCH',
    json: payload,
  });
}

export async function deleteLearner(learnerId: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/learners/${learnerId}`, { method: 'DELETE' });
}
