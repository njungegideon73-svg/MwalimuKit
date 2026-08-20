import { useQuery } from '@tanstack/react-query';
import { fetchMySchool } from '@/features/schools/api';

export function useMySchool() {
  return useQuery({
    queryKey: ['school', 'me'],
    queryFn: fetchMySchool,
  });
}
