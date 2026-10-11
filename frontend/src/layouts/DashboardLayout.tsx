import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  CloudSun,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  MapPin,
  MapPinned,
  Microscope,
  Menu as MenuIcon,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  ShieldCheck,
  Wheat,
  X,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useFields } from "../hooks/useFields";
import { Logo } from "../components/ui/Logo";
import { Dropdown } from "../components/ui/Dropdown";
import { cn } from "../lib/cn";
import { landStructure } from "../lib/labels";

interface NavEntry {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

const NAV: NavEntry[] = [
  { to: "/dashboard", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/fields", label: "My Fields", icon: MapPinned },
  { to: "/weather", label: "Weather Intelligence", icon: CloudSun },
  { to: "/soil", label: "Soil Intelligence", icon: FlaskConical },
  { to: "/crops", label: "Crop Recommendations", icon: Wheat },
  { to: "/actions", label: "Action Planner", icon: ClipboardList },
  { to: "/disease", label: "Crop Disease", icon: Microscope },
  { to: "/settings", label: "Settings", icon: Settings },
];

const SECTION_TITLES: Record<string, string> = {
  "/dashboard": "Overview",
  "/fields": "My Fields",
  "/weather": "Weather Intelligence",
  "/soil": "Soil Intelligence",
  "/crops": "Crop Recommendations",
  "/actions": "Action Planner",
  "/disease": "Crop Disease",
  "/settings": "Settings",
  "/admin": "Admin",
};

function sectionFor(pathname: string): string {
  if (pathname.startsWith("/fields/")) return "My Fields";
  return SECTION_TITLES[pathname] ?? "Dashboard";
}

function initialsOf(name?: string | null): string {
  if (!name) return "F";
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function NavCell({
  item,
  collapsed,
  onNavigate,
}: {
  item: NavEntry;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      end={item.end}
      onClick={onNavigate}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400",
          collapsed && "justify-center px-0",
          isActive
            ? "bg-brand-400 text-forest-950 shadow-soft"
            : "text-white/70 hover:bg-white/10 hover:text-white"
        )
      }
    >
      <Icon className="h-[18px] w-[18px] shrink-0" />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </NavLink>
  );
}

interface SidebarProps {
  collapsed: boolean;
  user: { name: string | null | undefined; email: string | null | undefined; role: string | undefined };
  onToggleCollapse?: () => void;
  onNavigate?: () => void;
  onClose?: () => void;
  onLogout: () => void;
}

function SidebarContent({ collapsed, user, onToggleCollapse, onNavigate, onClose, onLogout }: SidebarProps) {
  return (
    <div className="relative flex h-full flex-col bg-forest-950">
      <div className="hero-gradient-left pointer-events-none absolute inset-0 opacity-60" />
      <div className="relative flex h-16 shrink-0 items-center justify-between border-b border-white/10 px-4">
        {collapsed ? (
          <Link to="/dashboard" onClick={onNavigate} aria-label="ANNADATA home" className="mx-auto">
            <Logo inverted showWordmark={false} size="sm" />
          </Link>
        ) : (
          <>
            <Link to="/dashboard" onClick={onNavigate} aria-label="ANNADATA home">
              <Logo inverted size="sm" />
            </Link>
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close menu"
                className="rounded-md p-1.5 text-white/70 hover:bg-white/10 lg:hidden"
              >
                <X className="h-5 w-5" />
              </button>
            )}
          </>
        )}
      </div>

      <nav className="thin-scroll relative flex-1 overflow-y-auto px-3 py-4">
        <p
          className={cn(
            "px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-white/40",
            collapsed && "sr-only"
          )}
        >
          Workspace
        </p>
        <div className="space-y-1">
          {NAV.map((item) => (
            <NavCell key={item.to} item={item} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
          {user.role === "admin" && (
            <NavCell
              item={{ to: "/admin", label: "Admin", icon: ShieldCheck }}
              collapsed={collapsed}
              onNavigate={onNavigate}
            />
          )}
        </div>
      </nav>

      <div className="relative shrink-0 space-y-1 border-t border-white/10 p-3">
        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            title="Toggle sidebar"
            className={cn(
              "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-white/60 transition-colors hover:bg-white/10 hover:text-white",
              collapsed && "justify-center px-0"
            )}
          >
            {collapsed ? <PanelLeftOpen className="h-[18px] w-[18px]" /> : <PanelLeftClose className="h-[18px] w-[18px]" />}
            {!collapsed && <span>Collapse sidebar</span>}
          </button>
        )}
        <button
          type="button"
          onClick={onLogout}
          title={collapsed ? "Log out" : undefined}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-white/60 transition-colors hover:bg-red-500/15 hover:text-red-300",
            collapsed && "justify-center px-0"
          )}
        >
          <LogOut className="h-[18px] w-[18px]" />
          {!collapsed && <span>Log out</span>}
        </button>
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { fields, selectedField, setSelectedFieldId } = useFields();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("annadata:sidebar") === "collapsed";
    } catch {
      return false;
    }
  });

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const toggleCollapsed = () => {
    setCollapsed((value) => {
      const next = !value;
      try {
        localStorage.setItem("annadata:sidebar", next ? "collapsed" : "expanded");
      } catch {
        /* storage unavailable */
      }
      return next;
    });
  };

  const section = sectionFor(location.pathname);
  const profileUser = {
    name: user?.name,
    email: user?.email,
    role: user?.role,
  };

  return (
    <div className="min-h-screen bg-canvas">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden border-r border-forest-900 transition-[width] duration-200 lg:block",
          collapsed ? "w-[76px]" : "w-64"
        )}
      >
        <SidebarContent
          collapsed={collapsed}
          user={profileUser}
          onToggleCollapse={toggleCollapsed}
          onLogout={handleLogout}
        />
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-forest-950/60 backdrop-blur-[2px] lg:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              aria-hidden="true"
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 w-72 border-r border-forest-900 shadow-pop lg:hidden"
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "tween", duration: 0.22, ease: "easeOut" }}
            >
              <SidebarContent
                collapsed={false}
                user={profileUser}
                onNavigate={() => setMobileOpen(false)}
                onClose={() => setMobileOpen(false)}
                onLogout={handleLogout}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div
        className={cn(
          "flex min-h-screen flex-col transition-[padding] duration-200",
          collapsed ? "lg:pl-[76px]" : "lg:pl-64"
        )}
      >
        <header className="sticky top-0 z-20 border-b border-border bg-canvas/90 shadow-soft backdrop-blur">
          <div className="flex h-16 items-center gap-2 px-4 sm:gap-3 sm:px-6">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation menu"
              className="rounded-lg p-2 text-ink-soft transition-colors hover:bg-surface-sunken lg:hidden"
            >
              <MenuIcon className="h-5 w-5" />
            </button>

            <div className="flex min-w-0 items-center gap-1.5 text-sm">
              <span className="hidden text-ink-muted sm:inline">Home</span>
              <ChevronRight className="hidden h-3.5 w-3.5 text-ink-muted/60 sm:inline" aria-hidden="true" />
              <span className="truncate font-semibold text-ink">{section}</span>
            </div>

            <div className="ml-auto flex items-center gap-2">
              {fields.length > 0 && (
                <Dropdown
                  label="Select field"
                  align="right"
                  panelClassName="w-72"
                  trigger={
                    <span className="flex items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2 text-sm transition-colors hover:bg-surface-muted">
                      <MapPin className="h-4 w-4 shrink-0 text-brand-700" />
                      <span className="max-w-[140px] truncate font-medium text-ink sm:max-w-[200px]">
                        {selectedField ? selectedField.field_name : "Fields"}
                      </span>
                      <ChevronDown className="h-4 w-4 shrink-0 text-ink-muted" />
                    </span>
                  }
                >
                  {(close) => (
                    <>
                      <p className="px-3 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                        Switch field
                      </p>
                      <div className="thin-scroll max-h-72 overflow-y-auto">
                        {fields.map((field) => {
                          const active = field.id === selectedField?.id;
                          const placeLabel = landStructure(field as unknown as {
                            locality?: string | null;
                            sub_district?: string | null;
                            district?: string | null;
                            state?: string | null;
                            country?: string | null;
                          });
                          return (
                            <button
                              key={field.id}
                              type="button"
                              onClick={() => {
                                setSelectedFieldId(field.id);
                                close();
                              }}
                              className={cn(
                                "flex w-full items-start gap-2.5 px-3 py-2 text-left text-sm transition-colors hover:bg-surface-muted",
                                active && "bg-brand-50"
                              )}
                            >
                              <span
                                className={cn(
                                  "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                                  active ? "bg-brand-600" : "bg-border-strong"
                                )}
                              />
                              <span className="min-w-0 flex-1">
                                <span className={cn("block truncate font-medium", active ? "text-brand-800" : "text-ink")}>
                                  {field.field_name}
                                </span>
                                <span className="block truncate text-[11px] text-ink-muted">{placeLabel}</span>
                              </span>
                              {active && <Check className="mt-0.5 h-4 w-4 shrink-0 text-brand-700" />}
                            </button>
                          );
                        })}
                      </div>
                    </>
                  )}
                </Dropdown>
              )}

              {user && (
                <Dropdown
                  label="Account menu"
                  align="right"
                  panelClassName="w-72"
                  trigger={
                    <span className="flex items-center gap-2 rounded-lg border border-border-strong bg-surface py-1.5 pl-1.5 pr-2 transition-colors hover:bg-surface-muted">
                      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-forest-800 text-xs font-bold text-white">
                        {initialsOf(user.name)}
                      </span>
                      <span className="hidden text-left md:block">
                        <span className="block max-w-[140px] truncate text-sm font-medium leading-tight text-ink">
                          {user.name}
                        </span>
                        <span className="block text-[11px] leading-tight text-ink-muted">
                          {user.role === "admin" ? "Admin" : "Farmer"}
                        </span>
                      </span>
                      <ChevronDown className="hidden h-4 w-4 text-ink-muted md:block" />
                    </span>
                  }
                >
                  {(close) => (
                    <>
                      <div className="border-b border-border px-3 pb-2 pt-1">
                        <p className="truncate text-sm font-semibold text-ink">{user.name}</p>
                        <p className="truncate text-xs text-ink-muted">{user.email}</p>
                      </div>
                      <div className="pt-1">
                        <Link
                          to="/settings"
                          onClick={close}
                          className="flex items-center gap-2.5 px-3 py-2 text-sm text-ink-soft transition-colors hover:bg-surface-muted"
                        >
                          <Settings className="h-4 w-4" /> Account settings
                        </Link>
                        <button
                          type="button"
                          onClick={() => {
                            close();
                            handleLogout();
                          }}
                          className="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50"
                        >
                          <LogOut className="h-4 w-4" /> Log out
                        </button>
                      </div>
                    </>
                  )}
                </Dropdown>
              )}
            </div>
          </div>
        </header>

        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:py-8"
        >
          <Outlet />
        </motion.main>
      </div>
    </div>
  );
}