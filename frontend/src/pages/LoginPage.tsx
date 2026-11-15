import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  KeyRound,
  Lock,
  LogIn,
  ShieldCheck,
  User,
} from "lucide-react";
import { loginUser } from "../services/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await loginUser(username, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign in.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError(null);
    setLoading(true);
    try {
      await loginUser(u, p);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Quick sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col justify-center items-center px-4 py-12 relative overflow-hidden">
      {/* Background ambient accents */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        <div className="flex items-center justify-between">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Landing Page
          </Link>
          <span className="text-[11px] font-mono text-slate-500">CSE476 · Group 14</span>
        </div>

        <div className="rounded-xl bg-surface-900 border border-surface-700 shadow-2xl p-7 space-y-6">
          <div className="space-y-1.5 text-center">
            <div className="w-10 h-10 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center mx-auto mb-3">
              <ShieldCheck className="w-6 h-6 text-blue-400" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-100">
              Sign In to Review Board
            </h1>
            <p className="text-xs text-slate-400">
              Access the multi-agent code analysis dashboard, execution trace, and patch generator.
            </p>
          </div>

          {/* Quick Demo Logins */}
          <div className="space-y-2">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider text-center">
              One-Click Demo Accounts
            </div>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin("reviewer@cse476.edu", "review123")}
                className="flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-surface-950/80 border border-surface-700 hover:border-blue-500/50 hover:bg-surface-850 transition-colors text-left group"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-200 group-hover:text-blue-300">
                    Dr. Sarah Chen
                  </div>
                  <div className="text-[11px] font-mono text-slate-400">
                    Lead Review Architect · reviewer@cse476.edu
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 shrink-0" />
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin("developer@cse476.edu", "dev123")}
                className="flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-surface-950/80 border border-surface-700 hover:border-blue-500/50 hover:bg-surface-850 transition-colors text-left group"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-200 group-hover:text-blue-300">
                    Alex Rivera
                  </div>
                  <div className="text-[11px] font-mono text-slate-400">
                    Senior Software Engineer · developer@cse476.edu
                  </div>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-blue-400 shrink-0" />
              </button>
            </div>
          </div>

          <div className="relative flex py-1 items-center">
            <div className="flex-grow border-t border-surface-700/70" />
            <span className="flex-shrink mx-3 text-[11px] font-mono text-slate-500 uppercase">
              Or custom sign in
            </span>
            <div className="flex-grow border-t border-surface-700/70" />
          </div>

          {error && (
            <div className="rounded-md bg-red-500/10 border border-red-500/30 p-2.5 text-xs text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Username or Email
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. reviewer@cse476.edu or your name"
                  className="w-full rounded-md bg-surface-950 border border-surface-700 pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-md bg-surface-950 border border-surface-700 pl-9 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-medium text-white transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              {loading ? "Signing In..." : "Sign In to Dashboard"}
            </button>
          </form>

          <div className="pt-2 text-center text-[11px] text-slate-500 space-y-1">
            <p>
              Guest mode is also supported. You can explore without an account.
            </p>
            <Link to="/dashboard" className="text-blue-400 hover:text-blue-300 underline font-mono">
              Continue as Guest Reviewer &rarr;
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

