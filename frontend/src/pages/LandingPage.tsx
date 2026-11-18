import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Cpu,
  FileCode2,
  GitBranch,
  GitCompare,
  GitPullRequest,
  Lock,
  LogIn,
  LogOut,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";
import { getStoredUser, logoutUser } from "../services/auth";
import type { UserProfile } from "../types/auth";

const AGENTS = [
  {
    name: "Diff Agent",
    role: "Structure & AST Analysis",
    description: "Parses unified diff hunks, extracts modified symbols, and flags structural syntax risks.",
    tools: ["parse_git_diff", "analyze_code_structure"],
    accent: "text-sky-400 bg-sky-500/10 border-sky-500/20",
    icon: GitCompare,
  },
  {
    name: "Style Agent",
    role: "Linter & Complexity Audit",
    description: "Runs Ruff static linter, calculates Radon cyclomatic complexity, and checks code style.",
    tools: ["run_linter (Ruff)", "calculate_complexity (Radon)"],
    accent: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    icon: FileCode2,
  },
  {
    name: "Security Agent",
    role: "Secrets & Vulnerability Scan",
    description: "Detects secrets with auto-redaction, flags SQLi patterns, shell injections, and Bandit flaws.",
    tools: ["scan_for_secrets", "run_security_analysis (Bandit)"],
    accent: "text-red-400 bg-red-500/10 border-red-500/20",
    icon: ShieldAlert,
  },
  {
    name: "Test-Coverage Agent",
    role: "Test Mapping & Test Gap Detection",
    description: "Maps changed functions to test suites, audits test coverage, and proposes test cases.",
    tools: ["discover_test_files", "analyze_test_coverage"],
    accent: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    icon: CheckCircle2,
  },
  {
    name: "Reviewer Manager",
    role: "Fan-In Orchestrator & Verdict",
    description: "Coordinates parallel execution via Semantic Kernel, deduplicates findings, and decides APPROVE / REQUEST_CHANGES.",
    tools: ["deduplicate_findings", "rank_findings", "generate_review_report"],
    accent: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    icon: Cpu,
  },
  {
    name: "Fix-Suggestion Agent",
    role: "Automated Patch Generation",
    description: "Group-of-three extension. Analyzes highest-severity finding and generates a validated unified diff patch.",
    tools: ["extract_code_context", "generate_unified_patch", "validate_patch"],
    accent: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    icon: Wrench,
  },
];

const STEPS = [
  {
    step: "01",
    title: "Submit Code Change",
    description: "Provide a unified Git diff or upload code files. Initialize SharedChangeState with metadata.",
  },
  {
    step: "02",
    title: "Concurrent Fan-Out",
    description: "Diff, Style, Security, and Test-Coverage agents run simultaneously using dedicated static analysis tools.",
  },
  {
    step: "03",
    title: "Consolidated Verdict & Fix",
    description: "Reviewer Manager deduplicates findings, assigns merge recommendation, and generates a concrete patch.",
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
      <header className="h-16 border-b border-surface-700/80 bg-surface-900/90 backdrop-blur-md sticky top-0 z-50 px-6">
        <div className="max-w-6xl mx-auto h-full flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <span className="text-sm font-semibold tracking-tight text-slate-100">
                Automated Code Review Board
              </span>
              <span className="ml-2 text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-800 border border-surface-700 text-slate-400">
                CSE476
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-300 font-mono hidden sm:inline">
                  {user.name}
                </span>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
                >
                  Dashboard <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md border border-surface-700 bg-surface-800 hover:bg-surface-750 text-xs text-slate-300"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign Out</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors shadow-sm"
              >
                <LogIn className="w-3.5 h-3.5" />
                Sign In
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="pt-16 pb-16 px-6 text-center">
        <div className="max-w-3xl mx-auto space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-900 border border-surface-700 text-xs text-blue-400 font-mono">
            <Sparkles className="w-3.5 h-3.5 text-blue-400" />
            <span>Microsoft Semantic Kernel · Fan-Out / Fan-In Architecture</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-slate-100 leading-tight">
            Automated Multi-Agent Code Review Board
          </h1>

          <p className="text-sm sm:text-base text-slate-400 leading-relaxed max-w-2xl mx-auto">
            Parallel specialist agents inspect your code for structural changes, style standards,
            security vulnerabilities, and test coverage gaps — delivering a consolidated verdict and fix patch.
          </p>

          <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-colors shadow-md shadow-blue-600/20"
                >
                  Go to Dashboard <ArrowRight className="w-4 h-4" />
                </Link>
                <Link
                  to="/new"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-900 hover:bg-surface-850 border border-surface-700 text-sm font-medium text-slate-200 transition-colors"
                >
                  <GitCompare className="w-4 h-4 text-slate-400" />
                  New Review
                </Link>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white transition-colors shadow-md shadow-blue-600/20"
                >
                  <Lock className="w-4 h-4" />
                  Sign In to Access Board
                </Link>
                <a
                  href="https://github.com/abhishekchauhan1365/AUTOMATED-CODE-REVIEW-BOARD"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-900 hover:bg-surface-850 border border-surface-700 text-sm font-medium text-slate-300 transition-colors"
                >
                  <GitBranch className="w-4 h-4 text-slate-400" />
                  GitHub Repository
                </a>
              </>
            )}
          </div>
        </div>
      </section>

      {/* How it Works - 3 Clean Steps */}
      <section className="py-12 px-6 border-y border-surface-700/60 bg-surface-900/40">
        <div className="max-w-5xl mx-auto space-y-8">
          <div className="text-center space-y-1">
            <h2 className="text-lg font-semibold text-slate-100">How the Review Pipeline Works</h2>
            <p className="text-xs text-slate-400">Deterministic orchestration with shared change state</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {STEPS.map((s) => (
              <div
                key={s.step}
                className="rounded-xl bg-surface-900 border border-surface-700 p-5 space-y-2 relative"
              >
                <div className="text-xs font-mono font-semibold text-blue-400">{s.step}</div>
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
                  className="rounded-xl bg-surface-900 border border-surface-700 p-4 space-y-3 flex flex-col justify-between"
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

                  <div className="pt-2 border-t border-surface-800/80">
                    <div className="text-[10px] font-mono text-slate-400 flex flex-wrap gap-1">
                      {agent.tools.map((t) => (
                        <span key={t} className="px-1.5 py-0.5 rounded bg-surface-950 border border-surface-700">
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
      <footer className="mt-auto border-t border-surface-700/80 py-6 px-6 bg-surface-900/60 text-xs text-slate-400">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <div>
            <span className="font-medium text-slate-200">Automated Code Review Board</span> · Group 14 (CSE476)
          </div>
          <div className="flex items-center gap-4 font-mono text-[11px]">
            <a
              href="https://github.com/abhishekchauhan1365/AUTOMATED-CODE-REVIEW-BOARD"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-200 transition-colors"
            >
              GitHub Repo
            </a>
            <Link to="/login" className="hover:text-slate-200 transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
