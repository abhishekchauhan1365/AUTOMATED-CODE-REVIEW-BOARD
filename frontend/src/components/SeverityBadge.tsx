import type { MergeDecision, Severity } from "../types/review";

const SEVERITY_STYLES: Record<Severity, string> = {
  CRITICAL: "bg-red-50 text-red-700 border-red-200",
  HIGH: "bg-orange-50 text-orange-700 border-orange-200",
  MEDIUM: "bg-amber-50 text-amber-800 border-amber-200",
  LOW: "bg-sky-50 text-sky-700 border-sky-200",
  INFO: "bg-slate-100 text-slate-700 border-slate-200",
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
      <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-mono border bg-slate-100 text-slate-600 border-slate-200">
        PENDING
      </span>
    );
  }
  const approved = decision === "APPROVE";
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-semibold border ${
        approved
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : "bg-red-50 text-red-700 border-red-200"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${approved ? "bg-emerald-600" : "bg-red-600"}`} />
      {decision}
    </span>
  );
}
