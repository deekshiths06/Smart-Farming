import { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, ShieldCheck, Users } from "lucide-react";
import { api } from "../services/api";

interface AdminStats {
  application: { name: string; version: string };
  database: { engine: string };
  counts: {
    total_users: number;
    total_fields: number;
    farmers: number;
    admins: number;
    active_users: number;
    fields_with_location: number;
    fields_with_verified_soil: number;
  };
  recent_activity: { new_users_last_7_days: number; new_fields_last_7_days: number };
  checked_at: string;
}

interface DataSourceCheckResult {
  reachable: boolean | null;
  latency_ms: number | null;
  message: string;
}

export default function Admin() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [sources, setSources] = useState<Array<Record<string, unknown>> | null>(null);
  const [schema, setSchema] = useState<Record<string, string[]> | null>(null);
  const [checkResults, setCheckResults] = useState<Record<string, DataSourceCheckResult> | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [statsResponse, sourcesResponse, schemaResponse] = await Promise.all([
        api.get<AdminStats>("/api/admin/stats"),
        api.get<{ sources: Array<Record<string, unknown>> }>("/api/admin/data-sources"),
        api.get<{ tables: Record<string, string[]> }>("/api/admin/schema"),
      ]);
      setStats(statsResponse.data);
      setSources(sourcesResponse.data.sources);
      setSchema(schemaResponse.data.tables);
    } catch {
      setError("Admin data could not be loaded. Are you logged in as an admin?");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const runCheck = async () => {
    setChecking(true);
    setCheckResults(null);
    try {
      const response = await api.post<{ results: Record<string, DataSourceCheckResult> }>(
        "/api/admin/data-sources/check"
      );
      setCheckResults(response.data.results);
    } catch {
      setError("The connectivity check failed. Please try again.");
    } finally {
      setChecking(false);
    }
  };

  if (error && !stats) {
    return (
      <>
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">{error}</div>
      </>
    );
  }

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-900 text-white">
            <ShieldCheck className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Admin</h1>
            <p className="mt-0.5 text-sm text-gray-500">
              Real system values only — no invented statistics.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => void load()}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
          <button
            type="button"
            onClick={runCheck}
            disabled={checking}
            className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-60"
          >
            <Database className="h-3.5 w-3.5" />
            {checking ? "Checking…" : "Check data sources"}
          </button>
        </div>
      </div>

      {stats && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Total farmers" value={stats.counts.farmers} icon={<Users className="h-4 w-4" />} />
            <StatCard label="Total fields" value={stats.counts.total_fields} icon={<Database className="h-4 w-4" />} />
            <StatCard
              label="Fields with location"
              value={stats.counts.fields_with_location}
              icon={<ShieldCheck className="h-4 w-4" />}
            />
            <StatCard
              label="Fields with verified soil"
              value={stats.counts.fields_with_verified_soil}
              icon={<ShieldCheck className="h-4 w-4" />}
            />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Admins" value={stats.counts.admins} />
            <StatCard label="Active users" value={stats.counts.active_users} />
            <StatCard label="New users (7d)" value={stats.recent_activity.new_users_last_7_days} />
            <StatCard label="New fields (7d)" value={stats.recent_activity.new_fields_last_7_days} />
          </div>

          <p className="mt-3 text-xs text-gray-400">
            Database engine: {stats.database.engine} · {stats.application.name} v{stats.application.version} ·
            checked {new Date(stats.checked_at).toLocaleString()}
          </p>
        </>
      )}

      {checkResults && (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">
            Connectivity check (live probes)
          </h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {Object.entries(checkResults).map(([key, result]) => (
              <div key={key} className="rounded-lg border border-gray-200 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-800">{key}</span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      result.reachable
                        ? "bg-emerald-50 text-emerald-700"
                        : result.reachable === null
                          ? "bg-gray-100 text-gray-500"
                          : "bg-amber-50 text-amber-700"
                    }`}
                  >
                    {result.reachable === null ? "Unknown" : result.reachable ? "Reachable" : "Unreachable"}
                  </span>
                </div>
                {result.latency_ms !== null && (
                  <p className="mt-1 text-xs text-gray-400">{result.latency_ms} ms</p>
                )}
                <p className="mt-1 text-xs text-gray-500">{result.message}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Data sources</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs uppercase text-gray-400">
                <th className="py-2 pr-4">Source</th>
                <th className="py-2 pr-4">Purpose</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {(sources ?? []).map((source) => (
                <tr key={String(source.id)} className="border-b border-gray-50">
                  <td className="py-2.5 pr-4 font-medium text-gray-800">
                    {String(source.name)}
                    <span className="block text-[11px] font-normal text-gray-400">{String(source.endpoint ?? "—")}</span>
                  </td>
                  <td className="py-2.5 pr-4 text-gray-500">{String(source.purpose)}</td>
                  <td className="py-2.5 pr-4">
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        source.status === "configured"
                          ? "bg-emerald-50 text-emerald-700"
                          : source.status === "not_implemented"
                            ? "bg-gray-100 text-gray-500"
                            : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {String(source.status).replace("_", " ")}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {schema && (
        <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Database schema</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {Object.entries(schema).map(([table, columns]) => (
              <div key={table} className="rounded-lg border border-gray-200 p-3">
                <p className="font-mono text-xs font-semibold text-gray-800">{table}</p>
                <p className="mt-1 font-mono text-[11px] text-gray-400">{columns.join(", ")}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="flex items-center gap-1.5 text-xs text-gray-500">
        {icon} {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-gray-900">{value}</div>
    </div>
  );
}