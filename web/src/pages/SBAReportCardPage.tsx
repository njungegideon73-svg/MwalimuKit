import { useState } from 'react';
import { Download, Printer } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiFetch, getTokens } from '@/lib/api';
import toast from 'react-hot-toast';
import type { SchoolClass, Learner } from '@mwalimukit/types';

interface SubjectReport {
  subject_name: string;
  term: number;
  exam_type: string;
  marks: number | null;
  max_marks: number;
  percentage: number | null;
  grade: string | null;
}

interface ReportCard {
  learner_id: string;
  learner_name: string;
  admission_no: string | null;
  class_name: string;
  class_id: string;
  academic_year: string;
  subjects: SubjectReport[];
  term_averages: Record<string, number>;
  overall_average: number;
}

const EXAM_TYPE_LABELS: Record<string, string> = { opener: 'Opener', midterm: 'Midterm', endterm: 'End Term' };
const TERM_LABELS: Record<string, string> = { '1': 'Term 1', '2': 'Term 2', '3': 'Term 3' };

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800',
  B: 'bg-blue-100 text-blue-800',
  C: 'bg-amber-100 text-amber-800',
  D: 'bg-orange-100 text-orange-800',
  E: 'bg-red-100 text-red-800',
  F: 'bg-red-100 text-red-800',
};

export function SBAReportCardPage() {
  const currentYear = new Date().getFullYear().toString();
  const [selectedClassId, setSelectedClassId] = useState('');
  const [selectedLearnerId, setSelectedLearnerId] = useState('');
  const [academicYear, setAcademicYear] = useState(currentYear);
  const [schoolClosedDate, setSchoolClosedDate] = useState('');
  const [nextTermBeginsDate, setNextTermBeginsDate] = useState('');
  const [classTeacherRemarks, setClassTeacherRemarks] = useState('');
  const [principalRemarks, setPrincipalRemarks] = useState('');
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isGeneratingPreview, setIsGeneratingPreview] = useState(false);

  const { data: classes = [] } = useQuery<SchoolClass[]>({
    queryKey: ['classes'],
    queryFn: () => apiFetch('/classes'),
  });

  const { data: learners = [] } = useQuery<Learner[]>({
    queryKey: ['learners', selectedClassId],
    queryFn: () => apiFetch(`/classes/${selectedClassId}/learners`),
    enabled: !!selectedClassId,
  });

  const { data: report, isLoading } = useQuery<ReportCard>({
    queryKey: ['sba-report-card', selectedLearnerId, academicYear],
    queryFn: () => apiFetch(`/term-exams/report-card/learner/${selectedLearnerId}?academic_year=${academicYear}`),
    enabled: !!selectedLearnerId && !!academicYear,
  });

  const handleDownloadPDF = async () => {
    if (!report) return;
    try {
      const tokens = await getTokens();
      const params = new URLSearchParams({
        academic_year: academicYear,
        format: 'pdf',
        ...(schoolClosedDate && { school_closed_date: schoolClosedDate }),
        ...(nextTermBeginsDate && { next_term_begins_date: nextTermBeginsDate }),
        ...(classTeacherRemarks && { class_teacher_remarks: classTeacherRemarks }),
        ...(principalRemarks && { principal_remarks: principalRemarks }),
      });
      const resp = await fetch(
        `/api/v1/reports/report-card/${report.learner_id}?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${tokens?.access}` },
        }
      );
      if (!resp.ok) throw new Error('Failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_card_${report.learner_name.replace(/\s+/g, '_')}_${academicYear}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('PDF downloaded');
    } catch {
      toast.error('Failed to download PDF. The endpoint may not exist yet.');
    }
  };

  const handlePreview = async () => {
    if (!report) return;
    setIsGeneratingPreview(true);
    try {
      const tokens = await getTokens();
      const params = new URLSearchParams({
        academic_year: academicYear,
        format: 'pdf',
        ...(schoolClosedDate && { school_closed_date: schoolClosedDate }),
        ...(nextTermBeginsDate && { next_term_begins_date: nextTermBeginsDate }),
        ...(classTeacherRemarks && { class_teacher_remarks: classTeacherRemarks }),
        ...(principalRemarks && { principal_remarks: principalRemarks }),
      });
      const resp = await fetch(
        `/api/v1/reports/report-card/${report.learner_id}?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${tokens?.access}` },
        }
      );
      if (!resp.ok) throw new Error('Failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      setPreviewUrl(url);
    } catch {
      toast.error('Failed to generate preview');
    } finally {
      setIsGeneratingPreview(false);
    }
  };

  const handlePrint = () => window.print();

  // Group subjects by term and exam type
  const groupedByTerm: Record<string, Record<string, SubjectReport[]>> = {};
  if (report) {
    for (const sub of report.subjects) {
      const termKey = String(sub.term);
      if (!groupedByTerm[termKey]) groupedByTerm[termKey] = {};
      if (!groupedByTerm[termKey][sub.exam_type]) groupedByTerm[termKey][sub.exam_type] = [];
      groupedByTerm[termKey][sub.exam_type].push(sub);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="no-print">
        <h1 className="text-2xl font-bold text-gray-900">SBA Report Card</h1>
        <p className="text-gray-500 mt-1">Comprehensive learner performance report</p>
      </div>

      {/* Selection */}
      <div className="no-print card">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="label">Class</label>
            <select className="input" value={selectedClassId} onChange={(e) => { setSelectedClassId(e.target.value); setSelectedLearnerId(''); }}>
              <option value="">Select class...</option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Learner</label>
            <select className="input" value={selectedLearnerId} onChange={(e) => setSelectedLearnerId(e.target.value)}>
              <option value="">Select learner...</option>
              {learners.map((l) => (
                <option key={l.id} value={l.id}>{l.full_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Academic Year</label>
            <input className="input" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} />
          </div>
        </div>
      </div>

      {/* Report Card Options */}
      {report && (
        <div className="no-print card">
          <h2 className="font-semibold text-gray-900 mb-4">Report Card Options</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">School Closed On</label>
              <input type="date" className="input" value={schoolClosedDate} onChange={(e) => setSchoolClosedDate(e.target.value)} />
            </div>
            <div>
              <label className="label">Next Term Begins On</label>
              <input type="date" className="input" value={nextTermBeginsDate} onChange={(e) => setNextTermBeginsDate(e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Class Teacher Remarks</label>
              <textarea className="input" rows={2} value={classTeacherRemarks} onChange={(e) => setClassTeacherRemarks(e.target.value)} placeholder="Enter class teacher remarks..." />
            </div>
            <div className="sm:col-span-2">
              <label className="label">Principal Remarks</label>
              <textarea className="input" rows={2} value={principalRemarks} onChange={(e) => setPrincipalRemarks(e.target.value)} placeholder="Enter principal remarks..." />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button type="button" onClick={handlePreview} disabled={isGeneratingPreview} className="btn-secondary text-sm">
              {isGeneratingPreview ? 'Generating...' : 'Preview Report Card'}
            </button>
            <button type="button" onClick={handleDownloadPDF} className="btn-primary text-sm">
              <Download className="h-4 w-4" /> Download PDF
            </button>
            <button type="button" onClick={handlePrint} className="btn-secondary text-sm">
              <Printer className="h-4 w-4" /> Print
            </button>
          </div>
        </div>
      )}

      {/* Preview */}
      {previewUrl && (
        <div className="no-print card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-900">Preview</h2>
            <button type="button" onClick={() => { URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }} className="text-sm text-gray-500 hover:text-gray-700">
              Close Preview
            </button>
          </div>
          <div className="border border-gray-200 rounded-lg overflow-hidden bg-gray-100">
            <iframe src={previewUrl} title="Report Card Preview" className="w-full h-[600px]" />
          </div>
        </div>
      )}

      {isLoading && selectedLearnerId && (
        <div className="space-y-4 animate-pulse">
          <div className="h-64 bg-gray-200 rounded-xl" />
        </div>
      )}

      {report && (
        <>
          {/* Report Card */}
          <div className="bg-white border border-gray-200 rounded-xl p-8 print:shadow-none">
            {/* Header */}
            <div className="text-center border-b border-gray-200 pb-6 mb-6">
              <h2 className="text-xl font-bold text-gray-900">School Based Assessment Report Card</h2>
              <p className="text-gray-500 mt-1">Academic Year {report.academic_year}</p>
            </div>

            {/* Student Info */}
            <div className="grid grid-cols-2 gap-4 mb-6 text-sm">
              <div>
                <span className="text-gray-500">Name:</span>
                <span className="ml-2 font-medium">{report.learner_name}</span>
              </div>
              <div>
                <span className="text-gray-500">Class:</span>
                <span className="ml-2 font-medium">{report.class_name}</span>
              </div>
              {report.admission_no && (
                <div>
                  <span className="text-gray-500">Admission No:</span>
                  <span className="ml-2 font-medium">{report.admission_no}</span>
                </div>
              )}
              <div>
                <span className="text-gray-500">Overall Average:</span>
                <span className="ml-2 font-bold text-primary-600">{report.overall_average}%</span>
              </div>
            </div>

            {/* Term Results */}
            {Object.entries(groupedByTerm).map(([termKey, examTypes]) => (
              <div key={termKey} className="mb-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-900">{TERM_LABELS[termKey] || `Term ${termKey}`}</h3>
                  {report.term_averages[termKey] !== undefined && (
                    <span className="text-sm font-medium text-gray-600">
                      Average: <span className="text-primary-600">{report.term_averages[termKey]}%</span>
                    </span>
                  )}
                </div>
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="text-left py-2 px-3 font-medium">Subject</th>
                      <th className="text-center py-2 px-3 font-medium">Exam Type</th>
                      <th className="text-center py-2 px-3 font-medium">Marks</th>
                      <th className="text-center py-2 px-3 font-medium">%</th>
                      <th className="text-center py-2 px-3 font-medium">Grade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(examTypes).map(([examType, subjects]) =>
                      subjects.map((sub, idx) => (
                        <tr key={`${examType}-${idx}`} className="border-b border-gray-100">
                          {idx === 0 && (
                            <td className="py-2 px-3 font-medium" rowSpan={Object.values(examTypes).length || 1}>
                              {sub.subject_name}
                            </td>
                          )}
                          <td className="py-2 px-3 text-center text-gray-600">
                            {EXAM_TYPE_LABELS[examType] || examType}
                          </td>
                          <td className="py-2 px-3 text-center">
                            {sub.marks !== null ? `${sub.marks}/${sub.max_marks}` : '-'}
                          </td>
                          <td className="py-2 px-3 text-center">
                            {sub.percentage !== null ? `${sub.percentage}%` : '-'}
                          </td>
                          <td className="py-2 px-3 text-center">
                            {sub.grade && (
                              <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${GRADE_COLORS[sub.grade] || 'bg-gray-100 text-gray-800'}`}>
                                {sub.grade}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </>
      )}

      {!selectedLearnerId && !isLoading && (
        <div className="card text-center py-12">
          <p className="text-gray-500">Select a learner to view their report card</p>
        </div>
      )}
    </div>
  );
}
