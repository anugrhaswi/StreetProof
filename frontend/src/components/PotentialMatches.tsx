import { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Loader2, RefreshCw, Search } from 'lucide-react';
import { getAIHealth, getMatchingStatus, type MatchingJob, type MatchSuggestion } from '../services/api';

interface PotentialMatchesProps {
  reportId: string;
}

const POLL_INTERVAL_MS = 2000;

function similarityLabel(score: number): string {
  return `${(score * 100).toFixed(1)}% semantic similarity`;
}

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    open: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    closed: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    merged: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  };
  return (
    <span className={`px-2 py-0.5 text-xs rounded-full border capitalize ${styles[status] || 'text-gray-400 border-gray-600'}`}>
      {status}
    </span>
  );
}

function SuggestionCard({ suggestion }: { suggestion: MatchSuggestion }) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-sm font-semibold text-brand-300">{similarityLabel(suggestion.similarity_score)}</span>
        <span className="text-xs text-gray-500">(semantic similarity, not duplication probability)</span>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-2">
        {suggestion.incident_category && (
          <span className="px-2 py-0.5 text-xs rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 capitalize">
            {suggestion.incident_category}
          </span>
        )}
        {suggestion.incident_status && statusBadge(suggestion.incident_status)}
      </div>

      <h4 className="text-sm font-medium text-white mb-1">{suggestion.incident_title || 'Related incident'}</h4>
      {suggestion.matched_report_description && (
        <p className="text-sm text-gray-400 line-clamp-3">{suggestion.matched_report_description}</p>
      )}
      <div className="mt-2 text-xs text-gray-500">
        Incident ID: {suggestion.incident_id}
        {suggestion.incident_latitude != null && suggestion.incident_longitude != null && (
          <span className="ml-2">
            ({suggestion.incident_latitude.toFixed(4)}, {suggestion.incident_longitude.toFixed(4)})
          </span>
        )}
      </div>
    </div>
  );
}

export default function PotentialMatches({ reportId }: PotentialMatchesProps) {
  const [job, setJob] = useState<MatchingJob | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<string | null>(null);
  const [pollFailures, setPollFailures] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const intervalRef = useRef<number | null>(null);
  const MAX_POLL_FAILURES = 10;

  const fetchStatus = useCallback(async () => {
    try {
      const [jobData, ai] = await Promise.all([getMatchingStatus(reportId), getAIHealth().catch(() => null)]);
      if (jobData === null) {
        setPollFailures((c) => c + 1);
      } else {
        setPollFailures(0);
      }
      setJob(jobData);
      if (ai) setAiStatus(ai.status);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load matching status.');
      setPollFailures((c) => c + 1);
    } finally {
      setIsRetrying(false);
    }
  }, [reportId]);

  useEffect(() => {
    let active = true;

    const run = async () => {
      if (!active) return;
      await fetchStatus();
    };

    run();

    return () => {
      active = false;
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, [fetchStatus]);

  useEffect(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    const shouldPoll =
      job === undefined ||
      (job === null && pollFailures < MAX_POLL_FAILURES) ||
      job?.status === 'pending' ||
      job?.status === 'processing';
    if (!shouldPoll) return;

    intervalRef.current = window.setInterval(() => {
      fetchStatus();
    }, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [job?.status, pollFailures, fetchStatus]);

  const renderContent = () => {
    if (error) {
      return (
        <div className="flex items-start gap-2 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      );
    }

    if (job === undefined) {
      return (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Loader2 size={16} className="animate-spin" />
          Checking matching status...
        </div>
      );
    }

    if (job === null) {
      if (pollFailures >= MAX_POLL_FAILURES) {
        return (
          <div className="flex items-start gap-3 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <div className="flex-1">
              <div className="font-medium">Unable to retrieve matching status</div>
              <div className="text-red-200/80 mt-0.5 mb-3">
                The matching job could not be found. It may not have been created yet.
              </div>
              <button
                onClick={() => { setError(null); setPollFailures(0); setIsRetrying(true); fetchStatus(); }}
                disabled={isRetrying}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isRetrying ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                {isRetrying ? 'Retrying...' : 'Retry'}
              </button>
            </div>
          </div>
        );
      }
      return (
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Clock size={16} />
          Matching job not found yet. It will appear shortly after submission.
        </div>
      );
    }

    if (job.status === 'pending') {
      return (
        <div className="flex items-start gap-2 text-sm text-amber-300 bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
          <Clock size={16} className="mt-0.5 shrink-0" />
          <div>
            <div className="font-medium">Matching pending</div>
            <div className="text-amber-200/80 mt-0.5">
              This report is queued for semantic matching.
              {aiStatus && aiStatus !== 'ready' ? ` AI model status: ${aiStatus}.` : ''}
            </div>
          </div>
        </div>
      );
    }

    if (job.status === 'processing') {
      return (
        <div className="flex items-start gap-2 text-sm text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
          <Loader2 size={16} className="mt-0.5 shrink-0 animate-spin" />
          <div>
            <div className="font-medium">Matching in progress</div>
            <div className="text-blue-200/80 mt-0.5">Analyzing semantic similarity against existing incidents.</div>
          </div>
        </div>
      );
    }

    if (job.status === 'failed') {
      return (
        <div className="flex items-start gap-2 text-sm text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div>
            <div className="font-medium">Matching failed</div>
            <div className="text-red-200/80 mt-0.5">
              {job.error_message || 'The matching job failed. Please try again later.'}
            </div>
          </div>
        </div>
      );
    }

    // completed
    const suggestions = job.suggestions || [];
    if (suggestions.length === 0) {
      return (
        <div className="flex items-start gap-2 text-sm text-gray-300 bg-gray-800/40 border border-gray-700 rounded-lg p-3">
          <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-gray-400" />
          <div>
            <div className="font-medium">No potential matches found</div>
            <div className="text-gray-400 mt-0.5">No existing incidents exceeded the semantic similarity threshold.</div>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <div className="flex items-start gap-2 text-sm text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
          <Search size={16} className="mt-0.5 shrink-0" />
          <div>
            <div className="font-medium">Potential matches found</div>
            <div className="text-emerald-200/80 mt-0.5">
              Review suggestions below. Scores show semantic similarity, not duplication probability.
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {suggestions.map((s) => (
            <SuggestionCard key={s.id} suggestion={s} />
          ))}
        </div>
      </div>
    );
  };

  return (
    <section className="mt-10 border-t border-gray-800 pt-8">
      <div className="flex items-center gap-2 mb-4">
        <Search size={18} className="text-brand-400" />
        <h2 className="text-lg font-semibold text-white">Potential Matches</h2>
      </div>
      {renderContent()}
    </section>
  );
}