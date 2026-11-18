import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Code2,
  Cpu,
  FileCode2,
  GitBranch,
  GitCompare,
  GitPullRequest,
  Layers,
  Lock,
  LogIn,
  LogOut,
  Play,
  RotateCcw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Wrench,
  Zap,
} from "lucide-react";
import { fetchHealth, fetchStats } from "../services/api";
import { getStoredUser, logoutUser } from "../services/auth";
import type { UserProfile } from "../types/auth";
import type { DashboardStats, HealthInfo } from "../types/review";

const AGENTS = [
  {
    name: "Diff Agent",
    role: "Structure & AST Delta",
    description: "Parses unified diff hunks, extracts modified functions, and detects structural syntax risks.",
    tools: ["parse_git_diff", "analyze_code_structure"],
    accent: "text-sky-700 bg-sky-50 border-sky-200",
    icon: GitCompare,
  },
  {
    name: "Style Agent",
    role: "Linter & Complexity Audit",
    description: "Runs Ruff static linter, calculates Radon cyclomatic complexity, and checks code style.",
    tools: ["run_linter (Ruff)", "calculate_complexity (Radon)"],
    accent: "text-emerald-700 bg-emerald-50 border-emerald-200",
    icon: FileCode2,
  },
  {
    name: "Security Agent",
    role: "Secrets & Vulnerability Scan",
    description: "Detects secrets with auto-redaction, flags SQLi patterns, shell injections, and Bandit flaws.",
    tools: ["scan_for_secrets", "run_security_analysis (Bandit)"],
    accent: "text-red-700 bg-red-50 border-red-200",
    icon: ShieldAlert,
  },
  {
    name: "Test-Coverage Agent",
    role: "Test Mapping & Gap Audit",
    description: "Maps changed functions to test suites, audits test coverage, and proposes missing test cases.",
    tools: ["discover_test_files", "analyze_test_coverage"],
    accent: "text-amber-700 bg-amber-50 border-amber-200",
    icon: CheckCircle2,
  },
  {
    name: "Reviewer Manager",
    role: "Fan-In Orchestrator & Decision",
    description: "Coordinates parallel execution via Semantic Kernel, deduplicates findings, and decides APPROVE / REQUEST_CHANGES.",
    tools: ["deduplicate_findings", "rank_findings", "generate_review_report"],
    accent: "text-indigo-700 bg-indigo-50 border-indigo-200",
    icon: Cpu,
  },
  {
    name: "Fix-Suggestion Agent",
    role: "Automated Patch Generation",
    description: "Group-of-three extension. Analyzes highest-severity finding and generates a validated unified diff patch.",
    tools: ["extract_code_context", "generate_unified_patch", "validate_patch"],
    accent: "text-purple-700 bg-purple-50 border-purple-200",
    icon: Wrench,
  },
];

const STEPS = [
  {
    step: "01",
    title: "Submit Code Change",
    description: "Provide a unified Git diff or source files. Creates grounded SharedChangeState in memory.",
  },
  {
    step: "02",
    title: "Concurrent Fan-Out",
    description: "Diff, Style, Security, and Test-Coverage agents execute simultaneously calling real static tools.",
  },
  {
    step: "03",
    title: "Consolidated Verdict & Fix",
    description: "Reviewer Manager deduplicates findings, scores severity, and Fix Agent generates a validated patch.",
  },
];

export function LandingPage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthInfo | null>(null);

  // Interactive Live Simulator Tab state
  const [demoTab, setDemoTab] = useState<"diff" | "orchestration" | "verdict">("orchestration");
  const [demoPatchApproved, setDemoPatchApproved] = useState(false);

  useEffect(() => {
    setUser(getStoredUser());
    fetchStats().then(setStats).catch(() => setStats(null));
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
  };

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col selection:bg-blue-100 selection:text-blue-900">
      {/* Top Navbar */}
      <header className="h-16 border-b border-surface-700 bg-surface-900/90 backdrop-blur-md sticky top-0 z-50 px-6 shadow-sm">
        <div className="max-w-6xl mx-auto h-full flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shadow-xs">
              <ShieldCheck className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <span className="text-sm font-semibold tracking-tight text-slate-100">
                Automated Code Review Board
              </span>
              <span className="ml-2 text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-600">
                CSE476 · Group 14
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {health && (
              <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>Semantic Kernel Live</span>
              </div>
            )}

            {user ? (
              <div className="flex items-center gap-2.5">
                <span className="text-xs text-slate-300 font-medium hidden md:inline">
                  {user.name}
                </span>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-all shadow-xs hover:shadow-sm"
                >
                  Dashboard <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-surface-700 bg-surface-850 hover:bg-surface-800 text-xs text-slate-300 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-all shadow-xs hover:shadow-sm"
              >
                <LogIn className="w-3.5 h-3.5" />
                Sign In
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-16 pb-12 px-6 text-center relative overflow-hidden">
        {/* Soft background ambient glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-blue-100/40 rounded-full blur-[100px] pointer-events-none" />

        <div className="max-w-4xl mx-auto space-y-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-surface-900 border border-surface-700 text-xs text-blue-700 font-mono shadow-xs"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            <span>Microsoft Semantic Kernel · 6-Agent Fan-Out / Fan-In System</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-100 leading-tight"
          >
            Autonomous Multi-Agent <br className="hidden sm:inline" />
            Code Review Board
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto"
          >
            Decomposes pull request inspection across parallel specialists: structural changes,
            style compliance, security vulnerabilities, and test coverage gaps — delivering a consolidated verdict and fix patch.
          </motion.p>

          {/* CTA Actions */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="pt-2 flex flex-wrap items-center justify-center gap-3"
          >
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-all shadow-md shadow-blue-500/10 hover:shadow-lg"
                >
                  <Play className="w-4 h-4 fill-white" />
                  Open Review Studio
                </Link>
                <Link
                  to="/new"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface-900 hover:bg-surface-850 border border-surface-700 text-sm font-medium text-slate-100 transition-all shadow-xs"
                >
                  <GitCompare className="w-4 h-4 text-slate-400" />
                  Submit New Review
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-all shadow-md shadow-blue-500/10 hover:shadow-lg"
                >
                  <Lock className="w-4 h-4" />
                  Sign In to Access Board
                </Link>
                <a
                  href="https://github.com/abhishekchauhan1365/AUTOMATED-CODE-REVIEW-BOARD"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface-900 hover:bg-surface-850 border border-surface-700 text-sm font-medium text-slate-100 transition-all shadow-xs"
                >
                  <GitBranch className="w-4 h-4 text-slate-400" />
                  GitHub Repository
                </a>
              </>
            )}
          </motion.div>

          {/* Dynamic Telemetry Strip */}
          <div className="pt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto">
            <div className="p-3 rounded-lg bg-surface-900 border border-surface-700 text-center shadow-xs">
              <div className="text-xl font-bold font-mono text-slate-100">
                {stats?.total_reviews ?? 4}
              </div>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">Reviews Processed</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-900 border border-surface-700 text-center shadow-xs">
              <div className="text-xl font-bold font-mono text-blue-600">6</div>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">Specialist Agents</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-900 border border-surface-700 text-center shadow-xs">
              <div className="text-xl font-bold font-mono text-emerald-600">12+</div>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">Static AST Tools</div>
            </div>
            <div className="p-3 rounded-lg bg-surface-900 border border-surface-700 text-center shadow-xs">
              <div className="text-xl font-bold font-mono text-purple-600">
                {stats?.patches_approved ?? 2}
              </div>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">Patches Approved</div>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive Live Multi-Agent Simulator Preview */}
      <section className="py-8 px-6">
        <div className="max-w-4xl mx-auto rounded-xl bg-surface-900 border border-surface-700 shadow-md overflow-hidden">
          {/* Simulator Header & Tabs */}
          <div className="px-4 py-3 border-b border-surface-700 bg-surface-850/60 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-semibold text-slate-100 font-mono">
                Interactive Multi-Agent Review Walkthrough
              </span>
            </div>

            <div className="flex items-center gap-1 bg-surface-900 p-1 rounded-lg border border-surface-700">
              <button
                type="button"
                onClick={() => setDemoTab("diff")}
                className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                  demoTab === "diff"
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-400 hover:text-slate-100"
                }`}
              >
                1. Pull Request Diff
              </button>
              <button
                type="button"
                onClick={() => setDemoTab("orchestration")}
                className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                  demoTab === "orchestration"
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-400 hover:text-slate-100"
                }`}
              >
                2. Parallel Fan-Out
              </button>
              <button
                type="button"
                onClick={() => setDemoTab("verdict")}
                className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                  demoTab === "verdict"
                    ? "bg-blue-600 text-white shadow-xs"
                    : "text-slate-400 hover:text-slate-100"
                }`}
              >
                3. Verdict &amp; Fix Patch
              </button>
            </div>
          </div>

          {/* Simulator Tab Content */}
          <div className="p-5">
            <AnimatePresence mode="wait">
              {demoTab === "diff" && (
                <motion.div
                  key="diff"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="space-y-3"
                >
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span>File: <strong>api/auth_handler.py</strong> (Unified Git Diff)</span>
                    <span className="text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      Unreviewed Changes
                    </span>
                  </div>
                  <div className="p-3.5 bg-surface-850 rounded-lg border border-surface-700 font-mono text-xs space-y-1 overflow-x-auto">
                    <div className="text-slate-400">--- a/api/auth_handler.py</div>
                    <div className="text-slate-400">+++ b/api/auth_handler.py</div>
                    <div className="text-blue-700 bg-blue-50/60 px-1 py-0.5 rounded">@@ -1,7 +1,7 @@</div>
                    <div className="text-red-700 bg-red-50/80 px-1 rounded">- GROQ_API_SECRET = "gsk_9876543210abcdefghijklmnop"</div>
                    <div className="text-emerald-700 bg-emerald-50/80 px-1 rounded">+ GROQ_API_SECRET = os.getenv("GROQ_API_SECRET", "")</div>
                    <div className="text-red-700 bg-red-50/80 px-1 rounded">- cursor.execute(f"SELECT * FROM users WHERE id = '{'{user_id}'}'")</div>
                    <div className="text-emerald-700 bg-emerald-50/80 px-1 rounded">+ cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))</div>
                    <div className="text-red-700 bg-red-50/80 px-1 rounded">- eval(filter_expr)</div>
                  </div>
                  <p className="text-xs text-slate-400">
                    The diff above contains a hardcoded API token, SQL injection vulnerability, and arbitrary code execution call.
                  </p>
                </motion.div>
              )}

              {demoTab === "orchestration" && (
                <motion.div
                  key="orchestration"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="space-y-4"
                >
                  <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                    <span>Orchestration: <strong>Semantic Kernel ConcurrentOrchestration</strong></span>
                    <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-semibold">
                      4 Agents Dispatched in Parallel
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-lg bg-surface-850 border border-surface-700 space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                        <span className="flex items-center gap-1.5">
                          <GitCompare className="w-4 h-4 text-sky-600" /> Diff Agent
                        </span>
                        <span className="text-emerald-700 font-mono text-[11px]">✓ Completed (1.4s)</span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-sky-600 h-full w-full rounded-full" />
                      </div>
                      <p className="text-[11px] text-slate-400">Parsed 1 diff hunk, mapped 2 modified functions, flagged 2 AST risk spots.</p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-surface-850 border border-surface-700 space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                        <span className="flex items-center gap-1.5">
                          <FileCode2 className="w-4 h-4 text-emerald-600" /> Style Agent
                        </span>
                        <span className="text-emerald-700 font-mono text-[11px]">✓ Completed (1.5s)</span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-emerald-600 h-full w-full rounded-full" />
                      </div>
                      <p className="text-[11px] text-slate-400">Ruff executed: 1 PEP8 violation. Radon cyclomatic complexity: Grade B.</p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-surface-850 border border-surface-700 space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                        <span className="flex items-center gap-1.5">
                          <ShieldAlert className="w-4 h-4 text-red-600" /> Security Agent
                        </span>
                        <span className="text-red-700 font-mono text-[11px]">⚠️ 2 Critical Found</span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-red-600 h-full w-full rounded-full" />
                      </div>
                      <p className="text-[11px] text-slate-400">Flagged hardcoded secret (redacted: sk-************890) and Bandit SQLi finding.</p>
                    </div>

                    <div className="p-3.5 rounded-lg bg-surface-850 border border-surface-700 space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                        <span className="flex items-center gap-1.5">
                          <CheckCircle2 className="w-4 h-4 text-amber-600" /> Test-Coverage Agent
                        </span>
                        <span className="text-amber-700 font-mono text-[11px]">⚠️ Test Gap</span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-amber-600 h-full w-full rounded-full" />
                      </div>
                      <p className="text-[11px] text-slate-400">No test suite covers fetch_user_profile(). Proposed 2 missing unit test cases.</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {demoTab === "verdict" && (
                <motion.div
                  key="verdict"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="space-y-4"
                >
                  <div className="flex items-center justify-between p-3 rounded-lg bg-red-50 border border-red-200 text-xs">
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-red-600" />
                      <span className="font-semibold text-red-800">
                        Reviewer Manager Verdict: REQUEST_CHANGES
                      </span>
                    </div>
                    <span className="font-mono text-red-700 font-semibold">2 Critical Blockers</span>
                  </div>

                  <div className="rounded-lg border border-surface-700 bg-surface-850 p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-slate-100">
                        Fix-Suggestion Agent · Proposed Remediation Patch
                      </span>
                      <span className="text-[10px] font-mono text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200 font-semibold">
                        Group-of-Three Extension
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">
                      Replaces vulnerable SQL string concatenation with safe parameterized execution. Validated via Python AST parse.
                    </p>
                    <div className="p-2.5 rounded bg-surface-900 border border-surface-700 font-mono text-[11px] space-y-0.5">
                      <div className="text-red-700">- cursor.execute(f"SELECT id FROM users WHERE username = '{'{username}'}'")</div>
                      <div className="text-emerald-700">+ cursor.execute("SELECT id FROM users WHERE username = %s", (username,))</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <span className="text-xs text-slate-400">
                      Status: {demoPatchApproved ? "Patch Approved by Reviewer" : "Awaiting Human-in-the-Loop Approval"}
                    </span>
                    <button
                      type="button"
                      onClick={() => setDemoPatchApproved(!demoPatchApproved)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        demoPatchApproved
                          ? "bg-emerald-600 text-white"
                          : "bg-surface-850 hover:bg-surface-800 border border-surface-700 text-slate-100"
                      }`}
                    >
                      <Check className="w-3.5 h-3.5" />
                      {demoPatchApproved ? "✓ Patch Approved" : "Approve Patch in Demo"}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </section>

      {/* How it Works - 3 Clean Steps */}
      <section className="py-12 px-6 border-y border-surface-700 bg-surface-900/60">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="text-center space-y-1">
            <h2 className="text-lg font-semibold text-slate-100">How the Review Pipeline Works</h2>
            <p className="text-xs text-slate-400">Deterministic orchestration with shared change state</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STEPS.map((s) => (
              <div
                key={s.step}
                className="rounded-xl bg-surface-900 border border-surface-700 p-5 space-y-2 relative shadow-xs hover:shadow-md transition-shadow"
              >
                <div className="text-xs font-mono font-semibold text-blue-600">{s.step}</div>
                <h3 className="text-sm font-semibold text-slate-100">{s.title}</h3>
                <p className="text-xs text-slate-400 leading-relaxed">{s.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 6 Specialized Agents Grid */}
      <section className="py-14 px-6">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="text-center space-y-1">
            <h2 className="text-lg font-semibold text-slate-100">6 Specialized Agent Modules</h2>
            <p className="text-xs text-slate-400">
              Each agent operates independently with dedicated static analysis tools
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {AGENTS.map((agent) => {
              const Icon = agent.icon;
              return (
                <div
                  key={agent.name}
                  className="rounded-xl bg-surface-900 border border-surface-700 p-4 space-y-3 flex flex-col justify-between shadow-xs hover:shadow-md transition-all hover:-translate-y-0.5"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`w-7 h-7 rounded-md flex items-center justify-center border ${agent.accent}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <h3 className="text-sm font-semibold text-slate-100">{agent.name}</h3>
                      </div>
                    </div>
                    <div className="text-[11px] font-medium text-slate-300">{agent.role}</div>
                    <p className="text-xs text-slate-400 leading-relaxed">{agent.description}</p>
                  </div>

                  <div className="pt-2 border-t border-surface-700/60">
                    <div className="text-[10px] font-mono text-slate-400 flex flex-wrap gap-1">
                      {agent.tools.map((t) => (
                        <span key={t} className="px-1.5 py-0.5 rounded bg-surface-850 border border-surface-700">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-surface-700 py-6 px-6 bg-surface-900/80 text-xs text-slate-400">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <div>
            <span className="font-medium text-slate-100">Automated Code Review Board</span> · Group 14 (CSE476)
          </div>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <a
              href="https://github.com/abhishekchauhan1365/AUTOMATED-CODE-REVIEW-BOARD"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-100 transition-colors"
            >
              GitHub Repo
            </a>
            <Link to="/login" className="hover:text-slate-100 transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
