import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Cloud, CloudOff } from 'lucide-react';
import { apiFetch } from '@/lib/api';
import { db } from '@/lib/db';
import type { Learner, Assessment, AssessmentRun, Score } from '@mwalimukit/types';

type SyncStatus = 'synced' | 'pending' | 'syncing';

async function hapticTap() {
  try {
    const { Haptics, ImpactStyle } = await import('@capacitor/haptics');
    await Haptics.impact({ style: ImpactStyle.Light });
  } catch {
    // Not in Capacitor — silent no-op
  }
}

export function ScoreEntryPage() {
  const { classId, assessmentId } = useParams<{ classId: string; assessmentId: string }>();
  const navigate = useNavigate();
  const [learners, setLearners] = useState<Learner[]>([]);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [run, setRun] = useState<AssessmentRun | null>(null);
  const [scores, setScores] = useState<Record<string, Record<string, number | null>>>({});
  const [syncStatus, setSyncStatus] = useState<SyncStatus>('synced');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [loading, setLoading] = useState(true);

  // Listen for online/offline
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load data
  useEffect(() => {
    if (!classId || !assessmentId) return;
    Promise.all([
      apiFetch<Learner[]>(`/learners/by-class/${classId}`).catch(() => []),
      apiFetch<Assessment>(`/assessments/${assessmentId}`).catch(() => null),
    ]).then(([l, a]) => {
      setLearners(l);
      setAssessment(a);
      setLoading(false);
    });
  }, [classId, assessmentId]);

  // Create run when learners and assessment are loaded
  useEffect(() => {
    if (!assessment || learners.length === 0 || run) return;

    const initRun = async () => {
      try {
        const r = await apiFetch<AssessmentRun>('/runs', {
          method: 'POST',
          json: { class_id: classId, assessment_id: assessmentId },
        });
        setRun(r);
        await loadScores(r.id);
      } catch {
        // Try to create offline run
        const offlineRun: AssessmentRun = {
          id: crypto.randomUUID(),
          school_id: '',
          class_id: classId!,
          assessment_id: assessmentId!,
          term: null,
          started_at: new Date().toISOString(),
          closed_at: null,
        };
        setRun(offlineRun);
        await db.runs.add({ ...offlineRun, _dirty: true, _synced_at: null });
      }
    };

    initRun();
  }, [assessment, learners, classId, assessmentId, run]);

  const loadScores = async (runId: string) => {
    try {
      // Load from IndexedDB first
      const localScores = await db.scores.where('run_id').equals(runId).toArray();
      if (localScores.length > 0) {
        const scoreMap: Record<string, Record<string, number | null>> = {};
        for (const s of localScores) {
          if (!scoreMap[s.learner_id]) scoreMap[s.learner_id] = {};
          scoreMap[s.learner_id][s.item_id] = s.level;
        }
        setScores(scoreMap);
      }
    } catch {
      // ignore
    }
  };

  const handleScoreChange = useCallback(
    async (learnerId: string, itemId: string, level: number | null) => {
      if (!run) return;

      // Update local state immediately
      setScores((prev) => ({
        ...prev,
        [learnerId]: { ...(prev[learnerId] ?? {}), [itemId]: level },
      }));

      // Write to IndexedDB
      const scoreId = `${run.id}_${learnerId}_${itemId}`;
      const scoreData: Score & { _dirty: boolean; _synced_at: string | null } = {
        id: scoreId,
        run_id: run.id,
        learner_id: learnerId,
        item_id: itemId,
        level: level as 1 | 2 | 3 | 4 | null,
        note: null,
        updated_at: new Date().toISOString(),
        _dirty: true,
        _synced_at: null,
      };

      await db.scores.put(scoreData);
      setSyncStatus('pending');

      // Try to sync immediately if online
      if (isOnline) {
        syncScores();
      }
    },
    [run, isOnline],
  );

  const syncScores = useCallback(async () => {
    if (!run || syncStatus === 'syncing') return;

    setSyncStatus('syncing');
    try {
      const dirtyScores = await db.scores
        .where('_dirty')
        .equals(1)
        .toArray();

      if (dirtyScores.length === 0) {
        setSyncStatus('synced');
        return;
      }

      const batch = dirtyScores.map((s) => ({
        id: s.id,
        run_id: s.run_id,
        learner_id: s.learner_id,
        item_id: s.item_id,
        level: s.level,
        note: s.note,
        updated_at: s.updated_at,
      }));

      await apiFetch('/scores/batch', {
        method: 'POST',
        json: { scores: batch },
      });

      // Mark as synced in IndexedDB
      for (const s of dirtyScores) {
        await db.scores.update(s.id, { _dirty: false, _synced_at: new Date().toISOString() });
      }
      setSyncStatus('synced');
    } catch {
      setSyncStatus('pending');
    }
  }, [run, syncStatus]);

  // Auto-sync when coming back online
  useEffect(() => {
    if (isOnline && syncStatus === 'pending') {
      syncScores();
    }
  }, [isOnline, syncStatus, syncScores]);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="h-64 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  if (!assessment || !run) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Could not load assessment data</p>
      </div>
    );
  }

  const items = assessment.items;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="btn-ghost text-sm">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-sm">
            {isOnline ? (
              <Cloud className="h-4 w-4 text-green-500" />
            ) : (
              <CloudOff className="h-4 w-4 text-amber-500" />
            )}
            <span
              className={
                syncStatus === 'synced'
                  ? 'text-green-600'
                  : syncStatus === 'syncing'
                    ? 'text-blue-600'
                    : 'text-amber-600'
              }
            >
              {syncStatus === 'synced'
                ? 'Saved'
                : syncStatus === 'syncing'
                  ? 'Syncing...'
                  : 'Saved offline'}
            </span>
          </div>
          {syncStatus === 'pending' && (
            <button onClick={syncScores} className="btn-ghost text-sm p-2">
              <RefreshCw className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div>
        <h1 className="text-lg font-bold text-gray-900">{assessment.name}</h1>
        <p className="text-sm text-gray-500">
          {learners.length} learners × {items.length} items
        </p>
      </div>

      {/* Score grid */}
      <div className="overflow-x-auto -mx-4 sm:mx-0">
        <table className="w-full text-sm border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="sticky left-0 bg-gray-50 text-left py-3 px-4 font-medium text-gray-700 min-w-[160px] z-10">
                Learner
              </th>
              {items.map((item, idx) => (
                <th key={item.id} className="py-3 px-3 text-center font-medium text-gray-700">
                  <div className="text-xs">Item {idx + 1}</div>
                  <div className="flex justify-center gap-1 mt-1">
                    {[1, 2, 3, 4].map((l) => (
                      <span key={l} className="text-[10px] text-gray-400">L{l}</span>
                    ))}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {learners.map((learner) => (
              <tr key={learner.id} className="border-b border-gray-100 hover:bg-gray-50/50">
                <td className="sticky left-0 bg-white hover:bg-gray-50/50 py-2.5 px-4 font-medium text-gray-900 z-10">
                  {learner.full_name}
                </td>
                {items.map((item) => (
                  <td key={item.id} className="py-2.5 px-3 text-center">
                    <div className="flex justify-center gap-1">
                      {[1, 2, 3, 4].map((level) => {
                        const current = scores[learner.id]?.[item.id];
                        const isActive = current === level;
                        return (
                          <button
                            key={level}
                            onClick={() => {
                              hapticTap();
                              handleScoreChange(
                                learner.id,
                                item.id,
                                isActive ? null : level,
                              );
                            }}
                            className={`h-7 w-7 rounded text-xs font-medium transition-all ${
                              isActive
                                ? level === 1
                                  ? 'bg-red-100 text-red-700 ring-2 ring-red-300'
                                  : level === 2
                                    ? 'bg-amber-100 text-amber-700 ring-2 ring-amber-300'
                                    : level === 3
                                      ? 'bg-green-100 text-green-700 ring-2 ring-green-300'
                                      : 'bg-blue-100 text-blue-700 ring-2 ring-blue-300'
                                : 'bg-gray-50 text-gray-400 hover:bg-gray-100'
                            }`}
                          >
                            {level}
                          </button>
                        );
                      })}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
