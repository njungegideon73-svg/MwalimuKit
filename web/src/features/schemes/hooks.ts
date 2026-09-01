import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import type {
  SchemeLesson,
  SchemeOfWork,
  SchemeOfWorkCreate,
  SchemePreviewResponse,
} from '@mwalimukit/types';
import {
  createScheme as createSchemeApi,
  deleteScheme as deleteSchemeApi,
  fetchScheme,
  fetchSchemePreview,
  fetchSchemes,
  updateLessonCell as updateLessonCellApi,
} from './api';

export function useSchemes() {
  return useQuery<SchemeOfWork[]>({
    queryKey: ['schemes'],
    queryFn: fetchSchemes,
  });
}

export function useScheme(id: string | undefined) {
  return useQuery({
    queryKey: ['schemes', id],
    queryFn: () => fetchScheme(id!),
    enabled: !!id,
  });
}

export function useSchemePreview(id: string | undefined) {
  return useQuery<SchemePreviewResponse>({
    queryKey: ['schemes', id, 'preview'],
    queryFn: () => fetchSchemePreview(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useCreateScheme(onSuccess?: (scheme: SchemeOfWork) => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SchemeOfWorkCreate) => createSchemeApi(payload),
    onSuccess: (scheme) => {
      queryClient.invalidateQueries({ queryKey: ['schemes'] });
      onSuccess?.(scheme);
    },
    onError: (err: Error) => toast.error(err.message || 'Failed to generate scheme of work'),
  });
}

export function useDeleteScheme() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSchemeApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schemes'] });
      toast.success('Scheme of work deleted');
    },
    onError: () => toast.error('Failed to delete scheme'),
  });
}

export function useUpdateLessonCell(schemeId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ week, lesson, patch }: { week: number; lesson: number; patch: Partial<SchemeLesson> }) =>
      updateLessonCellApi(schemeId, week, lesson, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schemes', schemeId] });
    },
  });
}