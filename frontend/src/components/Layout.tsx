import { Outlet, NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Compass,
  Search,
  Building2,
  FileText,
  TrendingUp,
  Star,
  BookOpen,
  Shield,
  Sparkles,
  ClipboardCheck,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/discovery", label: "Discovery", icon: Compass },
  { to: "/scanner", label: "Scanner", icon: Search },
  { to: "/hedgefunds", label: "Hedge Funds", icon: Building2 },
  { to: "/papers", label: "Research", icon: FileText },
  { to: "/macro", label: "Makro", icon: TrendingUp },
  { to: "/watchlist", label: "Watchlist", icon: Star },
  { to: "/journal", label: "Journal", icon: BookOpen },
  { to: "/portfolio-check", label: "Portfolio-Check", icon: ClipboardCheck },
  { to: "/risk", label: "Risiko", icon: Shield },
  { to: "/ai", label: "KI-Analyse", icon: Sparkles },
];

export function Layout() {
  return (
    <div className="flex h-screen bg-surface-subtle">
      <aside className="w-60 bg-surface border-r border-border flex flex-col shrink-0">
        <div className="px-6 py-5">
          <h1 className="text-lg font-bold text-ink tracking-tight">
            Trading<span className="text-accent">Intel</span>
          </h1>
          <p className="text-[10px] text-ink-tertiary mt-0.5 tracking-wide uppercase">Institutional Analysis</p>
        </div>
        <nav className="flex-1 px-3 space-y-0.5">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all ${
                  isActive
                    ? "bg-accent/[0.06] text-accent"
                    : "text-ink-secondary hover:text-ink hover:bg-surface-muted"
                }`
              }
            >
              <Icon size={16} strokeWidth={1.8} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-6 py-4 border-t border-border">
          <p className="text-[10px] text-ink-faint text-center">v1.0 — Keine Anlageberatung</p>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1440px] mx-auto px-8 py-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
