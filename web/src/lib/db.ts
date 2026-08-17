import Dexie, { type Table } from 'dexie';
import type {
  LearningArea,
  Strand,
  SubStrand,
  Assessment,
  SchoolClass,
  Learner,
  AssessmentRun,
  Score,
} from '@mwalimukit/types';

export type Syncable<T> = T & {
  _dirty: boolean;
  _synced_at: string | null;
};

class MwalimuDB extends Dexie {
  learning_areas!: Table<LearningArea, string>;
  strands!: Table<Strand, string>;
  sub_strands!: Table<SubStrand, string>;
  assessments!: Table<Syncable<Assessment>, string>;
  classes!: Table<Syncable<SchoolClass>, string>;
  learners!: Table<Syncable<Learner>, string>;
  runs!: Table<Syncable<AssessmentRun>, string>;
  scores!: Table<Syncable<Score>, string>;

  constructor() {
    super('mwalimukit');
    this.version(1).stores({
      learning_areas: 'code, level',
      strands: 'code, learning_area_code',
      sub_strands: 'code, strand_code',
      assessments: 'id, owner_id, school_id, strand_code, _dirty',
      classes: 'id, teacher_id, school_id, _dirty',
      learners: 'id, class_id, school_id, _dirty',
      runs: 'id, class_id, assessment_id, school_id, _dirty',
      scores: 'id, run_id, learner_id, [run_id+learner_id+item_id], _dirty',
    });
  }
}

export const db = new MwalimuDB();

export async function syncCurriculum(catalogue: {
  learning_areas: LearningArea[];
  strands: Strand[];
  sub_strands: SubStrand[];
}) {
  await db.transaction('rw', db.learning_areas, db.strands, db.sub_strands, async () => {
    await db.learning_areas.clear();
    await db.strands.clear();
    await db.sub_strands.clear();
    await db.learning_areas.bulkPut(catalogue.learning_areas);
    await db.strands.bulkPut(catalogue.strands);
    await db.sub_strands.bulkPut(catalogue.sub_strands);
  });
}

export async function getDirtyScores(): Promise<Syncable<Score>[]> {
  return db.scores.where('_dirty').equals(1).toArray();
}

export async function markSynced(table: Table, ids: string[]) {
  await db.transaction('rw', table, async () => {
    for (const id of ids) {
      const item = await table.get(id);
      if (item) {
        await table.update(id, { _dirty: false, _synced_at: new Date().toISOString() });
      }
    }
  });
}
