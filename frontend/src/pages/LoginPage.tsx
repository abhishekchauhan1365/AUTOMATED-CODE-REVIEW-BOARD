import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  LogIn,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User,
  UserCheck,
  Wifi,
  WifiOff,
} from "lucide-react";
import { fetchHealth } from "../services/api";
import { loginUser } from "../services/auth";

const SQLI_PATTERN = /('|--|;|\/\*|\*\/|union\s+select|select\s+\*|or\s+1=1)/i;
const MAX_LOCAL_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

const DEMO_PERSONAS = [
  {
    id: "demo",
    username: "demo",
    password: "demo123",
    name: "Dr. Sarah Chen",
    role: "Lead Review Architect",
    avatar: "SC",
    badge: "border-blue-200 bg-blue-50 text-blue-700",
  },
  {
    id: "admin",
    username: "admin",
    password: "admin",
    name: "Alex Rivera",
    role: "System & Governance Admin",
    avatar: "AR",
    badge: "border-purple-200 bg-purple-50 text-purple-700",
  },
];

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [selectedPersona, setSelectedPersona] = useState<string>("demo");
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo123");
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockActive, setCapsLockActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Safety Net 1: Backend connectivity check
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  // Safety Net 2: Rate limit & lockout timer
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lockoutRemaining, setLockoutRemaining] = useState(0);

  // Safety Net 3: Input injection detection
  const [injectionWarning, setInjectionWarning] = useState(false);

  const redirectTarget =
    (location.state as { from?: { pathname?: string } })?.from?.pathname || "/dashboard";

  // Check backend health on mount
  useEffect(() => {
    fetchHealth()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  // Lockout countdown timer
  useEffect(() => {
    if (lockoutRemaining <= 0) return;
    const interval = setInterval(() => {
      setLockoutRemaining((prev) => {
        if (prev <= 1) {
          setFailedAttempts(0);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [lockoutRemaining]);

  // Handle key events to detect Caps Lock
  const handlePasswordKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.getModifierState) {
      setCapsLockActive(e.getModifierState("CapsLock"));
    }
  };

  const handleUsernameChange = (val: string) => {
    setUsername(val);
    setSelectedPersona("custom");
    if (SQLI_PATTERN.test(val)) {
      setInjectionWarning(true);
    } else {
      setInjectionWarning(false);
    }
  };

  const selectPersona = (p: typeof DEMO_PERSONAS[0]) => {
    setSelectedPersona(p.id);
    setUsername(p.username);
    setPassword(p.password);
    setError(null);
    setInjectionWarning(false);
  };

  const executeLogin = async (u: string, p: string) => {
    if (lockoutRemaining > 0) return;

    const cleanUser = u.trim();
    const cleanPass = p.trim();

    if (!cleanUser || !cleanPass) {
      setError("Please provide both username and password.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await loginUser(cleanUser, cleanPass);
      setFailedAttempts(0);
      navigate(redirectTarget, { replace: true });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to sign in.";
      setError(msg);

      const nextAttempts = failedAttempts + 1;
      setFailedAttempts(nextAttempts);

      if (nextAttempts >= MAX_LOCAL_ATTEMPTS || msg.includes("Lockout")) {
        setLockoutRemaining(LOCKOUT_SECONDS);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    executeLogin(username, password);
  };

  const activePersonaObj = DEMO_PERSONAS.find((p) => p.id === selectedPersona);

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col justify-center items-center px-4 py-10 relative">
      {/* Soft background ambient accents */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-blue-100/30 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-4xl space-y-5 relative z-10">
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-100 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Home
          </Link>
          <span className="text-[11px] font-mono text-slate-400">CSE476 · Group 14</span>
        </div>

        {/* Safety Net Banner: Backend Connectivity Guard */}
        {backendOnline === false && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl bg-red-50 border border-red-200 p-3.5 text-xs text-red-800 flex items-start gap-2.5 shadow-sm"
          >
            <WifiOff className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">Backend Server Offline</div>
              <p className="text-[11px] text-red-700/80 mt-0.5">
                Cannot reach <code>http://127.0.0.1:8000/api/health</code>. Please start the FastAPI backend service to authenticate.
              </p>
            </div>
          </motion.div>
        )}

        {/* Dynamic Dual-Panel Auth Container */}
        <div className="rounded-2xl bg-surface-900 border border-surface-700 shadow-xl overflow-hidden grid grid-cols-1 md:grid-cols-12">
          {/* Left Column: Form & Persona Switcher */}
          <div className="md:col-span-7 p-6 sm:p-8 space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center shadow-xs">
                  <ShieldCheck className="w-5 h-5 text-blue-600" />
                </div>
                <span className="text-xs font-mono font-semibold text-blue-700 uppercase tracking-wide">
                  Reviewer Portal
                </span>
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-100">
                Sign In to Review Board
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Select an authorized reviewer persona or enter your credentials.
              </p>
            </div>

            {/* Persona Switcher Tabs */}
            <div className="space-y-2">
              <label className="block text-[11px] font-mono uppercase tracking-wider text-slate-400">
                Select Authorized Demo Role
              </label>
              <div className="grid grid-cols-2 gap-2">
                {DEMO_PERSONAS.map((p) => {
                  const isSelected = selectedPersona === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => selectPersona(p)}
                      className={`p-2.5 rounded-xl border text-left transition-all ${
                        isSelected
                          ? "bg-blue-50/70 border-blue-300 ring-1 ring-blue-400/30 shadow-xs"
                          : "bg-surface-850 hover:bg-surface-800 border-surface-700"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-blue-600 text-white font-bold text-[10px] flex items-center justify-center shrink-0">
                          {p.avatar}
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-slate-100 truncate">
                            {p.name}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400 truncate">
                            {p.username}
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Active Persona Banner */}
            {activePersonaObj && (
              <div className="p-2.5 rounded-lg bg-surface-850 border border-surface-700 flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-600" />
                  <span className="text-slate-300">
                    Signing in as <strong>{activePersonaObj.name}</strong> ({activePersonaObj.role})
                  </span>
                </div>
                <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${activePersonaObj.badge}`}>
                  VERIFIED
                </span>
              </div>
            )}

            {/* Safety Net Alert: Brute Force Lockout */}
            {lockoutRemaining > 0 && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="rounded-lg bg-amber-50 border border-amber-300 p-3 text-xs text-amber-800 flex items-center gap-2"
              >
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                <div>
                  <strong>Security Lockout:</strong> {lockoutRemaining}s cooldown active to protect against brute-force attacks.
                </div>
              </motion.div>
            )}

            {/* General Error Alert */}
            {error && lockoutRemaining === 0 && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-lg bg-red-50 border border-red-300 p-3 text-xs text-red-800 flex items-start gap-2"
              >
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <div>{error}</div>
              </motion.div>
            )}

            {/* Safety Net Alert: SQLi / Script Pattern Warning */}
            {injectionWarning && (
              <div className="rounded-lg bg-amber-50 border border-amber-300 p-2.5 text-[11px] text-amber-800 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                <span>SQL/Script pattern detected. Input is sanitized by backend guardrails.</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Username or Email
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    maxLength={128}
                    disabled={lockoutRemaining > 0}
                    value={username}
                    onChange={(e) => handleUsernameChange(e.target.value)}
                    placeholder="demo or username"
                    className="w-full rounded-lg bg-surface-850 border border-surface-700 pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-surface-900 transition-all disabled:opacity-50"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-medium text-slate-300">
                    Password
                  </label>
                  {capsLockActive && (
                    <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 font-mono flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> CAPS LOCK IS ON
                    </span>
                  )}
                </div>
                <div className="relative">
                  <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    maxLength={128}
                    disabled={lockoutRemaining > 0}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={handlePasswordKey}
                    onKeyUp={handlePasswordKey}
                    placeholder="••••••••"
                    className="w-full rounded-lg bg-surface-850 border border-surface-700 pl-9 pr-9 py-2 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-surface-900 transition-all disabled:opacity-50"
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-200 transition-colors"
                    title={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || lockoutRemaining > 0}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-medium text-white transition-all shadow-sm hover:shadow-md cursor-pointer"
              >
                <LogIn className="w-3.5 h-3.5" />
                {loading ? "Authenticating..." : lockoutRemaining > 0 ? `Locked (${lockoutRemaining}s)` : "Sign In to Dashboard"}
                <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
              </button>
            </form>
          </div>

          {/* Right Column: Live Multi-Agent Telemetry & Safety Status */}
          <div className="md:col-span-5 bg-surface-850/70 border-t md:border-t-0 md:border-l border-surface-700 p-6 sm:p-8 flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400 uppercase tracking-wider text-[10px]">
                  System Telemetry
                </span>
                <span className="flex items-center gap-1.5 text-emerald-700 font-semibold text-[11px]">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Live Engine
                </span>
              </div>

              {/* Status Modules */}
              <div className="space-y-2.5">
                <div className="p-3 rounded-xl bg-surface-900 border border-surface-700 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                    <span className="flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-blue-600" /> Orchestration
                    </span>
                    <span className="text-[10px] font-mono text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                      Semantic Kernel
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Fan-Out / Fan-In coordination with SharedChangeState actor runtime.
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-surface-900 border border-surface-700 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                    <span className="flex items-center gap-1.5">
                      <Shield className="w-3.5 h-3.5 text-emerald-600" /> Enterprise Guardrails
                    </span>
                    <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                      Active
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Shannon entropy secret redaction, AST patch validation &amp; Human approval gate.
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-surface-900 border border-surface-700 shadow-xs space-y-1">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-100">
                    <span className="flex items-center gap-1.5">
                      <Server className="w-3.5 h-3.5 text-purple-600" /> Dual Persistence
                    </span>
                    <span className="text-[10px] font-mono text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200">
                      SQLite + JSONL
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Immutable event audit trail with full replay capability.
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-surface-700/60 text-[11px] font-mono text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>Group:</span>
                <span className="text-slate-100 font-semibold">Group 14 (CSE476)</span>
              </div>
              <div className="flex justify-between">
                <span>Security Net:</span>
                <span className="text-emerald-700 font-semibold">Rate-Limited &amp; Masked</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
