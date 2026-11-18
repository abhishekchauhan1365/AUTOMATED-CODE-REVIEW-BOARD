import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  Cpu,
  Eye,
  EyeOff,
  GitBranch,
  KeyRound,
  Lock,
  LogIn,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User,
  UserCheck,
  WifiOff,
  Wrench,
} from "lucide-react";
import { fetchHealth } from "../services/api";
import { loginUser } from "../services/auth";

const SQLI_PATTERN = /('|--|;|\/\*|\*\/|union\s+select|select\s+\*|or\s+1=1)/i;
const MAX_LOCAL_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

const SLIDES = [
  {
    title: "Autonomous Multi-Agent Review",
    subtitle: "Diff, Style, Security & Test-Coverage agents coordinate concurrently via Microsoft Semantic Kernel.",
    tag: "Fan-Out / Fan-In",
  },
  {
    title: "Zero-Leak Secret Redaction",
    subtitle: "High-entropy API keys and passwords are masked automatically before reaching logs or shared state.",
    tag: "Enterprise Safety",
  },
  {
    title: "Automated Fix Suggestions",
    subtitle: "Isolates top findings, extracts AST context, and generates syntactically validated unified diff patches.",
    tag: "Human-in-the-Loop",
  },
];

const DEMO_ACCOUNTS = [
  {
    id: "demo",
    username: "demo",
    password: "demo123",
    name: "Dr. Sarah Chen",
    role: "Lead Review Architect",
    avatar: "SC",
    color: "bg-blue-600",
  },
  {
    id: "admin",
    username: "admin",
    password: "admin",
    name: "Alex Rivera",
    role: "System & Governance Admin",
    avatar: "AR",
    color: "bg-purple-600",
  },
];

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [activeSlide, setActiveSlide] = useState(0);
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("demo123");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockActive, setCapsLockActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Safety Nets
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [lockoutRemaining, setLockoutRemaining] = useState(0);
  const [injectionWarning, setInjectionWarning] = useState(false);

  const redirectTarget =
    (location.state as { from?: { pathname?: string } })?.from?.pathname || "/dashboard";

  // Cycle slides automatically
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveSlide((prev) => (prev + 1) % SLIDES.length);
    }, 4500);
    return () => clearInterval(timer);
  }, []);

  // Pre-flight backend health check
  useEffect(() => {
    fetchHealth()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  // Cooldown countdown timer
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

  const handlePasswordKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.getModifierState) {
      setCapsLockActive(e.getModifierState("CapsLock"));
    }
  };

  const handleUsernameChange = (val: string) => {
    setUsername(val);
    setInjectionWarning(SQLI_PATTERN.test(val));
  };

  const selectPreset = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
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

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex items-center justify-center p-4 sm:p-6 lg:p-10 selection:bg-blue-100 selection:text-blue-900">
      {/* Outer Split Card Container */}
      <div className="w-full max-w-5xl rounded-3xl bg-surface-900 border border-surface-700 shadow-2xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[640px]">
        {/* LEFT COLUMN: Modern Visual Showcase Card (Inspired by reference layout) */}
        <div className="lg:col-span-5 p-3 sm:p-4 flex flex-col">
          <div className="w-full h-full rounded-2xl relative overflow-hidden bg-gradient-to-br from-[#1E293B] via-[#0F172A] to-[#020617] text-white p-7 sm:p-8 flex flex-col justify-between shadow-inner">
            {/* Ambient decorative glowing orb */}
            <div className="absolute top-1/4 right-0 w-72 h-72 bg-blue-500/20 rounded-full blur-[80px] pointer-events-none" />
            <div className="absolute bottom-1/4 left-0 w-64 h-64 bg-indigo-500/20 rounded-full blur-[70px] pointer-events-none" />

            {/* Top row: Brand & "Back to website" pill button */}
            <div className="relative z-10 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-white/10 backdrop-blur-md border border-white/20 flex items-center justify-center">
                  <ShieldCheck className="w-5 h-5 text-blue-400" />
                </div>
                <span className="font-semibold text-sm tracking-tight text-white font-mono">
                  ReviewBoard
                </span>
              </div>

              <Link
                to="/"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/15 text-xs text-white/90 transition-all font-mono"
              >
                Back to website <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            {/* Middle Graphic: Live Multi-Agent Fan-Out Visual */}
            <div className="relative z-10 my-8 py-4 space-y-3">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/20 border border-blue-400/30 text-[11px] font-mono text-blue-300">
                <Sparkles className="w-3 h-3 text-blue-400" />
                <span>{SLIDES[activeSlide].tag}</span>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={activeSlide}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-2"
                >
                  <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white leading-snug">
                    {SLIDES[activeSlide].title}
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-sm">
                    {SLIDES[activeSlide].subtitle}
                  </p>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Bottom Row: Tagline & Carousel Indicator Bars */}
            <div className="relative z-10 pt-4 border-t border-white/10 space-y-3">
              <div className="text-xs text-slate-400 font-mono flex items-center justify-between">
                <span>CSE476 · Group 14</span>
                <span className="text-emerald-400 font-semibold">Semantic Kernel Live</span>
              </div>

              {/* Interactive Carousel Indicator Bars */}
              <div className="flex items-center gap-2 pt-1">
                {SLIDES.map((_, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setActiveSlide(idx)}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      activeSlide === idx ? "w-8 bg-blue-400" : "w-2 bg-white/30 hover:bg-white/50"
                    }`}
                    title={`Slide ${idx + 1}`}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Clean, Elevated Sign In Form */}
        <div className="lg:col-span-7 p-7 sm:p-10 lg:p-12 flex flex-col justify-center space-y-6">
          {/* Header */}
          <div className="space-y-1.5">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-100">
              Sign In to Your Account
            </h1>
            <p className="text-xs sm:text-sm text-slate-400">
              Welcome back! Access your multi-agent review pipeline and fix suggestions.
            </p>
          </div>

          {/* Safety Net Banner: Backend Connectivity Guard */}
          {backendOnline === false && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl bg-red-50 border border-red-200 p-3.5 text-xs text-red-800 flex items-start gap-2.5 shadow-xs"
            >
              <WifiOff className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold">Backend Offline</div>
                <p className="text-[11px] text-red-700/80 mt-0.5">
                  Cannot connect to <code>http://127.0.0.1:8000</code>. Ensure the FastAPI service is running.
                </p>
              </div>
            </motion.div>
          )}

          {/* Safety Net: Brute-Force Lockout Active */}
          {lockoutRemaining > 0 && (
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="rounded-xl bg-amber-50 border border-amber-300 p-3 text-xs text-amber-800 flex items-center gap-2.5"
            >
              <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
              <div>
                <strong>Security Lockout:</strong> {lockoutRemaining}s cooldown remaining to protect against brute-force attempts.
              </div>
            </motion.div>
          )}

          {/* General Error Message */}
          {error && lockoutRemaining === 0 && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl bg-red-50 border border-red-300 p-3 text-xs text-red-800 flex items-start gap-2"
            >
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div>{error}</div>
            </motion.div>
          )}

          {/* Safety Net: SQLi Warning */}
          {injectionWarning && (
            <div className="rounded-xl bg-amber-50 border border-amber-300 p-2.5 text-xs text-amber-800 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>SQL/Script pattern detected. Automatically sanitized by backend.</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Username or Email
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  maxLength={128}
                  disabled={lockoutRemaining > 0}
                  value={username}
                  onChange={(e) => handleUsernameChange(e.target.value)}
                  placeholder="demo or your username"
                  className="w-full rounded-xl bg-surface-850 border border-surface-700 pl-10 pr-3.5 py-2.5 text-sm text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all disabled:opacity-50"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-slate-300">
                  Password
                </label>
                {capsLockActive && (
                  <span className="text-[10px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-mono flex items-center gap-1 font-semibold">
                    <AlertTriangle className="w-3 h-3 text-amber-600" /> CAPS LOCK ON
                  </span>
                )}
              </div>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
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
                  className="w-full rounded-xl bg-surface-850 border border-surface-700 pl-10 pr-10 py-2.5 text-sm text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all disabled:opacity-50"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-slate-400 hover:text-slate-200 transition-colors"
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me Checkbox */}
            <div className="flex items-center justify-between text-xs">
              <label className="flex items-center gap-2 cursor-pointer text-slate-300">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500"
                />
                <span>Remember reviewer session</span>
              </label>
              <button
                type="button"
                onClick={() => selectPreset("demo", "demo123")}
                className="text-blue-600 hover:text-blue-500 font-medium font-mono text-[11px]"
              >
                Reset to demo credentials
              </button>
            </div>

            {/* Primary Sign In Button */}
            <button
              type="submit"
              disabled={loading || lockoutRemaining > 0}
              className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-semibold text-white transition-all shadow-md shadow-blue-500/10 hover:shadow-lg cursor-pointer"
            >
              <LogIn className="w-4 h-4" />
              {loading ? "Authenticating..." : lockoutRemaining > 0 ? `Locked (${lockoutRemaining}s)` : "Sign In to Dashboard"}
              <ArrowRight className="w-4 h-4 ml-0.5" />
            </button>
          </form>

          {/* Divider */}
          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-surface-700" />
            <span className="flex-shrink mx-3 text-[11px] font-mono text-slate-400 uppercase">
              Or Instant Demo Profiles
            </span>
            <div className="flex-grow border-t border-surface-700" />
          </div>

          {/* One-Click Demo Role Cards (Inspired by the Google / Apple social login buttons in the reference layout) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {DEMO_ACCOUNTS.map((acc) => {
              const isActive = username === acc.username;
              return (
                <button
                  key={acc.id}
                  type="button"
                  onClick={() => selectPreset(acc.username, acc.password)}
                  className={`flex items-center gap-3 p-3 rounded-xl border text-left transition-all ${
                    isActive
                      ? "bg-blue-50/70 border-blue-300 ring-1 ring-blue-400/40 shadow-xs"
                      : "bg-surface-850 hover:bg-surface-800 border-surface-700"
                  }`}
                >
                  <div className={`w-8 h-8 rounded-lg ${acc.color} text-white font-bold text-xs flex items-center justify-center shrink-0`}>
                    {acc.avatar}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-100 truncate">
                      {acc.name}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400 truncate">
                      {acc.role}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
