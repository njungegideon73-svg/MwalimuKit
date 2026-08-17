import { useState, useRef } from 'react';
import { GripVertical, Plus, Trash2, Palette } from 'lucide-react';
import type { Rubric, RubricLevel } from '@mwalimukit/types';

const LEVEL_COLORS = [
  { level: 1, bg: 'bg-red-100', ring: 'ring-red-400', text: 'text-red-700', hex: '#fca5a5' },
  { level: 2, bg: 'bg-amber-100', ring: 'ring-amber-400', text: 'text-amber-700', hex: '#fcd34d' },
  { level: 3, bg: 'bg-green-100', ring: 'ring-green-400', text: 'text-green-700', hex: '#86efac' },
  { level: 4, bg: 'bg-blue-100', ring: 'ring-blue-400', text: 'text-blue-700', hex: '#93c5fd' },
];

interface RubricEditorProps {
  value: Rubric;
  onChange: (rubric: Rubric) => void;
}

export function RubricEditor({ value, onChange }: RubricEditorProps) {
  const [dragIdx, setDragIdx] = useState<number | null>(null);
  const [editingColor, setEditingColor] = useState<number | null>(null);
  const dragOverIdx = useRef<number | null>(null);

  const updateLevel = (idx: number, field: keyof RubricLevel, val: string) => {
    const levels = value.levels.map((l, i) => (i === idx ? { ...l, [field]: val } : l));
    onChange({ ...value, levels });
  };

  const updateLevelColor = (idx: number, color: string) => {
    const levels = value.levels.map((l, i) => (i === idx ? { ...l, color } : l));
    onChange({ ...value, levels });
    setEditingColor(null);
  };

  const addCriterion = () => {
    const id = `crit_${Date.now()}`;
    onChange({
      ...value,
      criteria: [...value.criteria, { id, label: 'New criterion' }],
    });
  };

  const updateCriterion = (idx: number, label: string) => {
    const criteria = value.criteria.map((c, i) => (i === idx ? { ...c, label } : c));
    onChange({ ...value, criteria });
  };

  const removeCriterion = (idx: number) => {
    onChange({
      ...value,
      criteria: value.criteria.filter((_, i) => i !== idx),
    });
  };

  const handleDragStart = (idx: number) => {
    setDragIdx(idx);
  };

  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    dragOverIdx.current = idx;
  };

  const handleDrop = (idx: number) => {
    if (dragIdx === null || dragIdx === idx) {
      setDragIdx(null);
      return;
    }
    const criteria = [...value.criteria];
    const [moved] = criteria.splice(dragIdx, 1);
    criteria.splice(idx, 0, moved);
    onChange({ ...value, criteria });
    setDragIdx(null);
  };

  const handleDragEnd = () => {
    setDragIdx(null);
    dragOverIdx.current = null;
  };

  return (
    <div className="space-y-6">
      {/* Levels section */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Rubric Levels</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {value.levels.map((level, idx) => {
            const colorDef = LEVEL_COLORS.find((c) => c.level === level.level);
            return (
              <div
                key={level.level}
                className={`rounded-lg border p-3 ${colorDef?.bg ?? 'bg-gray-50'} relative`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${colorDef?.text ?? 'text-gray-600'}`}>
                    L{level.level}
                  </span>
                  <input
                    className="flex-1 text-sm font-medium bg-transparent border-b border-transparent hover:border-gray-300 focus:border-gray-500 outline-none"
                    value={level.label}
                    onChange={(e) => updateLevel(idx, 'label', e.target.value)}
                  />
                  <button
                    type="button"
                    className="p-1 rounded hover:bg-white/50"
                    onClick={() => setEditingColor(editingColor === idx ? null : idx)}
                    title="Pick colour"
                  >
                    <Palette className="h-3.5 w-3.5 text-gray-500" />
                  </button>
                </div>
                {editingColor === idx && (
                  <div className="flex gap-1.5 mb-2">
                    {LEVEL_COLORS.map((c) => (
                      <button
                        key={c.level}
                        type="button"
                        className={`w-6 h-6 rounded-full border-2 ${level.color === c.hex ? 'border-gray-800 scale-110' : 'border-transparent'}`}
                        style={{ backgroundColor: c.hex }}
                        onClick={() => updateLevelColor(idx, c.hex)}
                        title={`Level ${c.level} colour`}
                      />
                    ))}
                  </div>
                )}
                <textarea
                  className="w-full text-xs bg-transparent border rounded p-1.5 resize-none"
                  rows={2}
                  placeholder="Descriptor..."
                  value={level.descriptor}
                  onChange={(e) => updateLevel(idx, 'descriptor', e.target.value)}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Criteria section with drag-reorder */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-700">Criteria</h4>
          <button
            type="button"
            onClick={addCriterion}
            className="inline-flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800"
          >
            <Plus className="h-3.5 w-3.5" /> Add
          </button>
        </div>
        <div className="space-y-2">
          {value.criteria.map((criterion, idx) => (
            <div
              key={criterion.id}
              draggable
              onDragStart={() => handleDragStart(idx)}
              onDragOver={(e) => handleDragOver(e, idx)}
              onDrop={() => handleDrop(idx)}
              onDragEnd={handleDragEnd}
              className={`flex items-center gap-2 rounded-lg border bg-white px-3 py-2 transition-all ${
                dragIdx === idx ? 'opacity-50 ring-2 ring-emerald-300' : ''
              }`}
            >
              <GripVertical className="h-4 w-4 text-gray-300 cursor-grab shrink-0" />
              <input
                className="flex-1 text-sm bg-transparent outline-none"
                value={criterion.label}
                onChange={(e) => updateCriterion(idx, e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeCriterion(idx)}
                className="p-1 text-gray-400 hover:text-red-500"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
