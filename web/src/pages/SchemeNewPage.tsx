import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, CalendarPlus } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCurriculum } from '@/features/assess/hooks';
import { useCreateScheme } from '@/features/schemes/hooks';
import type { CalendarInterruptionType } from '@mwalimukit/types';
import toast from 'react-hot-toast';

const schemeSchema = z.object({
  name: z.string().min(1, 'Scheme name is required'),
  learning_area_code: z.string().min(1, 'Learning area is required'),
  strand_code: z.string().min(1, 'Strand is required'),
  sub_strand_code: z.string().min(1, 'Sub-strand is required'),
  grade: z.string().min(1, 'Grade is required'),
  academic_year: z.string().min(1, 'Academic year is required'),
  term_number: z.number().int().min(1).max(3),
  lessons_per_week: z.number().int().min(1).max(10),
  total_weeks: z.number().int().min(1).max(20),
});

type SchemeFormData = z.infer<typeof schemeSchema>;

interface InterruptionRow {
  week_number: number;
  interruption_type: CalendarInterruptionType;
  label: string;
}

const INTERRUPTION_TYPES: { value: CalendarInterruptionType; label: string }[] = [
  { value: 'mid_term_break', label: 'Mid-term break' },
  { value: 'exam_week', label: 'Exam week' },
  { value: 'public_holiday', label: 'Public holiday' },
  { value: 'school_activity', label: 'School activity' },
  { value: 'other', label: 'Other' },
];

const DEFAULT_INTERRUPTIONS: InterruptionRow[] = [
  { week_number: 7, interruption_type: 'mid_term_break', label: 'Mid-term break' },
  { week_number: 12, interruption_type: 'exam_week', label: 'End of term exams' },
];

export function SchemeNewPage() {
  const navigate = useNavigate();
  const { register, handleSubmit, watch, setValue } = useForm<SchemeFormData>({
    resolver: zodResolver(schemeSchema),
    defaultValues: {
      academic_year: String(new Date().getFullYear()),
      term_number: 1,
      lessons_per_week: 3,
      total_weeks: 14,
      grade: 'Grade 1',
    },
  });

  const [interruptions, setInterruptions] = useState<InterruptionRow[]>(DEFAULT_INTERRUPTIONS);

  const selectedLA = watch('learning_area_code');
  const selectedStrand = watch('strand_code');

  const { data: curriculum, isLoading: curriculumLoading } = useCurriculum();
  const createScheme = useCreateScheme((scheme) => {
    toast.success('Scheme of work generated');
    navigate(`/schemes/${scheme.id}/preview`);
  });

  useEffect(() => {
    setValue('strand_code', '');
    setValue('sub_strand_code', '');
  }, [selectedLA, setValue]);

  useEffect(() => {
    setValue('sub_strand_code', '');
  }, [selectedStrand, setValue]);

  const learningAreas = curriculum?.learning_areas ?? [];
  const strands = (curriculum?.strands ?? []).filter((s) => s.learning_area_code === selectedLA);
  const subStrands = (curriculum?.sub_strands ?? []).filter((s) => s.strand_code === selectedStrand);

  const onSubmit = (data: SchemeFormData) => {
    createScheme.mutate({
      name: data.name,
      sub_strand_code: data.sub_strand_code,
      grade: data.grade,
      learning_area_code: data.learning_area_code,
      academic_year: data.academic_year,
      term_number: data.term_number as 1 | 2 | 3,
      lessons_per_week: data.lessons_per_week,
      total_weeks: data.total_weeks,
      calendar_interruptions: interruptions
        .filter((i) => i.week_number >= 1 && i.week_number <= data.total_weeks)
        .map((i) => ({ week_number: i.week_number, interruption_type: i.interruption_type, label: i.label })),
    });
  };

  if (curriculumLoading || !curriculum) {
    return (
      <div className="space-y-4 animate-pulse max-w-3xl mx-auto">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="h-64 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="btn-ghost text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">New scheme of work</h1>
        <p className="text-gray-500 text-sm mt-1">
          Pick a sub-strand and a term calendar. Lessons are scheduled from the content bank.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">1. Curriculum</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Learning area</label>
              <select {...register('learning_area_code')} className="input">
                <option value="">Select...</option>
                {learningAreas.map((la) => (
                  <option key={la.code} value={la.code}>
                    {la.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Grade</label>
              <select {...register('grade')} className="input">
                {['Grade 1', 'Grade 2', 'Grade 3', 'Grade 4', 'Grade 5', 'Grade 6', 'Grade 7', 'Grade 8', 'Grade 9'].map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Strand</label>
              <select {...register('strand_code')} className="input" disabled={!selectedLA}>
                <option value="">{selectedLA ? 'Select...' : 'Choose a learning area first'}</option>
                {strands.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Sub-strand</label>
              <select {...register('sub_strand_code')} className="input" disabled={!selectedStrand}>
                <option value="">{selectedStrand ? 'Select...' : 'Choose a strand first'}</option>
                {subStrands.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">2. Term calendar</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="label">Academic year</label>
              <input {...register('academic_year')} className="input" />
            </div>
            <div>
              <label className="label">Term</label>
              <select {...register('term_number', { valueAsNumber: true })} className="input">
                <option value={1}>Term 1</option>
                <option value={2}>Term 2</option>
                <option value={3}>Term 3</option>
              </select>
            </div>
            <div>
              <label className="label">Total weeks</label>
              <input
                type="number"
                min={1}
                max={20}
                {...register('total_weeks', { valueAsNumber: true })}
                className="input"
              />
            </div>
            <div>
              <label className="label">Lessons / week</label>
              <input
                type="number"
                min={1}
                max={10}
                {...register('lessons_per_week', { valueAsNumber: true })}
                className="input"
              />
            </div>
          </div>
          <p className="text-xs text-gray-500">
            {watch('lessons_per_week') * watch('total_weeks')} lesson slots in this term; the content
            bank is walked in order and repeated if it runs out.
          </p>
        </div>

        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-semibold text-gray-900">3. Calendar interruptions</h2>
              <p className="text-xs text-gray-500 mt-1">
                Breaks and exam weeks are reserved automatically as full weeks.
              </p>
            </div>
            <button
              type="button"
              onClick={() =>
                setInterruptions([...interruptions, { week_number: 1, interruption_type: 'other', label: '' }])
              }
              className="btn-secondary text-sm"
            >
              <Plus className="h-4 w-4" /> Add
            </button>
          </div>

          {interruptions.length === 0 ? (
            <p className="text-sm text-gray-500 py-2">No interruptions — lessons run every week of the term.</p>
          ) : (
            <div className="space-y-2">
              {interruptions.map((row, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2 items-center">
                  <div className="col-span-2">
                    <input
                      type="number"
                      min={1}
                      max={watch('total_weeks')}
                      value={row.week_number}
                      placeholder="Week"
                      className="input"
                      onChange={(e) => {
                        const next = [...interruptions];
                        next[idx] = { ...row, week_number: Number(e.target.value) };
                        setInterruptions(next);
                      }}
                    />
                  </div>
                  <div className="col-span-3">
                    <select
                      value={row.interruption_type}
                      className="input"
                      onChange={(e) => {
                        const next = [...interruptions];
                        next[idx] = { ...row, interruption_type: e.target.value as CalendarInterruptionType };
                        setInterruptions(next);
                      }}
                    >
                      {INTERRUPTION_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="col-span-6">
                    <input
                      type="text"
                      value={row.label}
                      placeholder="Label (e.g. Mid-term break)"
                      className="input"
                      onChange={(e) => {
                        const next = [...interruptions];
                        next[idx] = { ...row, label: e.target.value };
                        setInterruptions(next);
                      }}
                    />
                  </div>
                  <div className="col-span-1 flex justify-end">
                    <button
                      type="button"
                      onClick={() => setInterruptions(interruptions.filter((_, i) => i !== idx))}
                      className="p-2 text-gray-400 hover:text-red-600 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {interruptions.some((i) => {
            const others = interruptions.filter((o) => o !== i && o.week_number === i.week_number);
            return others.length > 0;
          }) && (
            <p className="text-xs text-amber-600">
              Two interruptions share the same week — only the first will be shown.
            </p>
          )}
        </div>

        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">4. Name it</h2>
          <div>
            <label className="label">Scheme name</label>
            <input
              {...register('name')}
              className="input"
              placeholder="e.g. Grade 4 Maths Fractions — Term 1"
            />
          </div>
          <button
            type="submit"
            disabled={createScheme.isPending}
            className="btn-primary w-full"
          >
            <CalendarPlus className="h-4 w-4" />
            {createScheme.isPending ? 'Generating...' : 'Generate scheme of work'}
          </button>
        </div>
      </form>
    </div>
  );
}