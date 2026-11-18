import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Clock, Loader2, Wrench } from "lucide-react";
import type { AgentStatusRecord } from "../types/review";

export function AgentStatusCard({ agent }: { agent: AgentStatusRecord }) {
  const statusConfig = {
    pending: {
      icon: Clock,
      badge: "text-slate-600 bg-slate-100 border-slate-250",
      border: "border-surface-700 shadow-sm",
      label: "Pending",
    },
    running: {
      icon: Loader2,
      badge: "text-blue-700 bg-blue-50 border-blue-200",
      border: "border-blue-300 shadow-sm",
      label: "Running",
    },
    completed: {
      icon: CheckCircle2,
      badge: "text-emerald-700 bg-emerald-50 border-emerald-200",
      border: "border-surface-700 shadow-sm",
      label: "Completed",
    },
    failed: {
      icon: AlertCircle,
      badge: "text-red-700 bg-red-50 border-red-200",
      border: "border-red-300 shadow-sm",
      label: "Failed",
    },
  }[agent.status];

  const Icon = statusConfig.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`rounded-xl bg-surface-900 border ${statusConfig.border} p-4 flex flex-col gap-3`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">{agent.display_name}</h3>
          <p className="text-xs text-slate-400 mt-0.5">{agent.role}</p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium border ${statusConfig.badge}`}
        >
          <Icon className={`w-3.5 h-3.5 ${agent.status === "running" ? "animate-spin" : ""}`} />
          {statusConfig.label}
        </span>
      </div>

      <div className="text-xs text-slate-300 bg-surface-850 border border-surface-700 rounded px-2.5 py-2 font-mono truncate">
        {agent.current_activity}
      </div>

      {agent.summary && (
        <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">{agent.summary}</p>
      )}
      {agent.error && (
        <p className="text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2 font-mono">
          {agent.error}
        </p>
      )}

      <div className="flex items-center justify-between pt-1 border-t border-surface-700/60 text-[11px] text-slate-400">
        <span className="font-mono">
          Findings:{" "}
          <strong className="text-slate-100">{agent.findings_count}</strong>
        </span>
        <span className="font-mono">
          {agent.duration_ms !== null ? `${agent.duration_ms} ms` : "—"}
        </span>
      </div>

      {agent.tools_invoked.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {agent.tools_invoked.map((tool) => (
            <span
              key={tool}
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-850 border border-surface-700 text-[10px] font-mono text-slate-300"
            >
              <Wrench className="w-2.5 h-2.5 text-slate-400" />
              {tool}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
}
