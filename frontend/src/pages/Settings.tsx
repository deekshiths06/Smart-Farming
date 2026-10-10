import { useEffect, useState } from "react";
import {
  BadgeCheck,
  CalendarDays,
  Info,
  Mail,
  MapPinned,
  Phone,
  Settings as SettingsIcon,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useFields } from "../hooks/useFields";
import { api } from "../services/api";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Skeleton } from "../components/ui/Skeleton";

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export default function Settings() {
  const { user } = useAuth();
  const { fields } = useFields();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    void api
      .get<HealthResponse>("/health")
      .then((response) => {
        if (!cancelled) setHealth(response.data);
      })
      .catch(() => {
        if (!cancelled) setHealth(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const initials = (user?.name ?? "AN")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  const confirmedCount = fields.filter((field) => field.location_confirmed).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="The real details ANNADATA has on file for your account — nothing invented."
        icon={<SettingsIcon className="h-5 w-5" />}
      />

      <div className="rounded-panel border border-border bg-surface shadow-card">
        <div className="border-b border-border p-6">
          <div className="flex items-center gap-4">
            <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-forest-800 text-lg font-bold text-white">
              {initials}
            </span>
            <div className="min-w-0">
              <h2 className="truncate text-xl font-bold tracking-tight text-ink">{user?.name}</h2>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <StatusBadge tone={user?.is_active === false ? "neutral" : "success"} dot>
                  {user?.is_active === false ? "Inactive" : "Active account"}
                </StatusBadge>
                <StatusBadge tone={user?.role === "admin" ? "brand" : "info"}>
                  {user?.role === "admin" ? "Administrator" : "Farmer"}
                </StatusBadge>
              </div>
            </div>
          </div>
        </div>

        <dl className="divide-y divide-border">
          <div className="flex items-center gap-3 px-6 py-4">
            <Mail className="h-4 w-4 shrink-0 text-ink-muted" />
            <dt className="w-32 shrink-0 text-sm text-ink-muted">Email</dt>
            <dd className="min-w-0 truncate text-sm font-medium text-ink">{user?.email ?? "—"}</dd>
          </div>
          <div className="flex items-center gap-3 px-6 py-4">
            <Phone className="h-4 w-4 shrink-0 text-ink-muted" />
            <dt className="w-32 shrink-0 text-sm text-ink-muted">Phone</dt>
            <dd className="min-w-0 truncate text-sm font-medium text-ink">{user?.phone ?? "—"}</dd>
          </div>
          <div className="flex items-center gap-3 px-6 py-4">
            <UserRound className="h-4 w-4 shrink-0 text-ink-muted" />
            <dt className="w-32 shrink-0 text-sm text-ink-muted">Account ID</dt>
            <dd className="min-w-0 font-mono text-sm font-medium text-ink">{user?.id ?? "—"}</dd>
          </div>
          <div className="flex items-center gap-3 px-6 py-4">
            <CalendarDays className="h-4 w-4 shrink-0 text-ink-muted" />
            <dt className="w-32 shrink-0 text-sm text-ink-muted">Session</dt>
            <dd className="min-w-0 text-sm font-medium text-ink">
              Signed in on this browser
            </dd>
          </div>
        </dl>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-panel border border-border bg-surface p-6 shadow-card">
          <h2 className="flex items-center gap-2 text-base font-bold tracking-tight text-ink">
            <MapPinned className="h-4 w-4 text-brand-700" /> Your record
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-muted">
            A summary of the fields saved to your account.
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-card bg-surface-sunken p-4">
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                Fields on record
              </dt>
              <dd className="mt-1 text-2xl font-bold tracking-tight text-ink">{fields.length}</dd>
            </div>
            <div className="rounded-card bg-surface-sunken p-4">
              <dt className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                GPS confirmed
              </dt>
              <dd className="mt-1 text-2xl font-bold tracking-tight text-ink">{confirmedCount}</dd>
            </div>
          </dl>
        </div>

        <div className="space-y-6">
          <div className="rounded-panel border border-border bg-surface p-6 shadow-card">
            <h2 className="flex items-center gap-2 text-base font-bold tracking-tight text-ink">
              <Info className="h-4 w-4 text-brand-700" /> About profile editing
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">
              Profile editing isn't available yet, so this page shows the true details ANNADATA has
              on file for your account — it reflects the server, not a form. When account editing
              ships, it will appear right here.
            </p>
          </div>

          <div className="rounded-panel border border-border bg-surface p-6 shadow-card">
            <h2 className="flex items-center gap-2 text-base font-bold tracking-tight text-ink">
              <ShieldCheck className="h-4 w-4 text-brand-700" /> Privacy
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">
              Your field records are private to your account. Only you — and administrators
              managing the system — can see them.
            </p>
            <p className="mt-3 flex items-center gap-1.5 text-xs text-ink-muted">
              <BadgeCheck className="h-3.5 w-3.5" /> Signed in as {user?.email ?? "you"}
            </p>
          </div>

          <div className="rounded-panel border border-border bg-surface p-6 shadow-card">
            <h2 className="text-base font-bold tracking-tight text-ink">About</h2>
            {health ? (
              <dl className="mt-3 space-y-1.5 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <dt className="text-ink-muted">{health.service}</dt>
                  <dd className="font-medium text-ink-soft">v{health.version}</dd>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <dt className="text-ink-muted">API status</dt>
                  <dd>
                    <StatusBadge tone="success" dot>
                      {health.status}
                    </StatusBadge>
                  </dd>
                </div>
              </dl>
            ) : (
              <div className="mt-3 space-y-2">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}