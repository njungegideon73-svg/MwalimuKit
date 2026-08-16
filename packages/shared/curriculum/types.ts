export type Level = 'lower_primary' | 'upper_primary' | 'jss';

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
