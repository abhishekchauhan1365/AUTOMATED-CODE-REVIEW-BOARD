import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  Activity,
  History,
  LayoutDashboard,
  LogOut,
  PlusCircle,
  ShieldCheck,
} from "lucide-react";
import { fetchHealth } from "../services/api";
import { getStoredUser, logoutUser } from "../services/auth";
import type { UserProfile } from "../types/auth";
import type { HealthInfo } from "../types/review";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/new", label: "New Review", icon: PlusCircle, end: false },
  { to: "/history", label: "Review History", icon: History, end: false },
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
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex bg-surface-950 text-slate-100">
      {/* Clean Sidebar */}
      <aside className="w-56 shrink-0 border-r border-surface-700 bg-surface-900 flex flex-col">
        {/* Brand header */}
        <Link
          to="/"
          className="h-14 px-4 border-b border-surface-700 flex items-center gap-2.5 hover:bg-surface-850/60 transition-colors"
        >
          <div className="w-7 h-7 rounded-md bg-blue-600/20 border border-blue-500/40 flex items-center justify-center">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <div className="text-xs font-semibold tracking-tight text-slate-100">
              Code Review Board
            </div>
            <div className="text-[10px] font-mono text-slate-400">
              CSE476
            </div>
          </div>
        </Link>

        {/* User Badge */}
        {user && (
          <div className="p-3 border-b border-surface-700/80 bg-surface-950/40 flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-6 h-6 rounded-full bg-blue-600/30 border border-blue-500/50 flex items-center justify-center text-blue-300 font-semibold text-xs shrink-0">
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
        )}

        {/* Navigation Items */}
        <nav className="p-3 space-y-1 flex-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
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

        {/* Minimal Engine Status */}
        <div className="p-3 border-t border-surface-700 text-[11px] flex items-center justify-between text-slate-400">
          <span className="flex items-center gap-1.5 font-mono text-[10px]">
            <Activity className="w-3 h-3 text-emerald-400" />
            Semantic Kernel
          </span>
          <span className={`font-mono text-[10px] ${health ? "text-emerald-400" : "text-red-400"}`}>
            {health ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b border-surface-700 bg-surface-900/70 px-6 flex items-center justify-between">
          <div className="text-xs text-slate-400 font-mono">
            Automated Code Review Pipeline
          </div>
          <div className="flex items-center gap-3">
            <NavLink
              to="/new"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-xs font-medium text-white transition-colors"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              New Review
            </NavLink>
          </div>
        </header>

        <main className="flex-1 p-6 max-w-6xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
