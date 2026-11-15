import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  Compass,
  GitPullRequest,
  History,
  Home,
  LayoutDashboard,
  LogIn,
  LogOut,
  PlusCircle,
  ShieldCheck,
  User,
} from "lucide-react";
import { fetchHealth } from "../services/api";
import { getStoredUser, logoutUser } from "../services/auth";
import type { UserProfile } from "../types/auth";
import type { HealthInfo } from "../types/review";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/new", label: "New Review", icon: PlusCircle, end: false },
  { to: "/history", label: "Review History", icon: History, end: false },
  { to: "/", label: "Overview & Specs", icon: Home, end: true },
];

export function DashboardLayout() {
  const navigate = useNavigate();
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
    setUser(getStoredUser());
  }, []);

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
    navigate("/");
  };

  return (
    <div className="min-h-screen flex bg-surface-950 text-slate-100">
      <aside className="w-60 shrink-0 border-r border-surface-700 bg-surface-900 flex flex-col">
        <Link
          to="/"
          className="h-14 px-4 border-b border-surface-700 flex items-center gap-2.5 hover:bg-surface-850/60 transition-colors"
        >
          <div className="w-7 h-7 rounded-md bg-blue-600/20 border border-blue-500/40 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
          </div>
          <div className="leading-tight">
            <div className="text-xs font-semibold tracking-tight text-slate-100">
              Code Review Board
            </div>
            <div className="text-[10px] font-mono text-slate-400">
              CSE476 · Multi-Agent
            </div>
          </div>
        </Link>

        {/* User Profile Pill in Sidebar */}
        <div className="p-3 border-b border-surface-700/80 bg-surface-950/40">
          {user ? (
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-full bg-blue-600/30 border border-blue-500/50 flex items-center justify-center text-blue-300 font-semibold text-xs shrink-0">
                  {user.name.charAt(0)}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-slate-200 truncate">{user.name}</div>
                  <div className="text-[10px] font-mono text-slate-400 truncate">{user.role}</div>
                </div>
              </div>
              <button
                type="button"
                onClick={handleLogout}
                className="p-1 rounded text-slate-400 hover:text-red-400 hover:bg-surface-800 transition-colors"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-surface-850 hover:bg-surface-800 border border-surface-700/80 text-xs text-slate-300 transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-slate-400" />
                Sign In
              </span>
              <span className="text-[10px] font-mono text-blue-400">Demo &rarr;</span>
            </Link>
          )}
        </div>

        <nav className="p-3 space-y-1 flex-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-surface-800 text-slate-100 border border-surface-700"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-850"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-3 border-t border-surface-700 text-[11px] space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              Backend API
            </span>
            <span className={`font-mono ${health ? "text-emerald-400" : "text-red-400"}`}>
              {health ? "ONLINE" : "OFFLINE"}
            </span>
          </div>
          {health && (
            <div className="rounded bg-surface-950 border border-surface-700 p-2 font-mono text-[10px] text-slate-400 space-y-1">
              <div className="flex justify-between">
                <span>Engine:</span>
                <span className="text-slate-200">{health.framework}</span>
              </div>
              <div className="flex justify-between">
                <span>Mode:</span>
                <span className={health.demo_mode_default ? "text-amber-300" : "text-emerald-400"}>
                  {health.demo_mode_default ? "DEMO" : "GROQ LIVE"}
                </span>
              </div>
            </div>
          )}
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-surface-700 bg-surface-900/70 px-6 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
            <GitPullRequest className="w-3.5 h-3.5 text-slate-400" />
            <span>Fan-Out / Fan-In Automated Multi-Agent Review Pipeline</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="text-xs text-slate-400 hover:text-slate-200 font-mono hidden sm:inline"
            >
              &larr; Landing Page
            </Link>
            <NavLink
              to="/new"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              New Code Review
            </NavLink>
          </div>
        </header>

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
