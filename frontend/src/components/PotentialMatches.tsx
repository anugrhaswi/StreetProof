import { useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Loader2, ShieldCheck } from 'lucide-react';
import { getAIHealth, getMatchingStatus, type AIHealthResponse, type PublicMatchingStatus } from '../services/api';

const POLL_INTERVAL_MS = 2000;
const MAX_POLLS = 30;

interface PotentialMatchesProps {
  reportId: string;
}

export default function PotentialMatches({ reportId }: PotentialMatchesProps) {
  const [job, setJob] = useState<PublicMatchingStatus | null>(null);
  const [aiHealth, setAiHealth] = useState<AIHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timedOut, setTimedOut] = useState(false);
  const pollCount = useRef(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const clearTimer = () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const poll = async () => {
      try {
        const [jobResult, healthResult] = await Promise.allSettled([
          getMatchingStatus(reportId),
          aiHealth ? Promise.resolve(aiHealth) : getAIHealth(),
        ]);
        if (cancelled) return;

        if (healthResult.status === 'fulfilled') setAiHealth(healthResult.value);

        if (jobResult.status === 'rejected') {
          throw jobResult.reason;
        }

        const nextJob = jobResult.value;
        setJob(nextJob);
        setError(null);
        setLoading(false);

        const status = nextJob?.status;
        const terminal = status === 'completed' || status === 'failed';
        if (terminal) {
          clearTimer();
          return;
        }

        pollCount.current += 1;
        if (pollCount.current >= MAX_POLLS) {
          setTimedOut(true);
          clearTimer();
          return;
        }

        clearTimer();
        timerRef.current = window.setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load matching status.');
        setLoading(false);
        clearTimer();
      }
    };

    setLoading(true);
    setError(null);
    setTimedOut(false);
    pollCount.current = 0;
    void poll();

    return () => {
      cancelled = true;
      clearTimer();
    };
    // aiHealth intentionally excluded to avoid poll restarts
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  return (
    <div className="bg-brand-900/60 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-semibold">Potential Matching Incidents</h2>
        {aiHealth && aiHealth.status !== 'ready' && (
          <span className={`text-xs px-2.5 py-1 rounded-full border ${
            aiHealth.status === 'disabled'
              ? 'border-blue-500/30 bg-blue-500/10 text-blue-300'
              : 'border-yellow-500/30 bg-yellow-500/10 text-yellow-300'
          }`}>
            {aiHealth.status === 'disabled'
              ? 'Lightweight matching'
              : aiHealth.status === 'failed'
                ? 'AI unavailable'
                : 'AI loading'}
          </span>
        )}
      </div>

      {loading && !job && (
        <div className="flex items-center gap-3 text-gray-300">
          <Loader2 size={18} className="animate-spin text-brand-400" />
          <span className="text-sm">Checking for potential duplicates...</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-300 bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {!error && job && (job.status === 'pending' || job.status === 'processing') && (
        <div className="flex items-center gap-3 text-gray-300">
          <Loader2 size={18} className="animate-spin text-brand-400" />
          <div>
            <p className="text-sm">
              {aiHealth?.status === 'disabled' ? 'Checking for potential duplicates...' : 'Analyzing similar incidents...'}
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              {job.status === 'pending' ? 'Queued for analysis' : 'Comparing against existing reports'}
            </p>
          </div>
        </div>
      )}

      {!error && job?.status === 'failed' && (
        <div className="flex items-start gap-2 text-yellow-200 bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-sm">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div>
            <p>Matching analysis could not be completed right now.</p>
            <p className="text-yellow-300/80 text-xs mt-1">{job.error_message || 'Please check back later.'}</p>
          </div>
        </div>
      )}

      {!error && timedOut && job && (job.status === 'pending' || job.status === 'processing') && (
        <div className="flex items-center gap-2 text-gray-400 text-sm">
          <Clock size={16} />
          <span>Matching is taking longer than expected. Check back later.</span>
        </div>
      )}

      {!error && job?.status === 'completed' && job.suggestion_count === 0 && (
        <div className="flex items-center gap-2 text-green-300 text-sm">
          <CheckCircle2 size={16} />
          <span>No potential matches found yet.</span>
        </div>
      )}

      {!error && job?.status === 'completed' && job.suggestion_count > 0 && (
        <div className="flex items-start gap-3 bg-brand-800/40 border border-brand-700/40 rounded-lg p-4">
          <ShieldCheck size={18} className="text-brand-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-gray-200">
              Potential matches found and awaiting moderator review.
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Matching details are reviewed by administrators before any incidents are merged.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
