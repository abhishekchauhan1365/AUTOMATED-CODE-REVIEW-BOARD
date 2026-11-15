import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  FileCode2,
  PlusCircle,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { MergeBadge } from "../components/SeverityBadge";
import { fetchReviews, fetchStats } from "../services/api";
import type { DashboardStats, ReviewSummaryItem } from "../types/review";

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recent, setRecent] = useState<ReviewSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchStats(), fetchReviews()])
      .then(([s, r]) => {
        setStats(s);
        setRecent(r.slice(0, 6));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"))
      .finally(() => setLoading(false));
  }, []);

  const kpis = [
    {
      label: "Total Reviews",
      value: stats?.total_reviews ?? 0,
      icon: FileCode2,
      accent: "text-blue-400",
    },
    {
      label: "Approved Reviews",
      value: stats?.approved_reviews ?? 0,
      icon: CheckCircle2,
      accent: "text-emerald-400",
    },
    {
      label: "Changes Requested",
      value: stats?.changes_requested ?? 0,
      icon: XCircle,
      accent: "text-amber-400",
    },
    {
      label: "Critical Issues Detected",
      value: stats?.critical_issues_detected ?? 0,
      icon: ShieldAlert,
      accent: "text-red-400",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-100">
            Review Board Overview
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Live metrics aggregated from SQLite review records and Semantic Kernel agent runs.
          </p>
        </div>
        <Link
          to="/new"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-colors"
        >
          <PlusCircle className="w-4 h-4" />
          Start New Code Review
        </Link>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((item, idx) => {
          const Icon = item.icon;
          return (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              className="rounded-lg bg-surface-900 border border-surface-700 p-4"
            >
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>{item.label}</span>
                <Icon className={`w-4 h-4 ${item.accent}`} />
              </div>
              <div className="mt-2 text-2xl font-semibold font-mono text-slate-100">
                {loading ? "—" : item.value}
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-700 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-100">Recent Review Activity</h2>
            <Link
              to="/history"
              className="text-xs text-blue-400 hover:text-blue-300 inline-flex items-center gap-1"
            >
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {loading ? (
            <div className="p-6 text-sm text-slate-400">Loading reviews...</div>
          ) : recent.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <p className="text-sm text-slate-400">
                No reviews recorded yet. Submit source files or a Git diff to run all 6 agents.
              </p>
              <Link
                to="/new"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface-800 hover:bg-surface-700 border border-surface-700 text-xs font-medium text-slate-200"
              >
                <PlusCircle className="w-3.5 h-3.5" /> Create First Review
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-surface-700/70">
              {recent.map((rev) => (
                <Link
                  key={rev.review_id}
                  to={rev.status === "completed" ? `/reviews/${rev.review_id}` : `/reviews/${rev.review_id}/live`}
                  className="px-4 py-3 flex items-center justify-between gap-4 hover:bg-surface-850/80 transition-colors"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-100 truncate">
                        {rev.title}
                      </span>
                      {rev.demo_mode && (
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-[10px] font-mono text-amber-300">
                          DEMO
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      {rev.submission_type.toUpperCase()} · {rev.total_findings} finding(s) ·{" "}
                      {new Date(rev.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {rev.critical_count > 0 && (
                      <span className="text-xs font-mono text-red-400">
                        {rev.critical_count} CRIT
                      </span>
                    )}
                    <MergeBadge decision={rev.merge_recommendation} />
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-lg bg-surface-900 border border-surface-700 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-700 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-100">Agent Execution Statistics</h2>
          </div>
          <div className="p-4 space-y-3">
            {loading ? (
              <p className="text-xs text-slate-400">Loading agent stats...</p>
            ) : !stats || stats.agent_stats.length === 0 ? (
              <p className="text-xs text-slate-400">
                Statistics will appear here after your first multi-agent review run.
              </p>
            ) : (
              stats.agent_stats.map((ag) => (
                <div
                  key={ag.agent_name}
                  className="rounded-md bg-surface-950/70 border border-surface-700/70 p-3 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-200">{ag.display_name}</span>
                    <span className="text-[11px] font-mono text-slate-400">
                      {ag.avg_duration_ms} ms avg
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>
                      Runs: <strong className="text-slate-200">{ag.runs}</strong> (
                      <span className="text-emerald-400">{ag.completed} ok</span>
                      {ag.failed > 0 && <span className="text-red-400">, {ag.failed} err</span>})
                    </span>
                    <span>Findings: {ag.total_findings}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

