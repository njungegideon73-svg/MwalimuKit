import { useState, useEffect } from 'react';
import { ArrowLeft, Sparkles, Plus } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import {
  useCurriculum,
  useAssessmentGeneration,
  useAssessmentItems,
  useNavigation,
  useOnlineStatus,
  assessmentFormSchema,
} from '@/features/assess/hooks';
import { createAssessment } from '@/features/assess/api';
import { defaultRubric } from '@mwalimukit/rubrics';
import { RubricEditor } from '@/components/RubricEditor';
import { PromptHistoryPanel } from '@/components/PromptHistoryPanel';
import {
  StrandSelector,
  ModeToggle,
  AssessmentItemListEditor,
} from '@/features/assess/components/AssessmentForm';
import type { FormData } from '@/features/assess/hooks';
import type { AssessmentItem, Rubric } from '@mwalimukit/types';
import { useFeatureFlags } from '@/lib/feature-flags';
import toast from 'react-hot-toast';

export function AssessmentNewPage() {
  const { goBack, goToAssessment } = useNavigation();
  const queryClient = useQueryClient();
  const isOnline = useOnlineStatus();
  const aiEnabled = useFeatureFlags((s) => s.ai_generation_enabled);
  const {
    items,
    rubric,
    setItems,
    setRubric,
  } = useAssessmentItems([], defaultRubric());

  const { register, handleSubmit, watch, setValue } = useForm<FormData>({
    resolver: zodResolver(assessmentFormSchema),
    defaultValues: { mode: 'ai', grade_level: 'Grade 1' },
  });

  const selectedLA = watch('learning_area_code');
  const selectedStrand = watch('strand_code');
  const mode = watch('mode');
  const { generation } = useAssessmentGeneration();
  const [strandSearch, setStrandSearch] = useState('');

  useEffect(() => {
    if (!aiEnabled || !isOnline) setValue('mode', 'manual');
  }, [aiEnabled, isOnline, setValue]);

  useEffect(() => {
    setValue('strand_code', '');
    setValue('sub_strand_code', '');
  }, [selectedLA, setValue]);

  useEffect(() => {
    setValue('sub_strand_code', '');
  }, [selectedStrand, setValue]);

  useEffect(() => {
    if (generation.data) {
      setItems(generation.data.items as unknown as AssessmentItem[]);
      setRubric(generation.data.rubric as unknown as Rubric);
    }
  }, [generation.data, setItems, setRubric]);

  const { data: curriculum, isLoading: curriculumLoading } = useCurriculum();

  const saveMutation = useMutation({
    mutationFn: (data: FormData) =>
      createAssessment({
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
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['assessments'] });
      toast.success('Assessment saved!');
      goToAssessment(result.id);
    },
    onError: () => toast.error('Failed to save assessment'),
  });

  const handleGenerate = (data: FormData) => {
    generation.mutate({
      learning_area_code: data.learning_area_code,
      strand_code: data.strand_code,
      sub_strand_codes: [data.sub_strand_code],
      grade_level: data.grade_level,
      teacher_prompt: data.teacher_prompt,
      item_count: data.item_count,
      include_diagrams: data.include_diagrams,
    });
  };

  const handleSave = (data: FormData) => {
    if (items.length === 0) {
      toast.error('Add at least one assessment item');
      return;
    }
    saveMutation.mutate(data);
  };

  if (curriculumLoading || !curriculum) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="h-64 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={goBack} className="btn-ghost text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">New assessment</h1>
        <p className="text-gray-500 text-sm mt-1">Pick a strand, generate or build manually</p>
      </div>

      <PromptHistoryPanel
        onUsePrompt={(entry) => {
          if (entry.teacher_prompt) setValue('teacher_prompt', entry.teacher_prompt);
          setValue('learning_area_code', entry.learning_area_code);
          toast.success('Prompt restored from history');
        }}
      />

      <form onSubmit={handleSubmit(mode === 'ai' && items.length === 0 ? handleGenerate : handleSave)}>
        <div className="card space-y-4">
          <h2 className="font-semibold text-gray-900">1. Choose strand</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <StrandSelector
              curriculum={curriculum}
              selectedLA={selectedLA}
              selectedStrand={selectedStrand}
              strandSearch={strandSearch}
              setStrandSearch={setStrandSearch}
              register={register}
            />
          </div>

          <ModeToggle mode={mode} aiEnabled={aiEnabled} isOnline={isOnline} register={register} />

          {mode === 'ai' && isOnline && (
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

          {mode === 'ai' && isOnline && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Number of questions</label>
                <input
                  type="number"
                  {...register('item_count', { valueAsNumber: true })}
                  className="input"
                  min={1}
                  max={20}
                />
                <p className="text-xs text-gray-500 mt-1">Choose between 1 and 20 questions</p>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer pb-2">
                  <input
                    type="checkbox"
                    {...register('include_diagrams')}
                    className="accent-primary-500"
                  />
                  <span className="text-sm">Include diagram / chart prompts</span>
                </label>
              </div>
            </div>
          )}
        </div>

        <div className="card space-y-4 mt-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">2. Assessment items</h2>
            {mode === 'ai' && items.length === 0 && isOnline && (
              <button type="submit" disabled={generation.isPending} className="btn-primary">
                <Sparkles className="h-4 w-4" />
                {generation.isPending ? 'Generating...' : 'Generate with AI'}
              </button>
            )}
          </div>

          <AssessmentItemListEditor
            items={items}
            onItemsChange={setItems}
          />

          <button type="button" onClick={() => {
            const newLength = items.length + 1;
            setItems([...items, {
              id: `itm_${String(newLength).padStart(2, '0')}`,
              criterion: 'accuracy',
              stem: '',
              answer_guide: '',
              max_level: 4,
              diagram_description: '',
            }]);
          }} className="btn-secondary">
            <Plus className="h-4 w-4" /> Add item
          </button>

          {mode === 'manual' && items.length === 0 && (
            <p className="text-sm text-gray-500 text-center py-4">
              Add assessment items to create your template
            </p>
          )}
        </div>

        <div className="card mt-4 space-y-4">
          <h2 className="font-semibold text-gray-900">3. Rubric</h2>
          <p className="text-sm text-gray-500">Edit levels, descriptors, and criteria. Drag to reorder criteria.</p>
          <RubricEditor value={rubric} onChange={setRubric} />
        </div>

        <div className="card mt-4 space-y-4">
          <h2 className="font-semibold text-gray-900">4. Save</h2>
          <div>
            <label className="label">Assessment name</label>
            <input {...register('name')} className="input" placeholder="e.g. Counting 0-20 check" />
          </div>
          <div>
            <label className="label">Description (optional)</label>
            <textarea {...register('description')} className="input" rows={2} />
          </div>
          <button
            type="submit"
            disabled={saveMutation.isPending || items.length === 0}
            className="btn-primary w-full"
          >
            {saveMutation.isPending ? 'Saving...' : 'Save assessment'}
          </button>
        </div>
      </form>
    </div>
  );
}
