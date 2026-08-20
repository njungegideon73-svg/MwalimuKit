import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchLearnersByClass,
  createLearner,
  bulkCreateLearners,
  updateLearner,
  deleteLearner,
} from '@/features/learners/api';
import toast from 'react-hot-toast';

export function useLearnersByClass(classId: string) {
  return useQuery({
    queryKey: ['learners', classId],
    queryFn: () => fetchLearnersByClass(classId),
    enabled: !!classId,
  });
}

export function useCreateLearner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, ...payload }: { classId: string; full_name: string; admission_no?: string | null; gender?: string | null }) =>
      createLearner(classId, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['learners', variables.classId] });
      toast.success('Learner added');
    },
    onError: () => toast.error('Failed to add learner'),
  });
}

export function useBulkCreateLearners() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, lines }: { classId: string; lines: string[] }) =>
      bulkCreateLearners(classId, lines),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['learners', variables.classId] });
      toast.success('Learners added');
    },
    onError: () => toast.error('Failed to add learners'),
  });
}

export function useUpdateLearner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ learnerId, ...payload }: { learnerId: string; full_name: string; admission_no?: string | null; gender?: string | null }) =>
      updateLearner(learnerId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learners'] });
      toast.success('Learner updated');
    },
    onError: () => toast.error('Failed to update learner'),
  });
}

export function useDeleteLearner() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteLearner,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learners'] });
      toast.success('Learner deleted');
    },
    onError: () => toast.error('Failed to delete learner'),
  });
}
