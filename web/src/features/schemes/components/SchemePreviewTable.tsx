import { useEffect, useRef } from 'react';
import type { SchemePreviewItem } from '@mwalimukit/types';

/**
 * Editable content-bank cell.  The teacher can click any cell and edit it
 * in place (Shift+Enter inserts a new line).  Changes are committed to the
 * backend debounced, so re-renders never clobber what the teacher typed.
 */
interface EditableCellProps {
  lines: string[] | string | null;
  onCommit: (lines: string[]) => void;
  placeholder?: string;
  className?: string;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderLines(value: string[] | string | null): string {
  if (Array.isArray(value)) {
    return value.map((l) => escapeHtml(l)).join('<br>');
  }
  if (value) {
    return escapeHtml(value).split('\n').join('<br>');
  }
  return '';
}

function toLines(innerText: string): string[] {
  const lines = innerText.split('\n');
  while (lines.length && lines[lines.length - 1].trim() === '') lines.pop();
  return lines;
}

function EditableCell({ lines, onCommit, placeholder, className }: EditableCellProps) {
  const ref = useRef<HTMLDivElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const committed = useRef<string | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (document.activeElement === el) return; // never clobber while typing
    const rendered = renderLines(lines);
    if (el.innerHTML !== rendered) el.innerHTML = rendered;
  }, [lines]);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const handleInput = () => {
    const el = ref.current;
    if (!el || committed.current === el.innerText) return;
    committed.current = el.innerText;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => onCommit(toLines(el.innerText)), 900);
  };

  const handleBlur = () => {
    const el = ref.current;
    if (!el) return;
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    onCommit(toLines(el.innerText));
  };

  return (
    <div
      ref={ref}
      contentEditable
      suppressContentEditableWarning
      onInput={handleInput}
      onBlur={handleBlur}
      suppressHydrationWarning
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          // Single Enter moves out of the cell; Shift+Enter adds a line.
          e.preventDefault();
          (e.currentTarget as HTMLDivElement).blur();
        }
      }}
      className={`min-h-[2.5rem] break-words rounded outline-none focus:bg-primary-50/30 focus:ring-2 focus:ring-primary-300 ${className ?? ''}`}
      data-placeholder={placeholder}
      dangerouslySetInnerHTML={{ __html: renderLines(lines) }}
    />
  );
}

type EditableField =
  | 'learning_outcomes'
  | 'key_inquiry_questions'
  | 'learning_experiences'
  | 'resources'
  | 'assessment_methods'
  | 'topic';

interface SchemePreviewTableProps {
  lessons: SchemePreviewItem[];
  onCommitCell: (week: number, lesson: number, field: EditableField, lines: string[]) => void;
  onCommitNotes: (week: number, lesson: number, note: string) => void;
}

const COLUMNS = [
  'Wk',
  'Lesson',
  'Strand',
  'Sub-Strand',
  'Specific Learning Outcomes',
  'Key Inquiry Question(s)',
  'Learning Experiences',
  'Learning Resources',
  'Assessment Methods',
  'Reflection',
];

export function SchemePreviewTable({ lessons, onCommitCell, onCommitNotes }: SchemePreviewTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full min-w-[1400px] border-collapse text-sm">
        <thead>
          <tr className="bg-gray-900 text-white">
            {COLUMNS.map((col, i) => (
              <th
                key={col}
                className={`px-2 py-2 text-left text-xs font-semibold ${
                  i === COLUMNS.length - 1 ? 'w-44' : ''
                }`}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {lessons.map((lesson, idx) => {
            if (lesson.is_break) {
              return (
                <tr key={idx} className="bg-amber-50">
                  <td className="border border-gray-200 px-2 py-2 text-center font-medium text-amber-800">
                    Wk {lesson.week_number}
                  </td>
                  <td className="border border-gray-200 px-2 py-2 text-amber-800">—</td>
                  <td
                    colSpan={8}
                    className="border border-gray-200 px-3 py-2 font-medium text-amber-800"
                  >
                    {lesson.break_label ?? 'School break'}
                  </td>
                </tr>
              );
            }
            return (
              <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="border border-gray-200 px-2 py-2 text-center font-medium">
                  {lesson.week_number}
                </td>
                <td className="border border-gray-200 px-2 py-2 text-center">{lesson.lesson_number}</td>
                <td className="border border-gray-200 px-2 py-2">{lesson.strand_code ?? '-'}</td>
                <td className="border border-gray-200 px-2 py-2">{lesson.sub_strand_code ?? '-'}</td>
                <td className="border border-gray-200 px-2 py-2">
                  <EditableCell
                    lines={lesson.learning_outcomes}
                    placeholder="Specific learning outcomes"
                    onCommit={(lines) =>
                      onCommitCell(lesson.week_number, lesson.lesson_number, 'learning_outcomes', lines)
                    }
                  />
                </td>
                <td className="border border-gray-200 px-2 py-2">
                  <EditableCell
                    lines={lesson.key_inquiry_questions}
                    placeholder="Key inquiry questions"
                    onCommit={(lines) =>
                      onCommitCell(lesson.week_number, lesson.lesson_number, 'key_inquiry_questions', lines)
                    }
                  />
                </td>
                <td className="border border-gray-200 px-2 py-2">
                  <EditableCell
                    lines={lesson.learning_experiences}
                    placeholder="Learning experiences"
                    onCommit={(lines) =>
                      onCommitCell(lesson.week_number, lesson.lesson_number, 'learning_experiences', lines)
                    }
                  />
                </td>
                <td className="border border-gray-200 px-2 py-2">
                  <EditableCell
                    lines={lesson.resources}
                    placeholder="Learning resources"
                    onCommit={(lines) =>
                      onCommitCell(lesson.week_number, lesson.lesson_number, 'resources', lines)
                    }
                  />
                </td>
                <td className="border border-gray-200 px-2 py-2">
                  <EditableCell
                    lines={lesson.assessment_methods}
                    placeholder="Assessment methods"
                    onCommit={(lines) =>
                      onCommitCell(lesson.week_number, lesson.lesson_number, 'assessment_methods', lines)
                    }
                  />
                </td>
                <td className="border border-gray-200 bg-white px-2 py-2">
                  <EditableCell
                    lines={lesson.notes}
                    placeholder="Teacher's notes"
                    onCommit={(lines) =>
                      onCommitNotes(lesson.week_number, lesson.lesson_number, lines.join('\n'))
                    }
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}