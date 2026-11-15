import { Link, useParams } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  GitBranch,
  GitMerge,
  Loader2,
  Wrench,
} from "lucide-react";
import { AgentStatusCard } from "../components/AgentStatusCard";
import { useReviewStream } from "../hooks/useReviewStream";

const SPECIALIST_KEYS = [
  "diff_agent",
  "style_agent",
  "security_agent",
  "test_coverage_agent",
];

export function LiveExecutionPage() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const { status, events, error } = useReviewStream(reviewId);

  const isDone =
    status?.overall_status === "completed" || status?.overall_status === "failed";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-semibold text-slate-100">
              Live Multi-Agent Execution
            </h1>
            {status && (
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono border ${
                  isDone
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                }`}
              >
                {!isDone && <Loader2 className="w-3 h-3 animate-spin" />}
                {isDone && <CheckCircle2 className="w-3 h-3" />}
                {status.overall_status.toUpperCase()}
              </span>
            )}
          </div>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Review ID: {reviewId} · Phase: {status?.phase ?? "initializing"}
          </p>
        </div>

        {isDone && reviewId && (
          <div className="flex items-center gap-2.5">
            <Link
              to={`/reviews/${reviewId}/patch`}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md border border-surface-700 bg-surface-900 hover:bg-surface-800 text-xs font-medium text-slate-200"
            >
              <Wrench className="w-3.5 h-3.5" />
              View Fix Patch
            </Link>
            <Link
              to={`/reviews/${reviewId}`}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white"
            >
              View Review Report
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-500/10 border border-red-500/30 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {status && (
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-300 uppercase tracking-wider">
              <GitBranch className="w-3.5 h-3.5 text-blue-400" />
              Stage 1 · Parallel Fan-Out Specialists (ConcurrentOrchestration)
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              {SPECIALIST_KEYS.map((key) =>
                status.agent_statuses[key] ? (
                  <AgentStatusCard key={key} agent={status.agent_statuses[key]} />
                ) : null
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-300 uppercase tracking-wider">
              <GitMerge className="w-3.5 h-3.5 text-emerald-400" />
              Stage 2 & 3 · Fan-In Consolidation & Fix Recommendation
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {status.agent_statuses["reviewer_manager"] && (
                <AgentStatusCard agent={status.agent_statuses["reviewer_manager"]} />
              )}
              {status.agent_statuses["fix_suggestion_agent"] && (
                <AgentStatusCard agent={status.agent_statuses["fix_suggestion_agent"]} />
              )}
            </div>
          </div>
        </div>
      )}

      <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
        <div className="px-4 py-2.5 border-b border-surface-700 text-xs font-semibold text-slate-200">
          Real-Time Execution Trace
        </div>
        <div className="p-3 max-h-60 overflow-y-auto font-mono text-xs space-y-1.5 bg-[#080A0F]">
          {events.length === 0 ? (
            <div className="text-slate-500">Waiting for SSE events from backend...</div>
          ) : (
            events.map((ev, i) => (
              <div key={`${ev.timestamp}-${i}`} className="flex items-start gap-2.5 text-slate-300">
                <span className="text-slate-500 shrink-0">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-blue-400 shrink-0 w-36 truncate">[{ev.agent_name}]</span>
                <span className={ev.error ? "text-red-400" : "text-slate-200"}>
                  {ev.message || ev.event}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

