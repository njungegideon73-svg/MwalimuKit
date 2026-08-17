import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, ClipboardCheck, BarChart3, FileText, Trash2, ChevronRight } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';
import type { SchoolClass, LearningArea } from '@mwalimukit/types';

interface TermExam {
  id: string;
  class_id: string;
  class_name: string;
  learning_area_id: string;
  learning_area_name: string;
  term: number;
  exam_type: string;
  academic_year: string;
  max_marks: number;
  created_at: string;
}

const EXAM_TYPES = [
  { value: 'opener', label: 'Opener' },
  { value: 'midterm', label: 'Midterm' },
  { value: 'endterm', label: 'End Term' },
];

const TERMS = [
  { value: 1, label: 'Term 1' },
  { value: 2, label: 'Term 2' },
  { value: 3, label: 'Term 3' },
];

export function SBADashboardPage() {
  const queryClient = useQueryClient();
  const currentYear = new Date().getFullYear().toString();

  const [showCreate, setShowCreate] = useState(false);
  const [selectedClass, setSelectedClass] = useState('');
  const [selectedLA, setSelectedLA] = useState('');
  const [selectedTerm, setSelectedTerm] = useState<number>(1);
  const [selectedExamType, setSelectedExamType] = useState('opener');
  const [academicYear, setAcademicYear] = useState(currentYear);
  const [filterClass, setFilterClass] = useState('');
  const [filterTerm, setFilterTerm] = useState<number | ''>('');
  const [filterYear, setFilterYear] = useState(currentYear);

  const { data: classes = [] } = useQuery<SchoolClass[]>({
    queryKey: ['classes'],
    queryFn: () => apiFetch('/classes'),
  });

  const { data: learningAreas = [] } = useQuery<LearningArea[]>({
    queryKey: ['learning-areas'],
    queryFn: () => apiFetch('/curriculum/learning-areas'),
  });

  const { data: exams = [], isLoading } = useQuery<TermExam[]>({
    queryKey: ['term-exams', filterClass, filterTerm, filterYear],
    queryFn: () => {
      const params = new URLSearchParams();
      if (filterClass) params.set('class_id', filterClass);
      if (filterTerm !== '') params.set('term', String(filterTerm));
      if (filterYear) params.set('academic_year', filterYear);
      return apiFetch(`/term-exams?${params.toString()}`);
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch('/term-exams', {
        method: 'POST',
        json: {
          class_id: selectedClass,
          learning_area_id: selectedLA,
          term: selectedTerm,
          exam_type: selectedExamType,
          academic_year: academicYear,
          max_marks: 100,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['term-exams'] });
      setShowCreate(false);
      setSelectedClass('');
      setSelectedLA('');
      toast.success('Term exam created');
    },
    onError: () => toast.error('Failed to create term exam'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiFetch(`/term-exams/${id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['term-exams'] });
      toast.success('Exam deleted');
    },
    onError: () => toast.error('Failed to delete exam'),
  });

  const examTypeLabel = (t: string) => EXAM_TYPES.find((e) => e.value === t)?.label || t;
  const termLabel = (t: number) => TERMS.find((e) => e.value === t)?.label || `Term ${t}`;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">School Based Assessments</h1>
          <p className="text-gray-500 mt-1">Manage term exams and enter learner marks</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary">
          <Plus className="h-4 w-4" /> {showCreate ? 'Cancel' : 'New Exam'}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="card border-primary-200 bg-primary-50/30">
          <h2 className="font-semibold text-gray-900 mb-4">Create Term Exam</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Class</label>
              <select className="input" value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)}>
                <option value="">Select class...</option>
                {classes.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Subject (Learning Area)</label>
              <select className="input" value={selectedLA} onChange={(e) => setSelectedLA(e.target.value)}>
                <option value="">Select subject...</option>
                {learningAreas.map((la) => (
                  <option key={la.code} value={la.code}>{la.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Term</label>
              <select className="input" value={selectedTerm} onChange={(e) => setSelectedTerm(Number(e.target.value))}>
                {TERMS.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Exam Type</label>
              <select className="input" value={selectedExamType} onChange={(e) => setSelectedExamType(e.target.value)}>
                {EXAM_TYPES.map((et) => (
                  <option key={et.value} value={et.value}>{et.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Academic Year</label>
              <input className="input" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
            </div>
          </div>
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending || !selectedClass || !selectedLA}
            className="btn-primary mt-4"
          >
            {createMutation.isPending ? 'Creating...' : 'Create Exam'}
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-3">
          <div>
            <label className="label text-xs">Filter by Class</label>
            <select className="input text-sm" value={filterClass} onChange={(e) => setFilterClass(e.target.value)}>
              <option value="">All classes</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label text-xs">Filter by Term</label>
            <select className="input text-sm" value={filterTerm} onChange={(e) => setFilterTerm(e.target.value === '' ? '' : Number(e.target.value))}>
              <option value="">All terms</option>
              {TERMS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label text-xs">Academic Year</label>
            <input className="input text-sm w-24" value={filterYear} onChange={(e) => setFilterYear(e.target.value)} />
          </div>
        </div>
      </div>

      {/* Exams list */}
      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(3)].map((_, i) => <div key={i} className="h-20 bg-gray-200 rounded-xl" />)}
        </div>
      ) : exams.length === 0 ? (
        <div className="card text-center py-12">
          <ClipboardCheck className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No term exams yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {exams.map((exam) => (
            <div key={exam.id} className="card flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-gray-900">{exam.learning_area_name}</span>
                  <span className="badge-primary text-xs">{exam.class_name}</span>
                  <span className="badge-gray text-xs">{termLabel(exam.term)}</span>
                  <span className="badge-accent text-xs">{examTypeLabel(exam.exam_type)}</span>
                  <span className="text-xs text-gray-400">{exam.academic_year}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link
                  to={`/sba/marks/${exam.id}`}
                  className="btn-secondary text-sm"
                >
                  Enter Marks <ChevronRight className="h-3 w-3" />
                </Link>
                <button
                  onClick={() => {
                    if (confirm('Delete this exam and all its scores?')) deleteMutation.mutate(exam.id);
                  }}
                  className="p-1.5 text-gray-400 hover:text-red-600 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link to="/sba/report-card" className="card group hover:border-primary-300 hover:shadow-md transition-all flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-green-500 flex items-center justify-center group-hover:bg-green-600 transition-colors">
            <FileText className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Learner Report Cards</p>
            <p className="text-sm text-gray-500">View comprehensive SBA report cards</p>
          </div>
        </Link>
        <Link to="/sba/analytics" className="card group hover:border-primary-300 hover:shadow-md transition-all flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-blue-500 flex items-center justify-center group-hover:bg-blue-600 transition-colors">
            <BarChart3 className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Performance Analytics</p>
            <p className="text-sm text-gray-500">Class performance breakdown and trends</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
