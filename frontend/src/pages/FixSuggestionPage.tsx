import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  Download,
  Lock,
  ShieldCheck,
} from "lucide-react";
import { SeverityBadge } from "../components/SeverityBadge";
import { approvePatch, fetchReviewDetail, getPatchDownloadUrl } from "../services/api";
import type { FixSuggestion } from "../types/review";

export function FixSuggestionPage() {
  const { reviewId } = useParams<{ reviewId: string }>();
  const [patch, setPatch] = useState<FixSuggestion | null>(null);
  const [title, setTitle] = useState("");
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!reviewId) return;
    fetchReviewDetail(reviewId)
      .then((detail) => {
        setTitle(detail.submission_metadata.title);
        setPatch(detail.fix_suggestion);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load patch"))
      .finally(() => setLoading(false));
  }, [reviewId]);

  const handleCopy = async () => {
    if (!patch?.proposed_patch) return;
    await navigator.clipboard.writeText(patch.proposed_patch);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  const handleApprove = async () => {
    if (!reviewId) return;
    setApproving(true);
    setError(null);
    try {
      const updated = await approvePatch(reviewId);
      setPatch(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setApproving(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-slate-400">Loading Fix-Suggestion Agent output...</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            to={`/reviews/${reviewId}`}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-1.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Review Report
          </Link>
          <h1 className="text-xl font-semibold text-slate-100">
            Fix-Suggestion Agent · Proposed Patch
          </h1>
          <p className="text-xs font-mono text-slate-400 mt-0.5">{title}</p>
        </div>

        {patch?.available && (
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-md border border-surface-700 bg-surface-900 hover:bg-surface-800 text-xs font-medium text-slate-200"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? "Copied Patch" : "Copy Patch"}
            </button>

            {patch.user_approved && reviewId ? (
              <a
                href={getPatchDownloadUrl(reviewId)}
                download={`fix_${reviewId.slice(0, 8)}.patch`}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-emerald-600 hover:bg-emerald-500 text-xs font-medium text-white"
              >
                <Download className="w-3.5 h-3.5" />
                Download Patch
              </a>
            ) : (
              <button
                type="button"
                disabled
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md bg-surface-800 border border-surface-700 text-xs font-medium text-slate-500 cursor-not-allowed"
                title="Explicit user approval is required before downloading"
              >
                <Lock className="w-3.5 h-3.5" />
                Download Locked (Approval Required)
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-500/10 border border-red-500/30 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {!patch || !patch.available ? (
        <div className="rounded-lg bg-surface-900 border border-surface-700 p-6 space-y-2">
          <h2 className="text-sm font-semibold text-slate-200">No Patch Generated</h2>
          <p className="text-sm text-slate-400">
            {patch?.explanation ||
              "No actionable code-level findings required a patch for this review."}
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Selected Highest-Priority Finding */}
          {patch.selected_finding && (
            <div className="rounded-lg bg-surface-900 border border-surface-700 p-4 space-y-2">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2.5">
                  <SeverityBadge severity={patch.selected_finding.severity} />
                  <span className="text-sm font-semibold text-slate-100">
                    {patch.selected_finding.title}
                  </span>
                </div>
                <span className="text-xs font-mono text-slate-400">
                  {patch.file_path}:{patch.line_start}
                </span>
              </div>
              <p className="text-xs text-slate-300">{patch.selected_finding.description}</p>
            </div>
          )}

          {/* Explanation & Validation Status */}
          <div className="rounded-lg bg-surface-900 border border-surface-700 p-4 space-y-2.5">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-sm font-semibold text-slate-100">Fix Explanation</h2>
              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono border ${
                  patch.validation_status === "valid"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                    : "bg-red-500/10 text-red-400 border-red-500/30"
                }`}
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                Validation: {patch.validation_status.toUpperCase()}
              </span>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">{patch.explanation}</p>
            <p className="text-xs font-mono text-slate-400">{patch.validation_message}</p>
          </div>

          {/* Original vs Suggested Replacement */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
              <div className="px-3 py-2 border-b border-surface-700 text-xs font-mono text-red-300 bg-red-500/5">
                Original Code ({patch.file_path}:{patch.line_start})
              </div>
              <pre className="p-3 font-mono text-xs text-slate-200 bg-[#080A0F] overflow-x-auto">
                {patch.original_code}
              </pre>
            </div>
            <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
              <div className="px-3 py-2 border-b border-surface-700 text-xs font-mono text-emerald-300 bg-emerald-500/5">
                Proposed Replacement
              </div>
              <pre className="p-3 font-mono text-xs text-slate-200 bg-[#080A0F] overflow-x-auto">
                {patch.suggested_replacement}
              </pre>
            </div>
          </div>

          {/* Unified Diff Preview */}
          <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
            <div className="px-4 py-2.5 border-b border-surface-700 text-xs font-semibold text-slate-200">
              Unified Diff Preview
            </div>
            <div className="p-3 bg-[#080A0F] font-mono text-xs overflow-x-auto space-y-0.5">
              {patch.proposed_patch.split("\n").map((line, i) => {
                let cls = "text-slate-300";
                if (line.startsWith("+") && !line.startsWith("+++")) {
                  cls = "bg-emerald-500/10 text-emerald-300";
                } else if (line.startsWith("-") && !line.startsWith("---")) {
                  cls = "bg-red-500/10 text-red-300";
                } else if (line.startsWith("@@")) {
                  cls = "text-blue-400";
                }
                return (
                  <div key={i} className={`px-2 py-0.5 whitespace-pre ${cls}`}>
                    {line || " "}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Explicit Safety Approval Gate */}
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1 max-w-2xl">
              <div className="text-xs font-semibold text-amber-300 uppercase tracking-wide">
                Human-in-the-Loop Safety Gate
              </div>
              <p className="text-xs text-slate-300">{patch.safety_note}</p>
              {patch.user_approved && patch.approved_at && (
                <p className="text-xs font-mono text-emerald-400 flex items-center gap-1.5 pt-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Approved by user at {new Date(patch.approved_at).toLocaleString()}
                </p>
              )}
            </div>

            {!patch.user_approved && (
              <button
                type="button"
                onClick={handleApprove}
                disabled={approving}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-amber-500 hover:bg-amber-400 text-xs font-semibold text-slate-950 transition-colors"
              >
                <CheckCircle2 className="w-4 h-4" />
                {approving ? "Recording Approval..." : "Approve Patch for Download"}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

