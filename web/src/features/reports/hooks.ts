import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRuns, createContextRun, closeRun } from '@/features/reports/api';
import toast from 'react-hot-toast';

export function useRuns(classId?: string) {
  return useQuery({
    queryKey: ['runs', classId],
    queryFn: () => fetchRuns(classId),
    enabled: !!classId,
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, assessmentId }: { classId: string; assessmentId: string }) =>
      createContextRun(classId, assessmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      toast.success('Run created');
    },
    onError: () => toast.error('Failed to create run'),
  });
}

export function useCloseRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => closeRun(runId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      toast.success('Run closed');
    },
    onError: () => toast.error('Failed to close run'),
  });
}
