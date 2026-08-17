// Shared API / domain types. These mirror the FastAPI Pydantic schemas
// in api/app/schemas/ and the Dexie tables in web/src/lib/db.ts.
// Keep them in sync manually for v0.1; v0.2 will generate from the
// OpenAPI schema.

export type ID = string;

export type Level = 'lower_primary' | 'upper_primary' | 'jss';

export type UserRole = 'teacher' | 'school_admin' | 'super_admin';

export type AssessmentSource = 'ai' | 'manual' | 'template';

// ---------- Curriculum ----------

export interface LearningArea {
  code: string;
  name: string;
  level: Level;
  sort_order: number;
}

export interface Strand {
  code: string;
  learning_area_code: string;
  name: string;
  sort_order: number;
}

export interface SubStrand {
  code: string;
  strand_code: string;
  name: string;
  sort_order: number;
}

// ---------- School & user ----------

export interface School {
  id: ID;
  name: string;
  code: string;
  county: string | null;
  level: string | null;
  settings: Record<string, unknown>;
}

export interface User {
  id: ID;
  school_id: ID;
  email: string;
  full_name: string;
  role: UserRole;
}

// ---------- Rubric & item ----------

export interface RubricLevel {
  level: 1 | 2 | 3 | 4;
  label: string;
  descriptor: string;
}

export interface RubricCriterion {
  id: string;
  label: string;
}

export interface Rubric {
  levels: RubricLevel[];
  criteria: RubricCriterion[];
}

export interface AssessmentItem {
  id: string;
  criterion: string;
  stem: string;
  answer_guide?: string | null;
  max_level: 1 | 2 | 3 | 4;
}

// ---------- Assessment template ----------

export interface Assessment {
  id: ID;
  owner_id: ID;
  school_id: ID;
  name: string;
  description: string | null;
  learning_area_code: string;
  strand_code: string;
  sub_strand_codes: string[];
  source: AssessmentSource;
  rubric: Rubric;
  items: AssessmentItem[];
  tags: string[];
  is_favourite: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

// ---------- Class + learner ----------

export interface SchoolClass {
  id: ID;
  school_id: ID;
  teacher_id: ID;
  name: string;
  grade_level: string;
  learning_area_codes: string[];
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Learner {
  id: ID;
  school_id: ID;
  class_id: ID;
  full_name: string;
  admission_no: string | null;
  gender: string | null;
  deleted_at: string | null;
}

// ---------- Run + score ----------

export interface AssessmentRun {
  id: ID;
  school_id: ID;
  class_id: ID;
  assessment_id: ID;
  term: string | null;
  started_at: string;
  closed_at: string | null;
}

export interface Score {
  id: ID;             // client-generated UUID for idempotency
  run_id: ID;
  learner_id: ID;
  item_id: string;    // matches AssessmentItem.id
  level: 1 | 2 | 3 | 4 | null;
  note: string | null;
  updated_at: string;
}

// ---------- API request/response shapes ----------

export interface AuthLoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user: User;
}

export interface AuthRefreshRequest {
  refresh_token: string;
}

export interface GenerateAssessmentRequest {
  learning_area_code: string;
  strand_code: string;
  sub_strand_codes: string[];
  grade_level: string;
  teacher_prompt?: string;
  item_count?: number;     // default 5
}

export interface GenerateAssessmentResponse {
  rubric: Rubric;
  items: AssessmentItem[];
  provider: 'mock' | 'openai' | 'anthropic';
  model: string;
}

export interface ScoreBatchRequest {
  scores: Score[];
}

export interface ScoreBatchResponse {
  accepted: number;
  rejected: { id: ID; reason: string }[];
}

export interface FeatureFlags {
  paywall_enabled: boolean;
  ai_generation_enabled: boolean;
  max_classes: number | null;
  max_learners_per_class: number | null;
}

export interface PaginatedResponse<T> {
  total: number;
  offset: number;
  limit: number;
  items: T[];
}
