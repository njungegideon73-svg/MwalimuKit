/**
 * CBC/CBE Grading Constants
 *
 * Kenya's Competency-Based Education (CBE) grading system uses four broad
 * performance bands (per KNEC guidelines). Learners are placed into these
 * bands based on their percentage score:
 *
 *   EE (Exceeding Expectations):  75–100%
 *   ME (Meeting Expectations):    41–74%
 *   AE (Approaching Expectations): 21–40%
 *   BE (Below Expectations):      0–20%
 *
 * Reference: https://educationnews.co.ke/knec-releases-guidelines-for-junior-school-summative-assessments/
 */

export type CbcGrade = 'EE' | 'ME' | 'AE' | 'BE';

export interface GradeBand {
  code: CbcGrade;
  label: string;
  description: string;
  minPercentage: number;
  maxPercentage: number;
  color: string;       // Tailwind text color class
  bgColor: string;     // Tailwind bg-color class for badges
  points: [number, number]; // Achievement Level points range (1-8)
}

export const GRADE_BANDS: GradeBand[] = [
  {
    code: 'EE',
    label: 'Exceeding Expectations',
    description: 'Learner demonstrates exceptional understanding and application',
    minPercentage: 75,
    maxPercentage: 100,
    color: 'text-green-600',
    bgColor: 'bg-green-100 text-green-800',
    points: [7, 8],
  },
  {
    code: 'ME',
    label: 'Meeting Expectations',
    description: 'Learner demonstrates satisfactory understanding',
    minPercentage: 41,
    maxPercentage: 74,
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 text-blue-800',
    points: [5, 6],
  },
  {
    code: 'AE',
    label: 'Approaching Expectations',
    description: 'Learner shows partial understanding, needs support',
    minPercentage: 21,
    maxPercentage: 40,
    color: 'text-amber-600',
    bgColor: 'bg-amber-100 text-amber-800',
    points: [3, 4],
  },
  {
    code: 'BE',
    label: 'Below Expectations',
    description: 'Learner requires significant intervention',
    minPercentage: 0,
    maxPercentage: 20,
    color: 'text-red-600',
    bgColor: 'bg-red-100 text-red-800',
    points: [1, 2],
  },
];

/**
 * Compute the CBC grade band from a percentage score.
 * @param percentage - Score as a percentage (0-100)
 * @returns The CBC grade code (EE, ME, AE, or BE)
 */
export function computeGradeFromPercentage(percentage: number): CbcGrade {
  if (percentage >= 75) return 'EE';
  if (percentage >= 41) return 'ME';
  if (percentage >= 21) return 'AE';
  return 'BE';
}

/**
 * Compute the CBC grade band from raw marks.
 * @param marks - Raw score obtained
 * @param maxMarks - Maximum possible marks
 * @returns The CBC grade code (EE, ME, AE, or BE)
 */
export function computeGradeFromMarks(marks: number, maxMarks: number): CbcGrade {
  const percentage = maxMarks > 0 ? (marks / maxMarks) * 100 : 0;
  return computeGradeFromPercentage(percentage);
}

/**
 * Convert raw marks to a percentage.
 * @param marks - Raw score obtained
 * @param maxMarks - Maximum possible marks
 * @returns Percentage (0-100)
 */
export function marksToPercentage(marks: number, maxMarks: number): number {
  return maxMarks > 0 ? (marks / maxMarks) * 100 : 0;
}

/**
 * Get the full label for a grade code.
 */
export function getGradeLabel(grade: CbcGrade): string {
  const band = GRADE_BANDS.find((b) => b.code === grade);
  return band?.label || grade;
}

/**
 * Get the color class for a grade code.
 */
export function getGradeColor(grade: CbcGrade): string {
  const band = GRADE_BANDS.find((b) => b.code === grade);
  return band?.color || 'text-gray-600';
}

/**
 * Get the badge bg color class for a grade code.
 */
export function getGradeBadgeColor(grade: CbcGrade): string {
  const band = GRADE_BANDS.find((b) => b.code === grade);
  return band?.bgColor || 'bg-gray-100 text-gray-800';
}
