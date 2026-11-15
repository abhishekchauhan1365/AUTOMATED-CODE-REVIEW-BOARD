import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Cpu,
  FileCode2,
  GitBranch,
  GitCommit,
  GitCompare,
  GitMerge,
  GitPullRequest,
  Lock,
  LogIn,
  Play,
  RotateCcw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  User,
  Wrench,
} from "lucide-react";
import { getStoredUser, logoutUser } from "../services/auth";
import type { UserProfile } from "../types/auth";

const AGENT_ROSTER = [
  {
    number: 1,
    name: "Diff Agent",
    role: "Structural & Risk Analysis",
    description:
      "Parses unified diffs, extracts modified files, analyzes AST syntax, and detects potentially risky structural modifications.",
    tools: ["parse_git_diff", "analyze_code_structure"],
    badge: "border-sky-500/30 text-sky-400 bg-sky-500/10",
  },
  {
    number: 2,
    name: "Style Agent",
    role: "Linter & Complexity Analysis",
    description:
      "Runs Ruff static checks, calculates Radon cyclomatic complexity, identifies code duplication, and enforces naming standards.",
    tools: ["run_linter (Ruff)", "calculate_complexity (Radon)"],
    badge: "border-emerald-500/30 text-emerald-400 bg-emerald-500/10",
  },
  {
    number: 3,
    name: "Security Agent",
    role: "Secrets & Vulnerability Audit",
    description:
      "Scans for hardcoded credentials with automatic redaction, flags SQL injection patterns, dangerous shell calls, and Bandit static findings.",
    tools: ["scan_for_secrets", "run_security_analysis (Bandit)"],
    badge: "border-red-500/30 text-red-400 bg-red-500/10",
  },
  {
    number: 4,
    name: "Test-Coverage Agent",
    role: "Test Mapping & Gaps",
    description:
      "Discovers test files, maps production symbols to test suites, evaluates coverage without unsafe execution, and proposes missing test scenarios.",
    tools: ["discover_test_files", "analyze_test_coverage"],
    badge: "border-amber-500/30 text-amber-400 bg-amber-500/10",
  },
  {
    number: 5,
    name: "Reviewer Manager",
    role: "Central Orchestrator",
    description:
      "Dispatches parallel fan-out via Semantic Kernel, deduplicates findings, applies severity ranking, and issues an APPROVE or REQUEST_CHANGES decision.",
    tools: ["deduplicate_findings", "rank_findings", "generate_review_report"],
    badge: "border-indigo-500/30 text-indigo-400 bg-indigo-500/10",
  },
  {
    number: 6,
    name: "Fix-Suggestion Agent",
    role: "Automated Patch Generation",
    description:
      "Group-of-three extension. Selects highest-severity finding, extracts context, generates a unified diff patch, and statically validates syntax.",
    tools: ["extract_code_context", "generate_unified_patch", "validate_patch"],
    badge: "border-purple-500/30 text-purple-400 bg-purple-500/10",
  },
];

export function LandingPage() {
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
  };

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col selection:bg-blue-500/30">
      {/* Top Navbar */}
      <header className="h-16 border-b border-surface-700/80 bg-surface-900/80 backdrop-blur-md sticky top-0 z-50 px-6">
        <div className="max-w-7xl mx-auto h-full flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <span className="text-sm font-semibold tracking-tight text-slate-100">
                Automated Code Review Board
              </span>
              <span className="ml-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 border border-surface-700 text-slate-400">
                CSE476 · Group 14
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-xs text-slate-400">
            <a href="#architecture" className="hover:text-slate-200 transition-colors">
              Architecture
            </a>
            <a href="#agents" className="hover:text-slate-200 transition-colors">
              Specialist Agents
            </a>
            <a href="#safety" className="hover:text-slate-200 transition-colors">
              Safety Guardrails
            </a>
            <a href="#rubric" className="hover:text-slate-200 transition-colors">
              Academic Deliverables
            </a>
          </nav>

          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-300 font-mono hidden sm:inline">
                  {user.name} ({user.role.split(" ")[0]})
                </span>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="px-2.5 py-1.5 rounded-md border border-surface-700 bg-surface-800 hover:bg-surface-700 text-xs text-slate-300"
                >
                  Sign Out
                </button>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
                >
                  Dashboard <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            ) : (
              <>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-surface-700 bg-surface-850 hover:bg-surface-800 text-xs font-medium text-slate-200 transition-colors"
                >
                  <LogIn className="w-3.5 h-3.5 text-slate-400" />
                  Sign In
                </Link>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
                >
                  Launch Board <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-16 pb-20 px-6 overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />

        <div className="max-w-5xl mx-auto text-center space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-900 border border-blue-500/30 text-xs text-blue-300 font-mono">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>Microsoft Semantic Kernel · 6-Agent Fan-Out / Fan-In Architecture</span>
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-100 max-w-4xl mx-auto leading-tight">
            Autonomous Code Review &amp; Intelligent Fix Recommendations
          </h1>

          <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-relaxed">
            A production-grade multi-agent platform for CSE476. Submits code changes across four
            parallel specialists, consolidates findings, enforces merge safety rules, and generates
            statically validated unified diff patches.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-colors shadow-lg shadow-blue-600/20"
            >
              <Play className="w-4 h-4 fill-white" />
              Launch Review Board
            </Link>
            <Link
              to="/new"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface-900 hover:bg-surface-850 border border-surface-700 text-sm font-medium text-slate-200 transition-colors"
            >
              <GitCompare className="w-4 h-4 text-slate-400" />
              New Code Review
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-900 hover:bg-surface-850 border border-surface-700 text-sm font-medium text-slate-300 transition-colors"
            >
              <User className="w-4 h-4 text-slate-400" />
              Sign In Demo
            </Link>
          </div>

          {/* Interactive Hero Visual */}
          <div className="pt-8 max-w-4xl mx-auto">
            <div className="rounded-xl bg-surface-900 border border-surface-700 shadow-2xl overflow-hidden text-left font-mono text-xs">
              <div className="h-9 px-4 border-b border-surface-700 bg-surface-950/80 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-red-500/60 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-yellow-500/60 inline-block" />
                  <span className="w-3 h-3 rounded-full bg-green-500/60 inline-block" />
                  <span className="text-slate-400 text-[11px] ml-2">
                    semantic_kernel_orchestration.log
                  </span>
                </div>
                <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  PIPELINE LIVE
                </span>
              </div>
              <div className="p-4 space-y-2 bg-[#07090E] text-slate-300 overflow-x-auto text-[11px]">
                <div className="text-slate-500">
                  # 1. Reviewer Manager creates SharedChangeState &amp; initiates Fan-Out
                </div>
                <div className="text-blue-400">
                  &gt; ConcurrentOrchestration.invoke(members=[DiffAgent, StyleAgent, SecurityAgent, TestCoverageAgent])
                </div>
                <div className="text-emerald-400">
                  &#10003; [Diff Agent] Analyzed 1 diff hunk · 2 functions · 2 risky AST touches
                </div>
                <div className="text-emerald-400">
                  &#10003; [Style Agent] Ruff linter executed · Radon cyclomatic complexity inspected
                </div>
                <div className="text-red-400">
                  &#9888; [Security Agent] Flagged 1 secret (redacted: sk-************890) · SQLi f-string · eval()
                </div>
                <div className="text-amber-400">
                  &#9888; [Test-Coverage] 0 test files submitted · 2 untested symbols mapped
                </div>
                <div className="text-slate-500 pt-1">
                  # 2. Fan-In: Reviewer Manager deduplicates &amp; issues decision
                </div>
                <div className="text-purple-300">
                  &gt; Final Merge Decision: <span className="text-red-400 font-bold">REQUEST_CHANGES</span> (4 CRITICAL blockers)
                </div>
                <div className="text-slate-500 pt-1">
                  # 3. Agent 6 (Fix-Suggestion) generates validated unified diff patch:
                </div>
                <div className="text-slate-400 pl-4 border-l border-emerald-500/40">
                  <span className="text-red-400">- STRIPE_SECRET = &quot;sk-************890&quot;</span>
                  <br />
                  <span className="text-emerald-400">+ STRIPE_SECRET = os.getenv(&quot;STRIPE_SECRET&quot;, &quot;&quot;)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Key Metrics Strip */}
      <section className="py-8 border-y border-surface-700/80 bg-surface-900/50">
        <div className="max-w-6xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center font-mono">
          <div>
            <div className="text-2xl font-bold text-slate-100">6 Agents</div>
            <div className="text-xs text-slate-400 mt-1">Separate Python Modules</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-blue-400">Parallel</div>
            <div className="text-xs text-slate-400 mt-1">Fan-Out / Fan-In Pipeline</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-emerald-400">14 Tools</div>
            <div className="text-xs text-slate-400 mt-1">Deterministic AST &amp; Scanners</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-amber-400">Human Gate</div>
            <div className="text-xs text-slate-400 mt-1">Explicit Patch Approval</div>
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section id="architecture" className="py-20 px-6 max-w-6xl mx-auto space-y-12">
        <div className="text-center space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-blue-400">
            System Topology
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100">
            Fan-Out / Fan-In Multi-Agent Architecture
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl mx-auto">
            Built strictly on Microsoft Semantic Kernel primitives, separating code review into
            specialized parallel domains before synthesis.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-xl bg-surface-900 border border-surface-700 p-6 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <GitBranch className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100">1. Parallel Fan-Out</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upon submission, the Reviewer Manager initializes a shared change-state and invokes the
              Diff, Style, Security, and Test-Coverage agents simultaneously using{" "}
              <code className="text-blue-300 font-mono">ConcurrentOrchestration</code>.
            </p>
          </div>

          <div className="rounded-xl bg-surface-900 border border-surface-700 p-6 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <GitMerge className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100">2. Fan-In Consolidation</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Findings from all four agents are aggregated into the shared change-state, deduplicated
              across overlapping lines/rules, ranked by severity, and evaluated against merge
              decision rules.
            </p>
          </div>

          <div className="rounded-xl bg-surface-900 border border-surface-700 p-6 space-y-3">
            <div className="w-9 h-9 rounded-lg bg-purple-600/20 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <Wrench className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100">3. Validated Fix Patch</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The Fix-Suggestion Agent targets the highest-severity actionable finding, generates a
              unified diff patch, verifies syntax via AST, and locks download behind explicit user
              approval.
            </p>
          </div>
        </div>
      </section>

      {/* Specialist Agents Roster */}
      <section id="agents" className="py-20 px-6 bg-surface-900/40 border-t border-surface-700/80">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-2">
            <span className="text-xs font-mono uppercase tracking-wider text-emerald-400">
              Agent Roster
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100">
              Six Independent Agent Modules
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl mx-auto">
              Every agent is encapsulated in its own module with its own Semantic Kernel plugin and calls
              at least two real deterministic Python tools.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {AGENT_ROSTER.map((agent) => (
              <div
                key={agent.name}
                className="rounded-xl bg-surface-900 border border-surface-700 p-5 space-y-3 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-500">Agent {agent.number}</span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${agent.badge}`}>
                      {agent.role}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-slate-100">{agent.name}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{agent.description}</p>
                </div>

                <div className="pt-2 border-t border-surface-700/60 space-y-1.5">
                  <span className="text-[11px] font-mono text-slate-400">Real Python Tools:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {agent.tools.map((t) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded bg-surface-950 border border-surface-700 text-[10px] font-mono text-slate-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Safety & Reliability Section */}
      <section id="safety" className="py-20 px-6 max-w-6xl mx-auto space-y-12">
        <div className="text-center space-y-2">
          <span className="text-xs font-mono uppercase tracking-wider text-red-400">
            Safety Guardrails
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100">
            Zero-Execution Security Model
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 max-w-2xl mx-auto">
            Built to review untrusted code safely without risking execution in host or server environments.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-xl bg-surface-900 border border-surface-700 p-6 space-y-2">
            <Shield className="w-6 h-6 text-emerald-400" />
            <h3 className="text-sm font-semibold text-slate-100">Never Execute Untrusted Code</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Analyzers run in isolated temp environments using AST parsing, Ruff, and Bandit. Submitted
              code is never imported, invoked, or executed.
            </p>
          </div>

          <div className="rounded-xl bg-surface-900 border border-surface-700 p-6 space-y-2">
            <Lock className="w-6 h-6 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-100">Automatic Credential Redaction</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Discovered API keys, tokens, and passwords are masked before entering reports, UI feeds,
              SQLite, or JSONL run logs.
            </p>
          </div>

          <div className="rounded-xl bg-surface-900 border border-surface-700 p-6 space-y-2">
            <CheckCircle2 className="w-6 h-6 text-purple-400" />
            <h3 className="text-sm font-semibold text-slate-100">Human-in-the-Loop Patch Gate</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Proposed patches are locked behind an explicit user approval button. The API returns HTTP
              403 until the developer approves download.
            </p>
          </div>
        </div>
      </section>

      {/* Academic Rubric Section */}
      <section id="rubric" className="py-16 px-6 bg-surface-900/60 border-t border-surface-700/80">
        <div className="max-w-4xl mx-auto text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-surface-800 border border-surface-700 text-xs font-mono text-slate-300">
            <span>Course: CSE476 · Agentic AI and Intelligent Automation</span>
          </div>

          <h2 className="text-2xl font-bold text-slate-100">
            Group 14 Academic Project Implementation
          </h2>

          <p className="text-xs text-slate-400 max-w-xl mx-auto leading-relaxed">
            Strictly satisfies all Group 14 specifications: Microsoft Semantic Kernel orchestration,
            six independent agent modules, two real tools per agent, append-only JSONL run logs,
            SQLite persistence, automated test scenarios, and the executable demo notebook.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
            >
              Open Review Board <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-850 hover:bg-surface-800 border border-surface-700 text-xs font-medium text-slate-300 transition-colors"
            >
              Sign In Demo Accounts
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-surface-700 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-slate-400" />
            <span>Automated Code Review Board · CSE476 Group 14</span>
          </div>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <Link to="/dashboard" className="hover:text-slate-300">
              Dashboard
            </Link>
            <Link to="/new" className="hover:text-slate-300">
              New Review
            </Link>
            <Link to="/history" className="hover:text-slate-300">
              History
            </Link>
            <Link to="/login" className="hover:text-slate-300">
              Sign In
            </Link>
            <a href="/api/health" target="_blank" rel="noreferrer" className="hover:text-slate-300">
              API Health
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

