/** CBC/CBE educational levels per Kenya's 2-6-3-3-3 structure:
 *  - lower_primary: Grades 1-3 (Ages 6-8)
 *  - upper_primary: Grades 4-6 (Ages 9-11)
 *  - jss: Junior School, Grades 7-9 (Ages 12-15)
 *  - senior_school: Grades 10-12 (Ages 15-18) - STEM, Social Sciences, Arts & Sports pathways
 */
export type Level = 'lower_primary' | 'upper_primary' | 'jss' | 'senior_school';

export interface LearningArea {
  code: string;          // e.g. "LP-MATH"
  name: string;
  level: Level;
  sort_order: number;
}

export interface Strand {
  code: string;          // e.g. "LP-MATH-NUM"
  learning_area_code: string;
  name: string;
  sort_order: number;
}

export interface SubStrand {
  code: string;          // e.g. "LP-MATH-NUM-2.1"
  strand_code: string;
  name: string;
  sort_order: number;
}

export interface CurriculumCatalogue {
  learning_areas: LearningArea[];
  strands: Strand[];
  sub_strands: SubStrand[];
}
