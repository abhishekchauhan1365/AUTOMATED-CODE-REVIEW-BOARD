import { useEffect, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  LogIn,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User,
  WifiOff,
} from "lucide-react";
import { fetchHealth } from "../services/api";
import { loginUser } from "../services/auth";

const SQLI_PATTERN = /('|--|;|\/\*|\*\/|union\s+select|select\s+\*|or\s+1=1)/i;
const MAX_LOCAL_ATTEMPTS = 5;
const LOCKOUT_SECONDS = 30;

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
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
    if (SQLI_PATTERN.test(val)) {
      setInjectionWarning(true);
    } else {
      setInjectionWarning(false);
    }
  };

  const executeLogin = async (u: string, p: string) => {
    if (lockoutRemaining > 0) return;

    // Safety Net: sanitize whitespace
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

  const handleQuickDemo = (demoUser: string, demoPass: string) => {
    setUsername(demoUser);
    setPassword(demoPass);
    setError(null);
    setInjectionWarning(false);
    executeLogin(demoUser, demoPass);
  };

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col justify-center items-center px-4 py-8">
      <div className="w-full max-w-sm space-y-4">
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Home
          </Link>
          <span className="text-[11px] font-mono text-slate-500">CSE476 · Group 14</span>
        </div>

        {/* Safety Net Banner: Backend Connectivity Guard */}
        {backendOnline === false && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-3 text-xs text-red-300 flex items-start gap-2">
            <WifiOff className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">Backend Server Offline</div>
              <p className="text-[11px] text-red-400/80 mt-0.5">
                Cannot connect to <code>http://127.0.0.1:8000</code>. Ensure the FastAPI service is running.
              </p>
            </div>
          </div>
        )}

        {/* Login Box */}
        <div className="rounded-xl bg-surface-900 border border-surface-700 shadow-xl p-6 space-y-5">
          <div className="text-center space-y-1">
            <div className="w-9 h-9 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center mx-auto mb-2">
              <ShieldCheck className="w-5 h-5 text-blue-400" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-100">
              Sign In to Review Board
            </h1>
            <p className="text-xs text-slate-400">
              Protected workspace · Role-based multi-agent access
            </p>
          </div>

          {/* Quick 1-Click Demo Sign In */}
          <button
            type="button"
            onClick={() => handleQuickDemo("demo", "demo123")}
            disabled={loading || lockoutRemaining > 0}
            className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-medium text-white transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {loading ? "Signing in..." : "1-Click Demo Sign In"}
            <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </button>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-surface-700/60" />
            <span className="flex-shrink mx-3 text-[10px] font-mono text-slate-500 uppercase">
              Or sign in with credentials
            </span>
            <div className="flex-grow border-t border-surface-700/60" />
          </div>

          {/* Safety Net Alert: Brute Force Lockout */}
          {lockoutRemaining > 0 && (
            <div className="rounded-md bg-amber-50 border border-amber-300 p-2.5 text-xs text-amber-800 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
              <div>
                <strong>Security Lockout Active:</strong> {lockoutRemaining}s cooldown remaining to protect against brute-force attempts.
              </div>
            </div>
          )}

          {/* General Error Alert */}
          {error && lockoutRemaining === 0 && (
            <div className="rounded-md bg-red-50 border border-red-300 p-2.5 text-xs text-red-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <div>{error}</div>
            </div>
          )}

          {/* Safety Net Alert: SQLi / Script Pattern Warning */}
          {injectionWarning && (
            <div className="rounded-md bg-amber-50 border border-amber-300 p-2 text-[11px] text-amber-800 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
              <span>SQL/Script pattern detected. Input is sanitized by backend guardrails.</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Username
              </label>
              <div className="relative">
                <User className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  maxLength={128}
                  disabled={lockoutRemaining > 0}
                  value={username}
                  onChange={(e) => handleUsernameChange(e.target.value)}
                  placeholder="demo or reviewer email"
                  className="w-full rounded-md bg-surface-950 border border-surface-700 pl-8 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-medium text-slate-300">
                  Password
                </label>
                {capsLockActive && (
                  <span className="text-[10px] text-amber-400 font-mono flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> CAPS LOCK ON
                  </span>
                )}
              </div>
              <div className="relative">
                <KeyRound className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
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
                  className="w-full rounded-md bg-surface-950 border border-surface-700 pl-8 pr-9 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300 transition-colors"
                  title={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || lockoutRemaining > 0}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-surface-800 hover:bg-surface-750 disabled:opacity-50 border border-surface-700 text-xs font-medium text-slate-200 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              {loading ? "Signing In..." : lockoutRemaining > 0 ? `Locked (${lockoutRemaining}s)` : "Sign In"}
            </button>
          </form>

          {/* Quick Auto-Fill Safety Net */}
          <div className="pt-2 border-t border-surface-800/80">
            <div className="text-[10px] font-mono text-slate-500 uppercase tracking-wider text-center mb-1.5">
              Demo Credentials Safety Helper
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
              <button
                type="button"
                onClick={() => handleQuickDemo("demo", "demo123")}
                className="px-2 py-1.5 rounded bg-surface-950 hover:bg-surface-850 border border-surface-750 text-slate-300 text-center transition-colors"
              >
                demo / demo123
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo("admin", "admin")}
                className="px-2 py-1.5 rounded bg-surface-950 hover:bg-surface-850 border border-surface-750 text-slate-300 text-center transition-colors"
              >
                admin / admin
              </button>
            </div>
          </div>
        </div>

        {/* Security Footer Badge */}
        <div className="text-center text-[10px] font-mono text-slate-500 flex items-center justify-center gap-1.5">
          <Lock className="w-3 h-3 text-emerald-400" />
          <span>Protected by Rate-Limiting, Redaction &amp; SQLite Audit Trail</span>
        </div>
      </div>
    </div>
  );
}
