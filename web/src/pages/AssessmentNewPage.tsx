import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft, Sparkles, Plus, Trash2 } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { getCurriculum } from '@/lib/curriculum';
import { defaultRubric } from '@mwalimukit/rubrics';
import toast from 'react-hot-toast';
import type { LearningArea, Strand, SubStrand, AssessmentItem, Rubric } from '@mwalimukit/types';

const schema = z.object({
  name: z.string().min(1, 'Assessment name is required'),
  description: z.string().optional(),
  mode: z.enum(['ai', 'manual']),
  learning_area_code: z.string().min(1, 'Select a learning area'),
  strand_code: z.string().min(1, 'Select a strand'),
  sub_strand_code: z.string().min(1, 'Select a sub-strand'),
  grade_level: z.string().min(1, 'Enter grade level'),
  teacher_prompt: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export function AssessmentNewPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [items, setItems] = useState<AssessmentItem[]>([]);
  const [rubric, setRubric] = useState<Rubric>(defaultRubric());
  const [curriculum, setCurriculum] = useState<{
    learning_areas: LearningArea[];
    strands: Strand[];
    sub_strands: SubStrand[];
  } | null>(null);

  const { register, handleSubmit, watch, setValue } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      mode: 'ai',
      grade_level: 'Grade 1',
    },
  });

  const selectedLA = watch('learning_area_code');
  const selectedStrand = watch('strand_code');
  const mode = watch('mode');

  useEffect(() => {
    getCurriculum().then(setCurriculum);
  }, []);

  const filteredStrands = curriculum?.strands.filter((s) => s.learning_area_code === selectedLA) ?? [];
  const filteredSubStrands = curriculum?.sub_strands.filter((s) => s.strand_code === selectedStrand) ?? [];

  useEffect(() => {
    setValue('strand_code', '');
    setValue('sub_strand_code', '');
  }, [selectedLA, setValue]);

  useEffect(() => {
    setValue('sub_strand_code', '');
  }, [selectedStrand, setValue]);

  const handleGenerate = useCallback(async (data: FormData) => {
    setGenerating(true);
    try {
      const result = await apiFetch<{
        rubric: Rubric;
        items: AssessmentItem[];
      }>('/assessments/generate', {
        method: 'POST',
        json: {
          learning_area_code: data.learning_area_code,
          strand_code: data.strand_code,
          sub_strand_codes: [data.sub_strand_code],
          grade_level: data.grade_level,
          teacher_prompt: data.teacher_prompt,
          item_count: 5,
        },
      });
      setItems(result.items);
      setRubric(result.rubric);
      toast.success('Assessment generated!');
    } catch {
      toast.error('Failed to generate assessment');
    } finally {
      setGenerating(false);
    }
  }, []);

  const handleSave = async (data: FormData) => {
    if (items.length === 0) {
      toast.error('Add at least one assessment item');
      return;
    }
    setLoading(true);
    try {
      const result = await apiFetch<{ id: string }>('/assessments', {
        method: 'POST',
        json: {
          name: data.name,
          description: data.description,
          learning_area_code: data.learning_area_code,
          strand_code: data.strand_code,
          sub_strand_codes: [data.sub_strand_code],
          source: data.mode,
          rubric,
          items,
          tags: [],
          is_favourite: false,
        },
      });
      toast.success('Assessment saved!');
      navigate(`/assessments/${result.id}`);
    } catch {
      toast.error('Failed to save assessment');
    } finally {
      setLoading(false);
    }
  };

  const addItem = () => {
    setItems([
      ...items,
      {
        id: `itm_${String(items.length + 1).padStart(2, '0')}`,
        criterion: rubric.criteria[0]?.id ?? 'accuracy',
        stem: '',
        answer_guide: '',
        max_level: 4,
      },
    ]);
  };

  const removeItem = (idx: number) => {
    setItems(items.filter((_, i) => i !== idx));
  };

  const updateItem = (idx: number, field: keyof AssessmentItem, value: string) => {
    setItems(items.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));
  };

  if (!curriculum) {
    return (
      <div className="space-y-4 animate-pulse">
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
        <h1 className="text-2xl font-bold text-gray-900">New assessment</h1>
        <p className="text-gray-500 text-sm mt-1">Pick a strand, generate or build manually</p>
      </div>

      <form onSubmit={handleSubmit(mode === 'ai' && items.length === 0 ? handleGenerate : handleSave)}>
        {/* Strand picker */}
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">1. Choose strand</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Learning area</label>
              <select {...register('learning_area_code')} className="input">
                <option value="">Select area...</option>
                {curriculum.learning_areas.map((la) => (
                  <option key={la.code} value={la.code}>
                    {la.name} ({la.level})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Strand</label>
              <select {...register('strand_code')} className="input" disabled={!selectedLA}>
                <option value="">Select strand...</option>
                {filteredStrands.map((s) => (
                  <option key={s.code} value={s.code}>
                    {s.code} — {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Sub-strand</label>
              <select {...register('sub_strand_code')} className="input" disabled={!selectedStrand}>
                <option value="">Select sub-strand...</option>
                {filteredSubStrands.map((ss) => (
                  <option key={ss.code} value={ss.code}>
                    {ss.code} — {ss.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Grade level</label>
              <input {...register('grade_level')} className="input" placeholder="Grade 1" />
            </div>
          </div>

          <div>
            <label className="label">Mode</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" value="ai" {...register('mode')} className="accent-primary-500" />
                <span className="text-sm">AI draft</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" value="manual" {...register('mode')} className="accent-primary-500" />
                <span className="text-sm">Structured template</span>
              </label>
            </div>
          </div>

          {mode === 'ai' && (
            <div>
              <label className="label">Teacher guidance (optional)</label>
              <textarea
                {...register('teacher_prompt')}
                className="input"
                rows={2}
                placeholder="e.g. Focus on word problems, use Kenyan currency"
              />
            </div>
          )}
        </div>

        {/* Assessment items */}
        <div className="card space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">2. Assessment items</h2>
            {mode === 'ai' && items.length === 0 && (
              <button
                type="submit"
                disabled={generating}
                className="btn-primary"
              >
                <Sparkles className="h-4 w-4" />
                {generating ? 'Generating...' : 'Generate with AI'}
              </button>
            )}
          </div>

          {items.map((item, idx) => (
            <div key={item.id} className="border border-gray-200 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-medium text-sm text-gray-700">Item {idx + 1}</span>
                <button type="button" onClick={() => removeItem(idx)} className="text-gray-400 hover:text-red-600">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <textarea
                value={item.stem}
                onChange={(e) => updateItem(idx, 'stem', e.target.value)}
                className="input"
                rows={2}
                placeholder="Question stem..."
              />
              <input
                value={item.answer_guide ?? ''}
                onChange={(e) => updateItem(idx, 'answer_guide', e.target.value)}
                className="input"
                placeholder="Answer guide (optional)"
              />
            </div>
          ))}

          {mode === 'manual' || items.length > 0 ? (
            <button type="button" onClick={addItem} className="btn-secondary">
              <Plus className="h-4 w-4" /> Add item
            </button>
          ) : null}

          {mode === 'manual' && items.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">
              Add assessment items to create your template
            </p>
          )}
        </div>

        {/* Save */}
        <div className="card mt-4 space-y-4">
          <h2 className="font-semibold text-gray-900">3. Save</h2>
          <div>
            <label className="label">Assessment name</label>
            <input
              {...register('name')}
              className="input"
              placeholder="e.g. Counting 0-20 check"
            />
          </div>
          <div>
            <label className="label">Description (optional)</label>
            <textarea {...register('description')} className="input" rows={2} />
          </div>
          <button type="submit" disabled={loading || items.length === 0} className="btn-primary w-full">
            {loading ? 'Saving...' : 'Save assessment'}
          </button>
        </div>
      </form>
    </div>
  );
}
