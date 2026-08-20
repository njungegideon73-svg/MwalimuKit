import type { Rubric, RubricCriterion } from '@mwalimukit/types';

export const DEFAULT_LEVEL_LABELS = [
  'Below expectation',
  'Approaching expectation',
  'Meeting expectation',
  'Exceeding expectation',
] as const;

export function defaultRubric(criteria: RubricCriterion[] = [
  { id: 'accuracy', label: 'Accuracy of response' },
  { id: 'reasoning', label: 'Reasoning / justification' },
  { id: 'communication', label: 'Communication of ideas' },
]): Rubric {
  return {
    levels: DEFAULT_LEVEL_LABELS.map((label, i) => ({
      level: (i + 1) as 1 | 2 | 3 | 4,
      label,
      descriptor: '',
    })),
    criteria,
  };
}

export const EMPTY_RUBRIC = defaultRubric();
