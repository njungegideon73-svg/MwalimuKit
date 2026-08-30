import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Save } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';
import { computeGradeFromMarks, getGradeColor, getGradeLabel } from '@/lib/grades';

interface ExamScore {
  id: string;
  learner_id: string;
  learner_name: string;
  admission_no: string | null;
  marks: number;
  grade: string | null;
  comment: string | null;
}

interface TermExamDetail {
  id: string;
  class_id: string;
  class_name: string;
  learning_area_id: string;
  learning_area_name: string;
  term: number;
  exam_type: string;
  academic_year: string;
  max_marks: number;
}

export function SBAMarksEntryPage() {
  const { examId } = useParams<{ examId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [scores, setScores] = useState<Record<string, number>>({});
  const [comments, setComments] = useState<Record<string, string>>({});

  const { data: exam, isLoading: loadingExam } = useQuery<TermExamDetail>({
    queryKey: ['term-exam', examId],
    queryFn: () => apiFetch(`/term-exams/${examId}`),
    enabled: !!examId,
  });

  const { data: existingScores = [], isLoading: loadingScores } = useQuery<ExamScore[]>({
    queryKey: ['term-exam-scores', examId],
    queryFn: () => apiFetch(`/term-exams/${examId}/scores`),
    enabled: !!examId,
  });

  // Initialize scores from existing data
  useEffect(() => {
    if (existingScores.length > 0) {
      const initial: Record<string, number> = {};
      const initialComments: Record<string, string> = {};
      for (const s of existingScores) {
        initial[s.learner_id] = s.marks;
        if (s.comment) initialComments[s.learner_id] = s.comment;
      }
      setScores(initial);
      setComments(initialComments);
    }
  }, [existingScores]);

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = existingScores.map((s) => ({
        learner_id: s.learner_id,
        marks: scores[s.learner_id] ?? 0,
        comment: comments[s.learner_id] || null,
      }));
      return apiFetch(`/term-exams/${examId}/scores`, {
        method: 'POST',
        json: { scores: payload },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['term-exam-scores', examId] });
      toast.success('Marks saved successfully');
    },
    onError: () => toast.error('Failed to save marks'),
  });

  const loading = loadingExam || loadingScores;

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse max-w-4xl mx-auto">
        <div className="h-8 w-32 bg-gray-200 rounded" />
        <div className="h-48 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Exam not found</p>
      </div>
    );
  }

  const maxMarks = exam.max_marks;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="btn-ghost text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">Enter Marks</h1>
        <p className="text-gray-500 mt-1">
          {exam.learning_area_name} — {exam.class_name} — Term {exam.term} ({exam.exam_type}) {exam.academic_year}
        </p>
        <p className="text-sm text-gray-400 mt-1">Maximum marks: {maxMarks}</p>
      </div>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="btn-primary"
        >
          {saveMutation.isPending ? (
            'Saving...'
          ) : (
            <>
              <Save className="h-4 w-4" /> Save All Marks
            </>
          )}
        </button>
        <span className="text-sm text-gray-400">
          {Object.keys(scores).filter((k) => scores[k] > 0).length} / {existingScores.length} learners scored
        </span>
      </div>

      {/* Marks entry table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 font-medium text-gray-700 min-w-[200px]">Learner</th>
              <th className="text-center py-3 px-4 font-medium text-gray-700 w-32">Marks (/{maxMarks})</th>
              <th className="text-center py-3 px-4 font-medium text-gray-700 w-24">%</th>
              <th className="text-center py-3 px-4 font-medium text-gray-700 w-20">Grade</th>
              <th className="text-left py-3 px-4 font-medium text-gray-700 min-w-[200px]">Comment</th>
            </tr>
          </thead>
          <tbody>
            {existingScores.map((s) => {
              const marks = scores[s.learner_id] ?? 0;
              const pct = maxMarks > 0 ? Math.round((marks / maxMarks) * 100) : 0;
              // CBC/CBE grading bands (per KNEC guidelines):
              // EE (Exceeding Expectations): 75–100%
              // ME (Meeting Expectations):   41–74%
              // AE (Approaching Expectations): 21–40%
              // BE (Below Expectations):     0–20%
              const grade = computeGradeFromMarks(marks, maxMarks);
              const gradeLabel = getGradeLabel(grade);
              const gradeColor = getGradeColor(grade);

              return (
                <tr key={s.learner_id} className="border-b border-gray-100 hover:bg-gray-50/50">
                  <td className="py-3 px-4">
                    <p className="font-medium text-gray-900">{s.learner_name}</p>
                    {s.admission_no && <p className="text-xs text-gray-500">Adm: {s.admission_no}</p>}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <input
                      type="number"
                      min={0}
                      max={maxMarks}
                      value={marks}
                      onChange={(e) => {
                        const val = Math.min(maxMarks, Math.max(0, Number(e.target.value)));
                        setScores((prev) => ({ ...prev, [s.learner_id]: val }));
                      }}
                      className="input w-20 text-center mx-auto"
                    />
                  </td>
                  <td className="py-3 px-4 text-center text-gray-600">{pct}%</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`font-semibold ${gradeColor}`} title={gradeLabel}>
                      {grade}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <input
                      type="text"
                      value={comments[s.learner_id] || ''}
                      onChange={(e) => setComments((prev) => ({ ...prev, [s.learner_id]: e.target.value }))}
                      className="input text-sm"
                      placeholder="Optional comment..."
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Bottom save */}
      <div className="flex justify-end">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
          className="btn-primary"
        >
          {saveMutation.isPending ? 'Saving...' : <><Save className="h-4 w-4" /> Save All Marks</>}
        </button>
      </div>
    </div>
  );
}
