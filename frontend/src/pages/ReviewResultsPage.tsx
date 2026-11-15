import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  CheckCircle2,
  FileCode2,
  Filter,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import { MergeBadge, SeverityBadge } from "../components/SeverityBadge";
import { fetchReviewDetail } from "../services/api";
import type { ReviewDetailResponse, Severity } from "../types/review";

const SEVERITIES: Array<Severity | "ALL"> = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
const AGENT_OPTIONS = [
  { value: "ALL", label: "All Agents" },
  { value: "diff_agent", label: "Diff Agent" },
  { value: "style_agent", label: "Style Agent" },
  { value: "security_agent", label: "Security Agent" },
  { value: "test_coverage_agent", label: "Test-Coverage Agent" },
];

export function ReviewResultsPage() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [detail, setDetail] = useState<ReviewDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sevFilter, setSevFilter] = useState<Severity | "ALL">("ALL");
  const [agentFilter, setAgentFilter] = useState<string>("ALL");

  useEffect(() => {
    if (!reviewId) return;
    fetchReviewDetail(reviewId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load review"))
      .finally(() => setLoading(false));
  }, [reviewId]);

  const filteredFindings = useMemo(() => {
    if (!detail) return [];
    return detail.consolidated_findings.filter((f) => {
      if (sevFilter !== "ALL" && f.severity !== sevFilter) return false;
      if (
        agentFilter !== "ALL" &&
        f.agent !== agentFilter &&
        !f.corroborated_by.includes(agentFilter)
      ) {
        return false;
      }
      return true;
    });
  }, [detail, sevFilter, agentFilter]);

  if (loading) {
    return <div className="text-sm text-slate-400">Loading review report...</div>;
  }
  if (error || !detail) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
        {error ?? "Review not found."}
      </div>
    );
  }

  const diffOutput = detail.agent_outputs["diff_agent"] as
    | { change_summary?: string; modified_files?: Array<{ path: string; status: string; additions: number; deletions: number }> }
    | undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-semibold text-slate-100">
              {detail.submission_metadata.title}
            </h1>
            <MergeBadge decision={detail.merge_recommendation?.decision} />
            {detail.submission_metadata.demo_mode && (
              <span className="px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-[11px] font-mono text-amber-300">
                DEMO MODE
              </span>
            )}
          </div>
          {detail.submission_metadata.description && (
            <p className="text-sm text-slate-400 mt-1">{detail.submission_metadata.description}</p>
          )}
          <div className="text-xs font-mono text-slate-500 mt-1">
            ID: {detail.review_id} · Duration:{" "}
            {detail.execution_timestamps.total_duration_ms ?? "—"} ms · Model:{" "}
            {detail.submission_metadata.model_used}
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to={`/reviews/${detail.review_id}/live`}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-surface-700 bg-surface-900 hover:bg-surface-800 text-xs font-medium text-slate-200"
          >
            <Activity className="w-3.5 h-3.5" />
            Execution Trace
          </Link>
          <Link
            to={`/reviews/${detail.review_id}/patch`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white"
          >
            <Wrench className="w-3.5 h-3.5" />
            Fix Suggestion Patch
          </Link>
        </div>
      </div>

      {/* Merge Recommendation Justification */}
      {detail.merge_recommendation && (
        <div
          className={`rounded-lg border p-4 space-y-2 ${
            detail.merge_recommendation.decision === "APPROVE"
              ? "bg-emerald-500/5 border-emerald-500/30"
              : "bg-red-500/5 border-red-500/30"
          }`}
        >
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
            {detail.merge_recommendation.decision === "APPROVE" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-red-400" />
            )}
            Reviewer Manager Decision: {detail.merge_recommendation.decision}
          </div>
          <p className="text-sm text-slate-200 leading-relaxed">
            {detail.merge_recommendation.reasoning}
          </p>
          {detail.merge_recommendation.decision_factors.length > 0 && (
            <ul className="list-disc list-inside text-xs text-slate-300 space-y-0.5 pt-1">
              {detail.merge_recommendation.decision_factors.map((f, idx) => (
                <li key={idx}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Severity Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] as Severity[]).map((sev) => (
          <div
            key={sev}
            className="rounded-lg bg-surface-900 border border-surface-700 p-3 flex items-center justify-between"
          >
            <SeverityBadge severity={sev} />
            <span className="text-lg font-mono font-semibold text-slate-100">
              {detail.severity_summary[sev] ?? 0}
            </span>
          </div>
        ))}
      </div>

      {/* Code Change Summary & Modified Files */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-lg bg-surface-900 border border-surface-700 p-4 space-y-2">
          <h2 className="text-sm font-semibold text-slate-100">Code Change Summary</h2>
          <p className="text-sm text-slate-300 leading-relaxed">
            {diffOutput?.change_summary ||
              detail.agent_statuses["diff_agent"]?.summary ||
              "Diff summary unavailable."}
          </p>
        </div>

        <div className="rounded-lg bg-surface-900 border border-surface-700 p-4 space-y-2.5">
          <h2 className="text-sm font-semibold text-slate-100">
            Modified Files ({detail.files.length})
          </h2>
          <div className="space-y-1.5 max-h-40 overflow-y-auto">
            {(diffOutput?.modified_files ?? detail.files.map((f) => ({ path: f.path, status: f.status, additions: 0, deletions: 0 }))).map(
              (f) => (
                <div
                  key={f.path}
                  className="flex items-center justify-between text-xs font-mono bg-surface-950 border border-surface-700/70 rounded px-2.5 py-1.5"
                >
                  <span className="flex items-center gap-1.5 text-slate-200 truncate">
                    <FileCode2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                    {f.path}
                  </span>
                  <span className="text-slate-400 shrink-0 uppercase text-[10px]">
                    {f.status}
                  </span>
                </div>
              )
            )}
          </div>
        </div>
      </div>

      {/* Agent-Wise Summaries */}
      <div className="rounded-lg bg-surface-900 border border-surface-700 p-4 space-y-3">
        <h2 className="text-sm font-semibold text-slate-100">Agent-Wise Execution Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.values(detail.agent_statuses).map((ag) => (
            <div
              key={ag.agent_name}
              className="rounded-md bg-surface-950 border border-surface-700/80 p-3 space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200">{ag.display_name}</span>
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    ag.status === "completed"
                      ? "bg-emerald-500/10 text-emerald-400"
                      : ag.status === "failed"
                      ? "bg-red-500/10 text-red-400"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {ag.status.toUpperCase()}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{ag.summary || "—"}</p>
              <div className="text-[11px] font-mono text-slate-500 flex justify-between pt-1">
                <span>Tools: {ag.tools_invoked.join(", ") || "none"}</span>
                <span>{ag.duration_ms ? `${ag.duration_ms}ms` : ""}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Consolidated Findings + Filters */}
      <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
        <div className="px-4 py-3 border-b border-surface-700 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-slate-100">
            Consolidated Findings ({filteredFindings.length})
          </h2>

          <div className="flex flex-wrap items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <div className="flex flex-wrap gap-1">
              {SEVERITIES.map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setSevFilter(sev)}
                  className={`px-2 py-1 rounded text-[11px] font-mono border transition-colors ${
                    sevFilter === sev
                      ? "bg-blue-600/20 border-blue-500/50 text-blue-300"
                      : "bg-surface-950 border-surface-700 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
            <select
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              className="rounded bg-surface-950 border border-surface-700 px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
            >
              {AGENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {filteredFindings.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-400">
            No findings match the selected severity/agent filters.
          </div>
        ) : (
          <div className="divide-y divide-surface-700/70">
            {filteredFindings.map((finding) => (
              <div key={finding.id} className="p-4 space-y-2.5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <SeverityBadge severity={finding.severity} />
                    <h3 className="text-sm font-semibold text-slate-100">{finding.title}</h3>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                    <span className="px-2 py-0.5 rounded bg-surface-800 border border-surface-700 text-slate-300">
                      {finding.agent}
                    </span>
                    {finding.corroborated_by.length > 1 && (
                      <span className="text-blue-400">
                        +{finding.corroborated_by.length - 1} corroborated
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{finding.description}</p>

                <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-400">
                  <span>
                    File: <strong className="text-slate-200">{finding.file_path}</strong>
                    {finding.line_start ? `:${finding.line_start}` : ""}
                    {finding.line_end && finding.line_end !== finding.line_start
                      ? `-${finding.line_end}`
                      : ""}
                  </span>
                  {finding.rule_id && <span>Rule: {finding.rule_id}</span>}
                </div>

                {finding.evidence && (
                  <pre className="rounded bg-[#080A0F] border border-surface-700 p-2.5 font-mono text-xs text-slate-200 overflow-x-auto">
                    {finding.evidence}
                  </pre>
                )}

                {finding.recommended_action && (
                  <div className="text-xs text-emerald-300/90 bg-emerald-500/5 border border-emerald-500/20 rounded px-3 py-2">
                    <strong className="font-medium">Recommended Action: </strong>
                    {finding.recommended_action}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

