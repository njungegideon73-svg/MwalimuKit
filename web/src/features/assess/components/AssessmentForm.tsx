import { useMemo } from 'react';
import { Search, CloudOff, Plus, Trash2 } from 'lucide-react';
import type { UseFormRegister } from 'react-hook-form';
import type { AssessmentItem } from '@mwalimukit/types';
import type { FormData } from '@/features/assess/hooks';
import { MermaidChart } from '@/components/MermaidChart';
import { SimpleChart } from '@/components/SimpleChart';

type FormValues = FormData;

export function StrandSelector({
  curriculum,
  selectedLA,
  selectedStrand,
  strandSearch,
  setStrandSearch,
  register,
}: {
  curriculum: { learning_areas: Array<{ code: string; name: string; level: string }>; strands: Array<{ code: string; name: string; learning_area_code: string }>; sub_strands: Array<{ code: string; name: string; strand_code: string }> } | undefined;
  selectedLA: string;
  selectedStrand: string;
  strandSearch: string;
  setStrandSearch: (v: string) => void;
  register: UseFormRegister<FormValues>;
}) {
  const filteredStrands = useMemo(() => {
    if (!curriculum) return [];
    return curriculum.strands.filter((s) => {
      if (s.learning_area_code !== selectedLA) return false;
      if (!strandSearch) return true;
      const q = strandSearch.toLowerCase();
      return s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q);
    });
  }, [curriculum, selectedLA, strandSearch]);

  const filteredSubStrands = useMemo(() => {
    if (!curriculum) return [];
    return curriculum.sub_strands.filter((s) => s.strand_code === selectedStrand);
  }, [curriculum, selectedStrand]);

  return (
    <>
      <div>
        <label className="label">Learning area</label>
        <select {...register('learning_area_code')} className="input">
          <option value="">Select area...</option>
          {curriculum?.learning_areas.map((la) => (
            <option key={la.code} value={la.code}>{la.name} ({la.level})</option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Strand</label>
        <div className="relative mb-1.5">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            className="input pl-10"
            placeholder="Search strands by name or code..."
            value={strandSearch}
            onChange={(e) => setStrandSearch(e.target.value)}
            disabled={!selectedLA}
          />
        </div>
        <select {...register('strand_code')} className="input" disabled={!selectedLA}>
          <option value="">Select strand...</option>
          {filteredStrands.map((s) => (
            <option key={s.code} value={s.code}>{s.code} — {s.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Sub-strand</label>
        <select {...register('sub_strand_code')} className="input" disabled={!selectedStrand}>
          <option value="">Select sub-strand...</option>
          {filteredSubStrands.map((ss) => (
            <option key={ss.code} value={ss.code}>{ss.code} — {ss.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Grade level</label>
        <input {...register('grade_level')} className="input" placeholder="Grade 1" />
      </div>
    </>
  );
}

export function AssessmentItemListEditor({
  items,
  onItemsChange,
}: {
  items: AssessmentItem[];
  onItemsChange: (items: AssessmentItem[]) => void;
}) {
  const addItem = () => {
    onItemsChange([...items, {
      id: `itm_${String(items.length + 1).padStart(2, '0')}`,
      criterion: 'accuracy',
      stem: '',
      answer_guide: '',
      max_level: 4,
      diagram_description: '',
    }]);
  };

  const removeItem = (idx: number) => {
    onItemsChange(items.filter((_, i) => i !== idx));
  };

  const updateItem = (idx: number, field: keyof AssessmentItem, value: string) => {
    onItemsChange(items.map((item, i) => (i === idx ? { ...item, [field]: value } : item)));
  };

  return (
    <>
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
          {item.diagram_type && item.diagram_type !== 'none' && item.diagram_data && (
            <div className="border border-blue-100 rounded-lg p-3 bg-blue-50/30">
              <p className="text-xs font-medium text-blue-700 mb-2">Diagram ({item.diagram_type})</p>
              {item.diagram_type === 'flowchart' && <MermaidChart code={item.diagram_data} />}
              {item.diagram_type === 'chart' && <SimpleChart data={item.diagram_data} />}
              {item.diagram_type === 'diagram' && (
                <p className="text-sm text-gray-600 italic">{item.diagram_data}</p>
              )}
              <textarea
                value={item.diagram_description ?? ''}
                onChange={(e) => updateItem(idx, 'diagram_description', e.target.value)}
                className="input mt-2"
                rows={1}
                placeholder="Diagram description (optional)"
              />
            </div>
          )}
          {(!item.diagram_type || item.diagram_type === 'none') && (
            <textarea
              value={item.diagram_description ?? ''}
              onChange={(e) => updateItem(idx, 'diagram_description', e.target.value)}
              className="input"
              rows={1}
              placeholder="Diagram / chart / picture description (optional)"
            />
          )}
        </div>
      ))}

      <button type="button" onClick={addItem} className="btn-secondary">
        <Plus className="h-4 w-4" /> Add item
      </button>

      {items.length === 0 && (
        <p className="text-sm text-gray-500 text-center py-4">Add assessment items to create your template</p>
      )}
    </>
  );
}

export function ModeToggle({ mode, aiEnabled, isOnline, register }: {
  mode: string;
  aiEnabled: boolean;
  isOnline: boolean;
  register: UseFormRegister<FormValues>;
}) {
  return (
    <div>
      <label className="label">Mode</label>
      {!isOnline && mode === 'ai' && (
        <div className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 mb-2 text-xs text-amber-800">
          <CloudOff className="h-3.5 w-3.5 shrink-0" />
          AI generation needs internet — switching to manual mode
        </div>
      )}
      <div className="flex gap-4">
        {aiEnabled && isOnline && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="radio" value="ai" {...register('mode')} className="accent-primary-500" />
            <span className="text-sm">AI draft</span>
          </label>
        )}
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="radio" value="manual" {...register('mode')} className="accent-primary-500" />
          <span className="text-sm">Structured template</span>
        </label>
      </div>
    </div>
  );
}
