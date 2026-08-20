import { useCallback, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useFeatureFlags } from '@/lib/feature-flags';
import { apiFetch } from '@/lib/api';
import type { AssessmentItem, Rubric, Assessment } from '@mwalimukit/types';
import { defaultRubric } from '@mwalimukit/rubrics';
import { generateAssessment } from '@/features/assess/api';
import toast from 'react-hot-toast';
import { getCurriculum } from '@/lib/curriculum';
import { z } from 'zod';

export const assessmentFormSchema = z.object({
  name: z.string().min(1, 'Assessment name is required'),
  description: z.string().optional(),
  learning_area_code: z.string().min(1, 'Learning area is required'),
  strand_code: z.string().min(1, 'Strand is required'),
  sub_strand_code: z.string().min(1, 'Sub-strand is required'),
  grade_level: z.string().min(1, 'Grade level is required'),
  teacher_prompt: z.string().optional(),
  mode: z.enum(['ai', 'manual']).default('ai'),
  item_count: z.number().int().min(1).max(20).default(5),
  include_diagrams: z.boolean().default(false),
});

export type FormData = z.infer<typeof assessmentFormSchema>;

export interface UseAssessmentEditorOptions {
  mode: 'ai' | 'manual';
  modeAuto: boolean;
}

export function useAssessments() {
  return useQuery({
    queryKey: ['assessments'],
    queryFn: () => apiFetch<{ id: string; name: string }[]>('/assessments'),
  });
}

export function useAssessment(id: string) {
  return useQuery({
    queryKey: ['assessment', id],
    queryFn: () => apiFetch<Assessment>(`/assessments/${id}`),
    enabled: !!id,
  });
}

export function useCurriculum() {
  return useQuery({
    queryKey: ['curriculum'],
    queryFn: getCurriculum,
    staleTime: 5 * 60_000,
  });
}

export function useMutationErrorHandler() {
  const queryClient = useQueryClient();
  const onError = useCallback(
    (error: Error, queryKey?: unknown[]) => {
      toast.error(error.message || 'Something went wrong');
      if (queryKey) queryClient.invalidateQueries({ queryKey });
    },
    [queryClient],
  );
  return { onError, queryClient };
}

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const onOnline = () => setIsOnline(true);
    const onOffline = () => setIsOnline(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);
    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  }, []);
  return isOnline;
}

export function useAssessmentGeneration() {
  const aiEnabled = useFeatureFlags((s) => s.ai_generation_enabled);

  const mutation = useMutation({
    mutationFn: generateAssessment,
    onSuccess: () => toast.success('Assessment generated!'),
    onError: () => toast.error('Failed to generate assessment'),
  });

  return { generation: mutation, aiEnabled };
}

export function useAssessmentItems(initial: AssessmentItem[], rubric: Rubric) {
  const [items, setItems] = useState<AssessmentItem[]>(initial);
  const [selectedRubric, setSelectedRubric] = useState<Rubric>(rubric);

  useEffect(() => {
    if (initial.length > 0) {
      setItems(initial);
    }
  }, [initial]);

  useEffect(() => {
    setSelectedRubric(rubric);
  }, [rubric]);

  const addItem = useCallback(() => {
    setItems((prev) => [
      ...prev,
      {
        id: `itm_${String(prev.length + 1).padStart(2, '0')}`,
        criterion: selectedRubric.criteria[0]?.id ?? 'accuracy',
        stem: '',
        answer_guide: '',
        max_level: 4,
        diagram_description: '',
      },
    ]);
  }, [selectedRubric]);

  const removeItem = useCallback((idx: number) => {
    setItems((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateItem = useCallback((idx: number, field: keyof AssessmentItem, value: string) => {
    setItems((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: value } : item)),
    );
  }, []);

  const setRubricFromGeneration = useCallback((newRubric: Rubric) => {
    setSelectedRubric(newRubric);
  }, []);

  const reset = useCallback(() => {
    setItems([]);
    setSelectedRubric(defaultRubric());
  }, []);

  return {
    items,
    setItems,
    rubric: selectedRubric,
    setRubric: setSelectedRubric,
    addItem,
    removeItem,
    updateItem,
    setRubricFromGeneration,
    reset,
  };
}

export function useNavigation() {
  const navigate = useNavigate();
  const goBack = useCallback(() => navigate(-1), [navigate]);
  const goToAssessment = useCallback((id: string) => navigate(`/assessments/${id}`), [navigate]);
  return { goBack, goToAssessment, navigate };
}
