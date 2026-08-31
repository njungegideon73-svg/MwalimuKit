import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Users, BookOpen } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import { getCurriculum } from '@/lib/curriculum';
import toast from 'react-hot-toast';
import type { SchoolClass } from '@mwalimukit/types';

const classSchema = z.object({
  name: z.string().min(1, 'Class name is required'),
  grade_level: z.string().min(1, 'Grade level is required'),
});
type ClassFormData = z.infer<typeof classSchema>;

export function ClassesPage() {
  const queryClient = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const [selectedAreas, setSelectedAreas] = useState<string[]>([]);

  const { data: classes = [], isLoading } = useQuery<SchoolClass[]>({
    queryKey: ['classes'],
    queryFn: () => apiFetch('/classes'),
  });

  const { data: learningAreas = [] } = useQuery({
    queryKey: ['curriculum', 'learning_areas'],
    queryFn: async () => {
      const c = await getCurriculum();
      return c.learning_areas;
    },
    staleTime: 5 * 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (data: ClassFormData) =>
      apiFetch<SchoolClass>('/classes', {
        method: 'POST',
        json: { ...data, learning_area_codes: selectedAreas },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['classes'] });
      setShowNew(false);
      reset();
      setSelectedAreas([]);
      toast.success('Class created');
    },
    onError: () => toast.error('Failed to create class'),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm<ClassFormData>({
    resolver: zodResolver(classSchema),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Classes</h1>
          <p className="text-gray-500 text-sm mt-1">Manage your classes and learners</p>
        </div>
        <button onClick={() => setShowNew(true)} className="btn-primary">
          <Plus className="h-4 w-4" /> New class
        </button>
      </div>

      {showNew && (
        <form onSubmit={handleSubmit((data) => createMutation.mutate(data))} className="card space-y-4">
          <h2 className="font-semibold text-gray-900">New class</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Class name</label>
              <input {...register('name')} className="input" placeholder="e.g. Grade 1 Blue" />
              {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
            </div>
            <div>
              <label className="label">Grade level</label>
              <select {...register('grade_level')} className="input">
                <option value="">Select...</option>
                <optgroup label="Pre-Primary">
                  <option value="PP1">PP1 (Pre-Primary 1)</option>
                  <option value="PP2">PP2 (Pre-Primary 2)</option>
                </optgroup>
                <optgroup label="Lower Primary (Grades 1-3)">
                  <option value="Grade 1">Grade 1</option>
                  <option value="Grade 2">Grade 2</option>
                  <option value="Grade 3">Grade 3</option>
                </optgroup>
                <optgroup label="Upper Primary (Grades 4-6)">
                  <option value="Grade 4">Grade 4</option>
                  <option value="Grade 5">Grade 5</option>
                  <option value="Grade 6">Grade 6</option>
                </optgroup>
                <optgroup label="Junior School (Grades 7-9)">
                  <option value="Grade 7">Grade 7</option>
                  <option value="Grade 8">Grade 8</option>
                  <option value="Grade 9">Grade 9</option>
                </optgroup>
                <optgroup label="Senior School (Grades 10-12)">
                  <option value="Grade 10">Grade 10</option>
                  <option value="Grade 11">Grade 11</option>
                  <option value="Grade 12">Grade 12</option>
                </optgroup>
              </select>
              {errors.grade_level && <p className="mt-1 text-sm text-red-600">{errors.grade_level.message}</p>}
            </div>
          </div>
          <div>
            <label className="label">Learning areas (optional)</label>
            <div className="flex flex-wrap gap-2">
              {learningAreas.map((la) => (
                <label key={la.code} className="flex items-center gap-1.5 text-sm cursor-pointer">
                  <input type="checkbox" checked={selectedAreas.includes(la.code)}
                    onChange={(e) => setSelectedAreas(e.target.checked
                      ? [...selectedAreas, la.code]
                      : selectedAreas.filter((c) => c !== la.code))}
                    className="accent-primary-500" />
                  {la.name}
                </label>
              ))}
            </div>
          </div>
          <div className="flex gap-3">
            <button type="submit" disabled={createMutation.isPending} className="btn-primary">
              {createMutation.isPending ? 'Creating...' : 'Create class'}
            </button>
            <button type="button" onClick={() => setShowNew(false)} className="btn-secondary">Cancel</button>
          </div>
        </form>
      )}

      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => <div key={i} className="h-20 bg-gray-200 rounded-xl" />)}
        </div>
      ) : classes.length === 0 ? (
        <div className="card text-center py-12">
          <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No classes yet</p>
          <button onClick={() => setShowNew(true)} className="btn-primary mt-4">
            <Plus className="h-4 w-4" /> Create your first class
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {classes.map((c) => (
            <Link key={c.id} to={`/classes/${c.id}`}
              className="flex items-center justify-between rounded-xl bg-white border border-gray-200 px-4 py-3 hover:border-primary-300 transition-colors">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center">
                  <BookOpen className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="font-medium text-gray-900">{c.name}</p>
                  <p className="text-sm text-gray-500">{c.grade_level}</p>
                </div>
              </div>
              <span className="text-sm text-gray-400">{new Date(c.created_at).toLocaleDateString()}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
