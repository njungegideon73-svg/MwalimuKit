import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Plus, Upload, Play } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import toast from 'react-hot-toast';
import type { SchoolClass, Learner, Assessment } from '@mwalimukit/types';

export function ClassDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [cls, setCls] = useState<SchoolClass | null>(null);
  const [learners, setLearners] = useState<Learner[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddLearner, setShowAddLearner] = useState(false);
  const [showBulkAdd, setShowBulkAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newAdmNo, setNewAdmNo] = useState('');
  const [bulkText, setBulkText] = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([
      apiFetch<SchoolClass>(`/classes/${id}`).catch(() => null),
      apiFetch<Learner[]>(`/learners/by-class/${id}`).catch(() => []),
      apiFetch<Assessment[]>('/assessments').catch(() => []),
    ]).then(([c, l, a]) => {
      setCls(c);
      setLearners(l);
      setAssessments(a);
      setLoading(false);
    });
  }, [id]);

  const addLearner = async () => {
    if (!newName.trim() || !id) return;
    try {
      const result = await apiFetch<Learner>('/learners', {
        method: 'POST',
        json: { class_id: id, full_name: newName.trim(), admission_no: newAdmNo || null },
      });
      setLearners([...learners, result]);
      setNewName('');
      setNewAdmNo('');
      setShowAddLearner(false);
      toast.success('Learner added');
    } catch {
      toast.error('Failed to add learner');
    }
  };

  const bulkAdd = async () => {
    if (!bulkText.trim() || !id) return;
    const lines = bulkText.split('\n').filter((l) => l.trim());
    try {
      const result = await apiFetch<Learner[]>('/learners/bulk', {
        method: 'POST',
        json: { class_id: id, lines },
      });
      setLearners([...learners, ...result]);
      setBulkText('');
      setShowBulkAdd(false);
      toast.success(`${result.length} learners added`);
    } catch {
      toast.error('Failed to bulk add');
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse max-w-3xl mx-auto">
        <div className="h-8 w-32 bg-gray-200 rounded" />
        <div className="h-48 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  if (!cls) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Class not found</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <button onClick={() => navigate(-1)} className="btn-ghost text-sm">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">{cls.name}</h1>
        <p className="text-gray-500">{cls.grade_level} — {learners.length} learners</p>
      </div>

      {/* Learners */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">Learners ({learners.length})</h2>
          <div className="flex gap-2">
            <button onClick={() => setShowAddLearner(true)} className="btn-secondary text-sm">
              <Plus className="h-4 w-4" /> Add
            </button>
            <button onClick={() => setShowBulkAdd(true)} className="btn-secondary text-sm">
              <Upload className="h-4 w-4" /> Bulk add
            </button>
          </div>
        </div>

        {showAddLearner && (
          <div className="flex gap-2 mb-4">
            <input
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="input flex-1"
              placeholder="Full name"
            />
            <input
              value={newAdmNo}
              onChange={(e) => setNewAdmNo(e.target.value)}
              className="input w-32"
              placeholder="Adm. no"
            />
            <button onClick={addLearner} className="btn-primary text-sm">Add</button>
            <button onClick={() => setShowAddLearner(false)} className="btn-ghost text-sm">Cancel</button>
          </div>
        )}

        {showBulkAdd && (
          <div className="mb-4 space-y-2">
            <textarea
              value={bulkText}
              onChange={(e) => setBulkText(e.target.value)}
              className="input"
              rows={5}
              placeholder="One name per line, or: name,admission_no"
            />
            <div className="flex gap-2">
              <button onClick={bulkAdd} className="btn-primary text-sm">Add all</button>
              <button onClick={() => setShowBulkAdd(false)} className="btn-secondary text-sm">Cancel</button>
            </div>
          </div>
        )}

        {learners.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">No learners yet. Add some above.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {learners.map((l) => (
              <div key={l.id} className="flex items-center justify-between py-2.5">
                <div>
                  <p className="font-medium text-sm text-gray-900">{l.full_name}</p>
                  {l.admission_no && <p className="text-xs text-gray-500">Adm: {l.admission_no}</p>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Run assessment */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4">Run an assessment</h2>
        {assessments.length === 0 ? (
          <p className="text-sm text-gray-500">No assessments available. Create one first.</p>
        ) : (
          <div className="space-y-2">
            {assessments.map((a) => (
              <Link
                key={a.id}
                to={`/classes/${id}/scores/${a.id}`}
                className="flex items-center justify-between rounded-lg border border-gray-200 px-4 py-3 hover:border-primary-300 transition-colors"
              >
                <div>
                  <p className="font-medium text-sm text-gray-900">{a.name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="badge-primary text-xs">{a.learning_area_code}</span>
                    <span className="text-xs text-gray-400">{a.items.length} items</span>
                  </div>
                </div>
                <Play className="h-4 w-4 text-primary-500" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
