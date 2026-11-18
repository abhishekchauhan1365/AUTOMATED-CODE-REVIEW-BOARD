import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  KeyRound,
  LogIn,
  ShieldCheck,
  Sparkles,
  User,
} from "lucide-react";
import { loginUser } from "../services/auth";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // If user was redirected from a protected page, navigate back there after login
  const redirectTarget = (location.state as { from?: { pathname?: string } })?.from?.pathname || "/dashboard";

  const handleLogin = async (u: string, p: string) => {
    setError(null);
    setLoading(true);
    try {
      await loginUser(u, p);
      navigate(redirectTarget, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to sign in.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    handleLogin(username, password);
  };

  const handleQuickDemo = () => {
    handleLogin("demo", "demo123");
  };

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 flex flex-col justify-center items-center px-4 py-8">
      <div className="w-full max-w-sm space-y-5">
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
              Authentication required to access multi-agent reviews.
            </p>
          </div>

          {/* Quick 1-Click Demo Login Button */}
          <button
            type="button"
            onClick={handleQuickDemo}
            disabled={loading}
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

          {error && (
            <div className="rounded-md bg-red-500/10 border border-red-500/30 p-2.5 text-xs text-red-300">
              {error}
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
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="demo or your username"
                  className="w-full rounded-md bg-surface-950 border border-surface-700 pl-8 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Password
              </label>
              <div className="relative">
                <KeyRound className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="demo123"
                  className="w-full rounded-md bg-surface-950 border border-surface-700 pl-8 pr-3 py-2 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-md bg-surface-800 hover:bg-surface-750 border border-surface-700 text-xs font-medium text-slate-200 transition-colors"
            >
              <LogIn className="w-3.5 h-3.5" />
              {loading ? "Signing In..." : "Sign In"}
            </button>
          </form>

          <div className="pt-1 text-center text-[11px] text-slate-500">
            Demo account: <span className="font-mono text-slate-400">demo</span> / <span className="font-mono text-slate-400">demo123</span>
          </div>
        </div>
      </div>
    </div>
  );
}
