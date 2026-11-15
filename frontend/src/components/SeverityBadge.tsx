import type { MergeDecision, Severity } from "../types/review";

const SEVERITY_STYLES: Record<Severity, string> = {
  CRITICAL: "bg-red-500/15 text-red-400 border-red-500/30",
  HIGH: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  MEDIUM: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  LOW: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  INFO: "bg-slate-500/15 text-slate-300 border-slate-500/30",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold tracking-wide border ${SEVERITY_STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}

export function MergeBadge({ decision }: { decision: MergeDecision | null | undefined }) {
  if (!decision) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-mono border bg-slate-800/70 text-slate-400 border-slate-700">
        PENDING
      </span>
    );
  }
  const approved = decision === "APPROVE";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold border ${
        approved
          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
          : "bg-red-500/15 text-red-400 border-red-500/30"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${approved ? "bg-emerald-400" : "bg-red-400"}`} />
      {decision}
    </span>
  );
}

