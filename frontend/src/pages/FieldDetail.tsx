import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CloudSun,
  Droplets,
  Info,
  MapPin,
  MapPinned,
  Pencil,
  RefreshCw,
  Sprout,
  Thermometer,
  Trash2,
  Wind,
} from "lucide-react";
import FieldMap from "../components/FieldMap";
import { fieldsApi } from "../services/fields";
import { formatArea, toCircleLngLat } from "../lib/geo";
import {
  AREA_SOURCE_LABELS,
  AREA_UNIT_LABELS,
  SOIL_STATUS_LABELS,
  WATER_AVAILABILITY_LABELS,
  WATER_SOURCE_LABELS,
  landStructure,
} from "../lib/labels";
import type { Field, WeatherResponse } from "../types/field";

function WeatherDetail({ fieldId }: { fieldId: number }) {
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setWeather(await fieldsApi.weather(fieldId));
    } catch {
      setWeather({
        status: "unavailable",
        message: "The weather service could not be reached right now.",
      });
    } finally {
      setLoading(false);
    }
  }, [fieldId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <p className="flex items-center gap-2 text-sm text-gray-500">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
        Fetching live weather…
      </p>
    );
  }

  if (weather?.status === "unavailable" || !weather?.weather) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
        <div className="text-sm text-amber-800">
          <p className="font-medium">Weather is not available right now.</p>
          <p className="mt-0.5 text-xs">
            {weather?.message ?? "The live weather service did not respond. Your field data is safe."}
          </p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-2 flex items-center gap-1 text-xs font-semibold text-amber-900 hover:text-amber-950"
          >
            <RefreshCw className="h-3 w-3" /> Try again
          </button>
        </div>
      </div>
    );
  }

  const values = weather.weather;
  return (
    <div>
      <p className="flex items-center gap-2 text-sm text-gray-500">
        <CloudSun className="h-4 w-4 text-brand-600" />
        Live conditions near your field (real weather service — not a guess)
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <WeatherStat
          icon={<Thermometer className="h-4 w-4" />}
          label="Temperature"
          value={values.temperature_2m !== null ? `${Math.round(values.temperature_2m)}°C` : "—"}
        />
        <WeatherStat
          icon={<Droplets className="h-4 w-4" />}
          label="Humidity"
          value={values.relative_humidity_2m !== null ? `${values.relative_humidity_2m}%` : "—"}
        />
        <WeatherStat
          icon={<CloudSun className="h-4 w-4" />}
          label="Rain (hourly)"
          value={values.precipitation !== null ? `${values.precipitation} mm` : "—"}
        />
        <WeatherStat
          icon={<Wind className="h-4 w-4" />}
          label="Wind"
          value={values.wind_speed_10m !== null ? `${values.wind_speed_10m} km/h` : "—"}
        />
      </dl>
      <p className="mt-4 text-xs text-gray-400">
        Source: {values.source} · Point {values.latitude.toFixed(3)}, {values.longitude.toFixed(3)} ·{" "}
        {values.observed_at
          ? `observed ${new Date(values.observed_at).toLocaleString()}`
          : "latest available observation"}
      </p>
    </div>
  );
}

function WeatherStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="flex items-center gap-1.5 text-xs text-gray-500">
        {icon} {label}
      </div>
      <div className="mt-1 text-lg font-semibold text-gray-900">{value}</div>
    </div>
  );
}

export default function FieldDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [field, setField] = useState<Field | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fieldsApi
      .get(id)
      .then(setField)
      .catch(() => setError("This field could not be found."));
  }, [id]);

  const handleDelete = async () => {
    if (!field) return;
    if (!window.confirm(`Delete “${field.field_name}”? This cannot be undone.`)) return;
    try {
      await fieldsApi.remove(field.id);
      navigate("/dashboard");
    } catch {
      setError("We could not delete the field. Please try again.");
    }
  };

  if (error) {
    return (
      <>
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          {error}
        </div>
      </>
    );
  }

  if (!field) {
    return (
      <>
        <p className="text-sm text-gray-400">Loading field…</p>
      </>
    );
  }

  const hasPosition = field.latitude !== null && field.longitude !== null;
  const mapPosition: [number, number] | undefined = hasPosition
    ? [field.latitude as number, field.longitude as number]
    : undefined;
  const polygon = field.boundary
    ? toCircleLngLat(field.boundary.coordinates[0].map((c) => [c[1], c[0]] as [number, number]))
    : undefined;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50"
            title="Back to my fields"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">{field.field_name}</h1>
            <p className="mt-0.5 text-sm text-gray-500">
              {landStructure(field as unknown as { locality?: string | null; sub_district?: string | null; district?: string | null; state?: string | null; country?: string | null })} · added{" "}
              {new Date(field.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/fields/${field.id}/edit`}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
          >
            <Pencil className="h-3.5 w-3.5" /> Edit
          </Link>
          <button
            type="button"
            onClick={handleDelete}
            className="flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
          >
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </button>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_360px]">
        {/* Left: map + sections */}
        <div className="space-y-5">
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              <MapPin className="h-4 w-4 text-brand-600" /> Location
            </h2>
            {mapPosition ? (
              <div className="mt-3">
                <FieldMap position={mapPosition} polygon={polygon} heightClass="h-[280px]" zoomControl={false} />
                <p className="mt-2 text-xs text-gray-500">
                  Marker:{" "}
                  <span className="font-mono font-semibold text-gray-800">
                    {field.latitude?.toFixed(6)}, {field.longitude?.toFixed(6)}
                  </span>
                  {field.location_accuracy !== null && (
                    <>
                      {" "}· GPS accuracy ≈ <span className="font-semibold">{Math.round(field.location_accuracy)} m</span>
                    </>
                  )}
                </p>
              </div>
            ) : (
              <p className="mt-3 flex items-center gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                <Info className="h-4 w-4 shrink-0" /> This field has no confirmed location yet.
              </p>
            )}
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span
                className={`rounded-full px-2.5 py-0.5 font-medium ${
                  field.location_confirmed ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                }`}
              >
                {field.location_confirmed ? "Location confirmed" : "Location pending confirmation"}
              </span>
              <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-gray-600">
                Area name {field.locality || field.district || field.state ? "recorded" : "not provided"}
              </span>
            </div>
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              <MapPinned className="h-4 w-4 text-brand-600" /> Area
            </h2>
            {field.area !== null ? (
              <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span className="text-3xl font-bold text-gray-900">
                  {formatArea(field.area)}
                  <span className="ml-1 text-sm font-medium text-gray-500">
                    {AREA_UNIT_LABELS[field.area_unit]}
                  </span>
                </span>
                <span className="text-xs text-gray-500">{AREA_SOURCE_LABELS[field.area_source]}</span>
                {field.area_source === "calculated_boundary" && field.boundary && (
                  <span className="text-xs text-gray-400">· from a drawn boundary review</span>
                )}
              </div>
            ) : (
              <p className="mt-3 text-sm text-gray-500">Area not provided yet — you can add it anytime.</p>
            )}
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              <Droplets className="h-4 w-4 text-brand-600" /> Water
            </h2>
            {field.water_source || field.water_availability ? (
              <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="rounded-lg bg-gray-50 p-3">
                  <dt className="text-xs text-gray-400">Main water source</dt>
                  <dd className="mt-0.5 font-semibold text-gray-800">
                    {field.water_source ? WATER_SOURCE_LABELS[field.water_source] ?? field.water_source : "Not recorded"}
                  </dd>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <dt className="text-xs text-gray-400">Water availability</dt>
                  <dd className="mt-0.5 font-semibold text-gray-800">
                    {field.water_availability
                      ? WATER_AVAILABILITY_LABELS[field.water_availability] ?? field.water_availability
                      : "Not recorded"}
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="mt-3 text-sm text-gray-500">Water conditions not recorded for this field.</p>
            )}
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              <Sprout className="h-4 w-4 text-brand-600" /> Soil
            </h2>
            <div className="mt-3 flex items-center gap-3">
              <span
                className={`rounded-full px-3 py-1 text-sm font-medium ${
                  field.soil_status === "available"
                    ? "bg-emerald-50 text-emerald-700"
                    : field.soil_status === "pending"
                      ? "bg-sky-50 text-sky-700"
                      : "bg-gray-100 text-gray-600"
                }`}
              >
                {SOIL_STATUS_LABELS[field.soil_status]}
              </span>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-gray-400">
              ANNADATA records only what is verified. Uploading soil reports arrives in a later stage.
            </p>
          </section>
        </div>

        {/* Right: weather + trust note */}
        <div className="space-y-5">
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
              <CloudSun className="h-4 w-4 text-brand-600" /> Weather near your field
            </h2>
            <div className="mt-3">
              <WeatherDetail fieldId={field.id} />
            </div>
          </section>

          <div className="rounded-xl border border-brand-100 bg-brand-50/50 p-5">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-brand-900">
              <Info className="h-4 w-4" /> Why this matters
            </h2>
            <ul className="mt-3 space-y-2 text-sm text-brand-900/80">
              <li>• This is your field’s trusted baseline — location, area, water, soil status.</li>
              <li>• We show only real values. Anything not known is marked “not provided”.</li>
              <li>• Weather here is live and real. It will power smarter crop advice later.</li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
}