import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, Info, Save } from "lucide-react";
import FieldMap from "../components/FieldMap";
import { fieldsApi } from "../services/fields";
import { formatArea } from "../lib/geo";
import {
  AREA_UNIT_LABELS,
  WATER_AVAILABILITY_OPTIONS,
  WATER_SOURCE_OPTIONS,
  landStructure,
} from "../lib/labels";
import type { AreaUnit, Field, WaterAvailability, WaterSource } from "../types/field";

export default function FieldEdit() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [field, setField] = useState<Field | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [waterSource, setWaterSource] = useState<WaterSource | null>(null);
  const [waterAvailability, setWaterAvailability] = useState<WaterAvailability | null>(null);
  const [soilStatus, setSoilStatus] = useState<"not_provided" | "pending" | "available">("not_provided");
  const [manualArea, setManualArea] = useState("");
  const [manualUnit, setManualUnit] = useState<AreaUnit>("acre");
  const [clearArea, setClearArea] = useState(false);

  const [marker, setMarker] = useState<[number, number] | null>(null);
  const [locationChanged, setLocationChanged] = useState(false);
  const [confirmLocation, setConfirmLocation] = useState(false);

  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    fieldsApi
      .get(id)
      .then((data) => {
        setField(data);
        setName(data.field_name);
        setWaterSource(data.water_source);
        setWaterAvailability(data.water_availability);
        setSoilStatus(data.soil_status);
        setMarker(data.latitude !== null && data.longitude !== null ? [data.latitude, data.longitude] : null);
      })
      .catch(() => setError("This field could not be found."));
  }, [id]);

  if (error) {
    return (
      <>
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">{error}</div>
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

  const handleMapChange = (pos: [number, number]) => {
    setMarker(pos);
    setLocationChanged(true);
    setConfirmLocation(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        field_name: name.trim(),
        water_source: waterSource,
        water_availability: waterAvailability,
        soil_status: soilStatus,
      };
      if (clearArea) {
        payload.area = null;
        payload.area_unit = "acre";
        payload.area_source = "not_provided";
        payload.boundary = null;
      } else if (manualArea) {
        const value = parseFloat(manualArea);
        if (!Number.isFinite(value)) {
          setError("Please enter a valid area number.");
          setSaving(false);
          return;
        }
        payload.area = value;
        payload.area_unit = manualUnit;
        payload.area_source = "manual";
        payload.boundary = null;
      }
      if (locationChanged && marker) {
        if (!confirmLocation) {
          setError("Location changed — please tick “I confirm the new location” to save it.");
          setSaving(false);
          return;
        }
        payload.latitude = marker[0];
        payload.longitude = marker[1];
        payload.location_confirmed = true;
      }
      await fieldsApi.update(field.id, payload);
      navigate(`/fields/${field.id}`);
    } catch (err) {
      const verbose = err as { response?: { data?: { detail?: string } } };
      setError(
        typeof verbose?.response?.data?.detail === "string"
          ? verbose.response.data.detail
          : "We could not save your changes. Please try again."
      );
      setSaving(false);
    }
  };

  const currentAreaLabel =
    field.area !== null
      ? `${formatArea(field.area)} ${AREA_UNIT_LABELS[field.area_unit]}`
      : "No area recorded";

  return (
    <>
      <div className="flex items-center gap-3">
        <Link
          to={`/fields/${field.id}`}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50"
          title="Back to field"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">Edit field</h1>
          <p className="mt-0.5 text-sm text-gray-500">{field.field_name}</p>
        </div>
      </div>

      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Basics</h2>
            <label className="mt-4 block text-sm font-medium text-gray-700" htmlFor="edit-name">
              Field name
            </label>
            <input
              id="edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500"
            />
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Location</h2>
            <p className="mt-2 text-xs text-gray-500">
              Current:{" "}
              {landStructure(field as unknown as { locality?: string | null; sub_district?: string | null; district?: string | null; state?: string | null; country?: string | null })}
            </p>
            {marker && (
              <>
                <div className="mt-3">
                  <FieldMap
                    position={marker}
                    onPositionChange={handleMapChange}
                    positionDraggable
                    heightClass="h-[260px]"
                    zoomControl={false}
                  />
                </div>
                <p className="mt-2 text-[11px] text-gray-400">
                  Marker at {marker[0].toFixed(6)}, {marker[1].toFixed(6)}
                  {locationChanged ? " (changed — needs confirmation)" : ""}
                </p>
                {locationChanged && (
                  <label className="mt-3 flex cursor-pointer items-center gap-2 rounded-lg border border-brand-200 bg-brand-50 p-3 text-sm text-brand-900">
                    <input
                      type="checkbox"
                      checked={confirmLocation}
                      onChange={(e) => setConfirmLocation(e.target.checked)}
                      className="h-4 w-4 accent-brand-600"
                    />
                    I confirm the new location for this field
                  </label>
                )}
              </>
            )}
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Area</h2>
            <p className="mt-2 text-xs text-gray-500">
              Currently recorded: <span className="font-semibold text-gray-700">{currentAreaLabel}</span>
            </p>
            <label className="mt-4 block text-sm font-medium text-gray-700" htmlFor="edit-area">
              Set a manual area (optional)
            </label>
            <div className="mt-2 grid max-w-sm grid-cols-[1fr_130px] gap-3">
              <input
                id="edit-area"
                value={manualArea}
                onChange={(e) => {
                  setManualArea(e.target.value);
                  setClearArea(false);
                }}
                inputMode="decimal"
                placeholder="e.g. 2.5"
                className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500"
              />
              <select
                value={manualUnit}
                onChange={(e) => setManualUnit(e.target.value as AreaUnit)}
                className="rounded-lg border border-gray-300 bg-white px-2 py-2.5 text-sm outline-none focus:border-brand-500"
              >
                <option value="acre">Acre</option>
                <option value="hectare">Hectare</option>
                <option value="bigha">Bigha</option>
                <option value="square_metre">Square metre</option>
              </select>
            </div>
            <label className="mt-3 flex cursor-pointer items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={clearArea}
                onChange={(e) => {
                  setClearArea(e.target.checked);
                  if (e.target.checked) setManualArea("");
                }}
                className="h-4 w-4 accent-brand-600"
              />
              Clear the recorded area
            </label>
          </section>
        </div>

        <div className="space-y-5">
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Water</h2>
            <p className="mt-3 text-xs font-semibold text-gray-700">Main water source</p>
            <div className="mt-2 space-y-1.5">
              {WATER_SOURCE_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                    waterSource === option.value ? "border-brand-600 bg-brand-50" : "border-gray-200"
                  }`}
                >
                  <span className="font-medium text-gray-800">{option.label}</span>
                  <input
                    type="radio"
                    name="water-source"
                    checked={waterSource === option.value}
                    onChange={() => setWaterSource(option.value as WaterSource)}
                    className="h-4 w-4 accent-brand-600"
                  />
                </label>
              ))}
              {waterSource && (
                <button
                  type="button"
                  onClick={() => setWaterSource(null)}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  Clear choice
                </button>
              )}
            </div>

            <p className="mt-5 text-xs font-semibold text-gray-700">Water availability</p>
            <div className="mt-2 space-y-1.5">
              {WATER_AVAILABILITY_OPTIONS.map((option) => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                    waterAvailability === option.value ? "border-brand-600 bg-brand-50" : "border-gray-200"
                  }`}
                >
                  <span className="font-medium text-gray-800">{option.label}</span>
                  <input
                    type="radio"
                    name="water-availability"
                    checked={waterAvailability === option.value}
                    onChange={() => setWaterAvailability(option.value as WaterAvailability)}
                    className="h-4 w-4 accent-brand-600"
                  />
                </label>
              ))}
              {waterAvailability && (
                <button
                  type="button"
                  onClick={() => setWaterAvailability(null)}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  Clear choice
                </button>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Soil</h2>
            <div className="mt-3 space-y-1.5">
              {[
                { value: "not_provided" as const, label: "No soil report yet" },
                { value: "pending" as const, label: "Pending — report to be added later" },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-center justify-between rounded-lg border px-3 py-2 text-sm ${
                    soilStatus === option.value ? "border-brand-600 bg-brand-50" : "border-gray-200"
                  }`}
                >
                  <span className="font-medium text-gray-800">{option.label}</span>
                  <input
                    type="radio"
                    name="soil-status"
                    checked={soilStatus === option.value}
                    onChange={() => setSoilStatus(option.value)}
                    className="h-4 w-4 accent-brand-600"
                  />
                </label>
              ))}
            </div>
            <p className="mt-3 flex items-start gap-2 text-xs text-gray-400">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              “Available” is reserved for a verified soil report — we never fake it.
            </p>
          </section>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}

          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {saving ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            Save changes
          </button>
        </div>
      </div>

      <p className="mt-4 flex items-center gap-1.5 text-xs text-gray-400">
        <Check className="h-3.5 w-3.5 text-brand-500" />
        Area name uses the location you confirmed; to change it, move the marker above.
      </p>
    </>
  );
}