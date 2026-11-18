export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type MergeDecision = "APPROVE" | "REQUEST_CHANGES";
export type AgentExecutionState = "pending" | "running" | "completed" | "failed";

export interface SubmittedFile {
  path: string;
  language: string;
  content: string;
  size_bytes: number;
  status: "added" | "modified" | "deleted";
}

export interface SubmissionMetadata {
  title: string;
  description: string;
  submission_type: "files" | "diff";
  created_at: string;
  llm_provider: string;
  model_used: string;
  demo_mode: boolean;
}

export interface Finding {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  agent: string;
  category: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  evidence: string;
  recommended_action: string;
  rule_id: string | null;
  source: "deterministic_tool" | "llm_analysis" | "hybrid" | "demo_mode";
  confidence: number;
  corroborated_by: string[];
}

export interface AgentStatusRecord {
  agent_name: string;
  display_name: string;
  role: string;
  status: AgentExecutionState;
  current_activity: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  findings_count: number;
  summary: string;
  error: string | null;
  tools_invoked: string[];
}

export interface MergeRecommendation {
  decision: MergeDecision;
  reasoning: string;
  decision_factors: string[];
  blocking_findings_count: number;
  has_agent_failures: boolean;
}

export interface FixSuggestion {
  available: boolean;
  selected_finding: Finding | null;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  original_code: string;
  suggested_replacement: string;
  explanation: string;
  proposed_patch: string;
  validation_status: "valid" | "invalid" | "unavailable";
  validation_message: string;
  requires_explicit_approval: boolean;
  user_approved: boolean;
  approved_at: string | null;
  safety_note: string;
}

export interface ExecutionTimestamps {
  submitted_at: string;
  started_at: string | null;
  fan_out_started_at: string | null;
  fan_in_completed_at: string | null;
  completed_at: string | null;
  total_duration_ms: number | null;
}

export interface ExecutionEvent {
  timestamp: string;
  review_id: string;
  agent_name: string;
  event: string;
  status: string;
  findings_count: number;
  message: string;
  error: string | null;
}

export interface ReviewStatusResponse {
  review_id: string;
  overall_status: "pending" | "running" | "completed" | "failed";
  phase: string;
  demo_mode: boolean;
  agent_statuses: Record<string, AgentStatusRecord>;
  timestamps: ExecutionTimestamps;
}

export interface ReviewSummaryItem {
  review_id: string;
  title: string;
  description: string;
  submission_type: string;
  status: string;
  merge_recommendation: MergeDecision | null;
  demo_mode: boolean;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  total_findings: number;
  patch_approved?: boolean;
  created_at: string;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface ReviewDetailResponse {
  review_id: string;
  overall_status: "pending" | "running" | "completed" | "failed";
  submission_metadata: SubmissionMetadata;
  files: SubmittedFile[];
  git_diff: string | null;
  agent_statuses: Record<string, AgentStatusRecord>;
  agent_findings: Record<string, Finding[]>;
  agent_outputs: Record<string, Record<string, unknown>>;
  severity_summary: Record<Severity, number>;
  consolidated_findings: Finding[];
  merge_recommendation: MergeRecommendation | null;
  fix_suggestion: FixSuggestion | null;
  execution_timestamps: ExecutionTimestamps;
  events: ExecutionEvent[];
}

export interface DashboardStats {
  total_reviews: number;
  approved_reviews: number;
  changes_requested: number;
  critical_issues_detected: number;
  total_critical_detected?: number;
  patches_approved?: number;
  agent_stats: Array<{
    agent_name: string;
    display_name: string;
    runs: number;
    completed: number;
    failed: number;
    avg_duration_ms: number;
    total_findings: number;
  }>;
}

export interface HealthInfo {
  status: string;
  demo_mode_default: boolean;
  framework: string;
  model: string;
}

