import { apiFetch } from '@/lib/api';
import { db, syncCurriculum } from '@/lib/db';
import type { LearningArea, Strand, SubStrand } from '@mwalimukit/types';

let cached: {
  learning_areas: LearningArea[];
  strands: Strand[];
  sub_strands: SubStrand[];
} | null = null;

export async function getCurriculum() {
  if (cached) return cached;

  try {
    const data = await apiFetch<{
      learning_areas: LearningArea[];
      strands: Strand[];
      sub_strands: SubStrand[];
    }>('/curriculum/catalogue');

    cached = data;
    await syncCurriculum(data);
    return data;
  } catch {
    // Offline: read from IndexedDB
    const learning_areas = await db.learning_areas.toArray();
    const strands = await db.strands.toArray();
    const sub_strands = await db.sub_strands.toArray();
    cached = { learning_areas, strands, sub_strands };
    return cached;
  }
}

export function getCachedCurriculum() {
  return cached;
}

export function invalidateCurriculumCache() {
  cached = null;
}
