// Shared API / domain types. These mirror the FastAPI Pydantic schemas
// in api/app/schemas/ and the Dexie tables in web/src/lib/db.ts.
// Keep them in sync manually for v0.1; v0.2 will generate from the
// OpenAPI schema.

export type ID = string;

export type Level = 'lower_primary' | 'upper_primary' | 'jss' | 'senior_school';

/** CBC/CBE educational levels per Kenya's 2-6-3-3-3 structure:
 *  - lower_primary: Grades 1-3 (Ages 6-8)
 *  - upper_primary: Grades 4-6 (Ages 9-11)
 *  - jss: Junior School, Grades 7-9 (Ages 12-15)
 *  - senior_school: Grades 10-12 (Ages 15-18) - STEM, Social Sciences, Arts & Sports pathways
 */

export type UserRole = 'teacher' | 'school_admin' | 'super_admin';

export type AssessmentSource = 'ai' | 'manual' | 'template';

// ---------- Curriculum ----------

export interface LearningArea {
  id: ID;
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
  color?: string;
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
  diagram_description?: string | null;
  diagram_type?: string | null;
  diagram_data?: string | null;
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

// ---------- Prompt History ----------

export interface PromptHistoryEntry {
  id: ID;
  assessment_id: ID | null;
  learning_area_code: string;
  strand_code: string;
  sub_strand_codes: string[];
  grade_level: string;
  teacher_prompt: string | null;
  item_count: number;
  provider: string;
  model: string;
  feedback: string | null;
  created_at: string;
}

// ---------- Background Jobs ----------

export type JobType =
  | 'assessment_pdf'
  | 'assessment_docx'
  | 'report_card_pdf'
  | 'sba_report_card_pdf'
  | 'class_summary_csv'
  | 'term_exam_class_csv'
  | 'scheme_of_work_pdf';

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface ExportJob {
  id: ID;
  type: JobType;
  status: JobStatus;
  payload: Record<string, unknown>;
  result: { filename: string; file_path: string; size_bytes: number; content_type: string } | null;
  error: string | null;
  idempotency_key: string | null;
  created_at: string;
  updated_at: string;
}

// ---------- Schemes of Work ----------

export type CalendarInterruptionType =
  | 'mid_term_break'
  | 'exam_week'
  | 'public_holiday'
  | 'school_activity'
  | 'other';

export interface CalendarInterruption {
  week_number: number;
  interruption_type: CalendarInterruptionType;
  label: string;
}

export interface SchemeOfWork {
  id: ID;
  name: string;
  sub_strand_code: string;
  grade: string;
  learning_area_code: string;
  academic_year: string;
  term_number: 1 | 2 | 3;
  lessons_per_week: number;
  total_weeks: number;
  created_at: string;
  updated_at: string;
}

export interface SchemeLesson {
  id: ID;
  scheme_id: ID;
  week_number: number;
  lesson_number: number;
  content_id: ID | null;
  is_break: boolean;
  break_label: string | null;
  strand_code: string | null;
  sub_strand_code: string | null;
  topic: string | null;
  learning_outcomes: string[];
  learning_experiences: string[];
  key_inquiry_questions: string[];
  resources: string[];
  assessment_methods: string[];
  notes: string | null;
}

export interface SchemeOfWorkDetail {
  scheme: SchemeOfWork;
  lessons: SchemeLesson[];
}

export interface SchemeOfWorkCreate {
  name: string;
  sub_strand_code: string;
  grade: string;
  learning_area_code: string;
  academic_year: string;
  term_number: 1 | 2 | 3;
  lessons_per_week: number;
  total_weeks: number;
  calendar_interruptions: CalendarInterruption[];
}

export interface SchemePreviewItem {
  week_number: number;
  lesson_number: number;
  lesson_sequence: number | null;
  is_break: boolean;
  break_label: string | null;
  strand_code: string | null;
  sub_strand_code: string | null;
  topic: string | null;
  learning_outcomes: string[] | null;
  learning_experiences: string[] | null;
  key_inquiry_questions: string[] | null;
  resources: string[] | null;
  assessment_methods: string[] | null;
  notes: string | null;
}

export interface SchemePreviewResponse {
  scheme: SchemeOfWork;
  lessons: SchemePreviewItem[];
}

export interface LessonContent {
  id: ID;
  sub_strand_code: string;
  term_number: number;
  sequence_order: number;
  topic: string;
  learning_outcomes: string[];
  learning_experiences: string[];
  key_inquiry_questions: string[];
  resources: string[];
  assessment_methods: string[];
  value_signs: string[] | null;
  core_competences: string[] | null;
}
