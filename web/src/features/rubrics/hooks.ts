import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import type { Rubric, RubricLevel, RubricCriterion } from '@mwalimukit/types';
import { defaultRubric } from '@/features/rubrics';
import toast from 'react-hot-toast';

export function useRubric(id: string) {
  return useQuery({
    queryKey: ['assessment-rubric', id],
    queryFn: () => apiFetch<{ rubric: Rubric }>(`/assessments/${id}`),
    select: (data) => data.rubric,
    enabled: !!id,
  });
}

export function useUpdateRubric() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, rubric }: { id: string; rubric: Rubric }) =>
      apiFetch(`/assessments/${id}`, {
        method: 'PATCH',
        json: { rubric },
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['assessment', variables.id] });
      toast.success('Rubric updated');
    },
    onError: () => toast.error('Failed to update rubric'),
  });
}

export { defaultRubric };
export type { Rubric, RubricLevel, RubricCriterion };
