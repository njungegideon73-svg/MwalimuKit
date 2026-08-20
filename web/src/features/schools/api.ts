import { apiFetch } from '@/lib/api';
import type { School } from '@mwalimukit/types';

export async function fetchMySchool(): Promise<School & { id: string; name: string; code: string; county: string | null; level: string | null }> {
  return apiFetch('/schools/me');
}
