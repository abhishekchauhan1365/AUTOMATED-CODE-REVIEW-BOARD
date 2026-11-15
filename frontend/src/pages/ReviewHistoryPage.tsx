import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeftRight, ExternalLink, Trash2 } from "lucide-react";
import { MergeBadge } from "../components/SeverityBadge";
import { deleteReviewRecord, fetchReviews } from "../services/api";
import type { ReviewSummaryItem } from "../types/review";

export function ReviewHistoryPage() {
  const [reviews, setReviews] = useState<ReviewSummaryItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    fetchReviews()
      .then(setReviews)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load history"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const toggleCompare = (id: string) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const handleDelete = async (id: string) => {
    await deleteReviewRecord(id);
    setSelectedIds((prev) => prev.filter((x) => x !== id));
    setReviews((prev) => prev.filter((r) => r.review_id !== id));
  };

  const compared = reviews.filter((r) => selectedIds.includes(r.review_id));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Review History</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            SQLite-persisted reviews. Select any two reviews to compare merge recommendations.
          </p>
        </div>
        {selectedIds.length > 0 && (
          <button
            type="button"
            onClick={() => setSelectedIds([])}
            className="text-xs text-slate-400 hover:text-slate-200 underline"
          >
            Clear comparison ({selectedIds.length}/2)
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-md bg-red-500/10 border border-red-500/30 p-3 text-xs text-red-300">
          {error}
        </div>
      )}

      {compared.length === 2 && (
        <div className="rounded-lg bg-surface-900 border border-blue-500/30 p-4 space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-blue-300 uppercase tracking-wider">
            <ArrowLeftRight className="w-3.5 h-3.5" />
            Side-by-Side Recommendation Comparison
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {compared.map((c) => (
              <div
                key={c.review_id}
                className="rounded-md bg-surface-950 border border-surface-700 p-3 space-y-2"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-100 truncate">{c.title}</span>
                  <MergeBadge decision={c.merge_recommendation} />
                </div>
                <div className="grid grid-cols-5 gap-1 text-center font-mono text-[11px] pt-1">
                  <div className="rounded bg-red-500/10 text-red-300 py-1">
                    CRIT {c.critical_count}
                  </div>
                  <div className="rounded bg-orange-500/10 text-orange-300 py-1">
                    HIGH {c.high_count}
                  </div>
                  <div className="rounded bg-amber-500/10 text-amber-300 py-1">
                    MED {c.medium_count}
                  </div>
                  <div className="rounded bg-sky-500/10 text-sky-300 py-1">
                    LOW {c.low_count}
                  </div>
                  <div className="rounded bg-slate-800 text-slate-300 py-1">
                    INFO {c.info_count}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
        {loading ? (
          <div className="p-6 text-sm text-slate-400">Loading review records...</div>
        ) : reviews.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-400">
            No review records found in SQLite.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-surface-700 text-[11px] font-mono uppercase text-slate-400 bg-surface-950/60">
                  <th className="py-2.5 px-3">Compare</th>
                  <th className="py-2.5 px-3">Title</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Decision</th>
                  <th className="py-2.5 px-3">Findings</th>
                  <th className="py-2.5 px-3">Duration</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700/70 text-xs">
                {reviews.map((rev) => (
                  <tr key={rev.review_id} className="hover:bg-surface-850/60">
                    <td className="py-3 px-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(rev.review_id)}
                        onChange={() => toggleCompare(rev.review_id)}
                        className="accent-blue-500 w-3.5 h-3.5"
                      />
                    </td>
                    <td className="py-3 px-3">
                      <Link
                        to={`/reviews/${rev.review_id}`}
                        className="font-medium text-slate-100 hover:text-blue-400"
                      >
                        {rev.title}
                      </Link>
                      <div className="text-[11px] font-mono text-slate-500">
                        {new Date(rev.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-300 uppercase">
                      {rev.submission_type}
                    </td>
                    <td className="py-3 px-3">
                      <MergeBadge decision={rev.merge_recommendation} />
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-300">
                      {rev.total_findings}
                      {rev.critical_count > 0 && (
                        <span className="ml-1.5 text-red-400">({rev.critical_count} crit)</span>
                      )}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">
                      {rev.duration_ms ? `${rev.duration_ms} ms` : "—"}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <Link
                          to={`/reviews/${rev.review_id}`}
                          className="p-1.5 rounded text-slate-400 hover:text-slate-100 hover:bg-surface-800"
                          title="Open review"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleDelete(rev.review_id)}
                          className="p-1.5 rounded text-slate-400 hover:text-red-400 hover:bg-surface-800"
                          title="Delete review"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

