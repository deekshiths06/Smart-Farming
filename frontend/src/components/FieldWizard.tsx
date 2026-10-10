import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Crosshair,
  Info,
  MapPin,
} from "lucide-react";
import FieldMap, { type PositionTuple } from "./FieldMap";
import { fieldsApi } from "../services/fields";
import {
  formatArea,
  latLngToBoundary,
  polygonAreaSquareMetres,
  SQM_PER,
} from "../lib/geo";
import {
  WATER_AVAILABILITY_LABELS,
  WATER_AVAILABILITY_OPTIONS,
  WATER_SOURCE_LABELS,
  WATER_SOURCE_OPTIONS,
  landStructure,
} from "../lib/labels";
import type {
  AreaSource,
  AreaUnit,
  CreateFieldPayload,
  Place,
  SoilStatus,
  WaterAvailability,
  WaterSource,
} from "../types/field";

const STEPS = [
  { id: "name", label: "Name" },
  { id: "location", label: "Location" },
  { id: "map", label: "Map" },
  { id: "place", label: "Area name" },
  { id: "area", label: "Area" },
  { id: "water", label: "Water" },
  { id: "soil", label: "Soil & finish" },
] as const;

interface GeoResult {
  ok: boolean;
  position?: PositionTuple;
  accuracy?: number | null;
  error?: string;
}

function requestCurrentPosition(): Promise<GeoResult> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve({
        ok: false,
        error: "Your browser does not support geolocation. You can still select your field on the map.",
      });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          ok: true,
          position: [position.coords.latitude, position.coords.longitude],
          accuracy:
            typeof position.coords.accuracy === "number" ? position.coords.accuracy : null,
        });
      },
      (error) => {
        const message =
          error.code === error.PERMISSION_DENIED
            ? "Location permission was denied. You can still select your field on the map below."
            : error.code === error.POSITION_UNAVAILABLE
              ? "Your location is not available right now. Please select your field on the map below."
              : error.code === error.TIMEOUT
                ? "Location lookup timed out. Please select your field on the map below."
                : "We could not retrieve your location. Please select your field on the map below.";
        resolve({ ok: false, error: message });
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );
  });
}

function coordinateLabel(lat: number, lng: number): string {
  return `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
}

function StepHeading({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h2 className="text-xl font-bold tracking-tight text-gray-900">{title}</h2>
      <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-gray-500">{subtitle}</p>
    </div>
  );
}

function Card({
  children,
  onClick,
  selected,
  className = "",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  selected?: boolean;
  className?: string;
}) {
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => e.key === "Enter" && onClick() : undefined}
      className={`relative rounded-xl border p-4 ${
        selected
          ? "border-brand-600 bg-brand-50/60 ring-1 ring-brand-600"
          : "border-gray-200 bg-white"
      } ${onClick ? "cursor-pointer hover:border-brand-400" : ""} ${className}`}
    >
      {selected && (
        <span className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-brand-600 text-white">
          <Check className="h-3 w-3" />
        </span>
      )}
      {children}
    </div>
  );
}

// Keep option collections typed but render explicitly below.
const WATER_SOURCE_CHOICES = WATER_SOURCE_OPTIONS as unknown as Array<{
  value: WaterSource;
  label: string;
  description: string;
}>;

const WATER_AVAILABILITY_CHOICES = WATER_AVAILABILITY_OPTIONS as unknown as Array<{
  value: WaterAvailability;
  label: string;
  description: string;
}>;

function PlaceRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-gray-400">{label}</dt>
      <dd className="font-medium text-gray-800">{value}</dd>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-gray-400">{label}</dt>
      <dd className="text-sm font-medium text-gray-800">{value}</dd>
    </div>
  );
}

export default function FieldWizard() {
  const navigate = useNavigate();

  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Step 1 — name
  const [fieldName, setFieldName] = useState("");
  // Step 2 — location
  const [position, setPosition] = useState<PositionTuple | null>(null);
  const [accuracy, setAccuracy] = useState<number | null>(null);
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [manualShow, setManualShow] = useState(false);
  const [manualLat, setManualLat] = useState("");
  const [manualLng, setManualLng] = useState("");
  // Step 3 — confirm
  const [confirmed, setConfirmed] = useState(false);
  // Step 4 — area name (reverse geocoded place)
  const [place, setPlace] = useState<Place | null>(null);
  const [placeUnavailable, setPlaceUnavailable] = useState<string | null>(null);
  const [geocoding, setGeocoding] = useState(false);
  // Step 5 — area
  const [areaMode, setAreaMode] = useState<"draw" | "manual" | "skip">("draw");
  const [drawingPoints, setDrawingPoints] = useState<PositionTuple[]>([]);
  const [manualArea, setManualArea] = useState("");
  const [manualUnit, setManualUnit] = useState<AreaUnit>("acre");
  // Step 6 — water
  const [waterSource, setWaterSource] = useState<WaterSource | null>(null);
  const [waterAvailability, setWaterAvailability] = useState<WaterAvailability | null>(null);
  // Step 7 — soil
  const [soilStatus, setSoilStatus] = useState<SoilStatus>("not_provided");

  const step = STEPS[stepIndex];
  const isLast = stepIndex === STEPS.length - 1;
  const isFirst = stepIndex === 0;

  const computedAreaAcres = useMemo(() => {
    if (areaMode !== "draw" || drawingPoints.length < 3) return null;
    const ring = drawingPoints.map((p) => [p[1], p[0]] as [number, number]);
    const sqm = polygonAreaSquareMetres(ring);
    if (!sqm) return null;
    return { sqm, acres: sqm / SQM_PER.acre };
  }, [areaMode, drawingPoints]);

  const areaPayload = useMemo((): {
    boundary: CreateFieldPayload["boundary"];
    area: number | null;
    area_unit: AreaUnit;
    area_source: AreaSource;
  } => {
    if (areaMode === "draw" && computedAreaAcres) {
      return {
        boundary: latLngToBoundary(drawingPoints),
        area: computedAreaAcres.acres,
        area_unit: "acre" as AreaUnit,
        area_source: "calculated_boundary" as AreaSource,
      };
    }
    if (areaMode === "manual" && manualArea) {
      const value = parseFloat(manualArea);
      return {
        boundary: null,
        area: Number.isFinite(value) ? value : null,
        area_unit: manualUnit,
        area_source: "manual" as AreaSource,
      };
    }
    return {
      boundary: null,
      area: null,
      area_unit: "acre" as AreaUnit,
      area_source: "not_provided" as AreaSource,
    };
  }, [areaMode, computedAreaAcres, drawingPoints, manualArea, manualUnit]);

  const nextStep = () => {
    setError(null);
    if (step.id === "name") {
      if (!fieldName.trim()) {
        setError("Please give your field a name, for example “East field” or “Kaveri plot”.");
        return;
      }
      setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
      return;
    }
    if (step.id === "location") {
      if (!position) {
        setError(
          'Please choose how we will locate your field: use "My Current Location" or tap on the map to place the marker.'
        );
        return;
      }
      setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
      return;
    }
    if (step.id === "map") {
      if (!confirmed) {
        setError("Please tap “Confirm This Location” after you are happy with the marker position.");
        return;
      }
      setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
      return;
    }
    if (step.id === "area") {
      if (areaMode === "draw" && drawingPoints.length > 0 && drawingPoints.length < 3) {
        setError("A boundary needs at least 3 points. Add more points or choose “Enter manually”.");
        return;
      }
      if (areaMode === "manual" && !manualArea) {
        setError("Please enter the estimated area of your field.");
        return;
      }
      setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
      return;
    }
    setStepIndex((index) => Math.min(index + 1, STEPS.length - 1));
  };

  const prevStep = () => {
    setError(null);
    setStepIndex((index) => Math.max(index - 1, 0));
  };

  const handleUseCurrentLocation = async () => {
    setLocating(true);
    setGeoError(null);
    const result = await requestCurrentPosition();
    setLocating(false);
    if (result.ok && result.position) {
      setPosition(result.position);
      setAccuracy(result.accuracy ?? null);
    } else {
      setGeoError(result.error ?? "We could not retrieve your location.");
    }
  };

  const handleManualApply = () => {
    const lat = parseFloat(manualLat);
    const lng = parseFloat(manualLng);
    if (Number.isNaN(lat) || lat < -90 || lat > 90) {
      setGeoError("Please enter a valid latitude between -90 and 90.");
      return;
    }
    if (Number.isNaN(lng) || lng < -180 || lng > 180) {
      setGeoError("Please enter a valid longitude between -180 and 180.");
      return;
    }
    setGeoError(null);
    setPosition([lat, lng]);
    setAccuracy(null);
  };

  const handleConfirmLocation = async () => {
    if (!position) return;
    setConfirmed(true);
    setGeocoding(true);
    setPlaceUnavailable(null);
    setPlace(null);
    try {
      const response = await fieldsApi.reverseGeocode(position[0], position[1]);
      if (response.status === "ok" && response.location) {
        setPlace(response.location);
      } else {
        setPlaceUnavailable(
          response.message ?? "We could not retrieve the area name for these coordinates."
        );
      }
    } catch {
      setPlaceUnavailable("We could not retrieve the area name for these coordinates.");
    } finally {
      setGeocoding(false);
    }
  };

  const handleCreate = async () => {
    if (!position) return;
    setSubmitting(true);
    setError(null);
    const payload: CreateFieldPayload = {
      field_name: fieldName.trim(),
      latitude: position[0],
      longitude: position[1],
      location_accuracy: accuracy,
      location_confirmed: true,
      locality: place?.locality ?? null,
      sub_district: place?.sub_district ?? null,
      district: place?.district ?? null,
      state: place?.state ?? null,
      country: place?.country ?? null,
      address: place?.address ?? null,
      boundary: areaPayload.boundary,
      area: areaPayload.area,
      area_unit: areaPayload.area_unit,
      area_source: areaPayload.area_source,
      water_source: waterSource,
      water_availability: waterAvailability,
      soil_status: soilStatus,
    };
    try {
      const created = await fieldsApi.create(payload);
      navigate(`/fields/${created.id}`);
    } catch (err) {
      const verbose = err as { response?: { data?: { detail?: string } } };
      const detail = verbose?.response?.data?.detail;
      setError(
        typeof detail === "string" ? detail : "We could not save your field. Please try again."
      );
      setSubmitting(false);
    }
  };

  const goToStep = (index: number) => {
    if (index < stepIndex) setStepIndex(index);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      {/* Step rail */}
      <aside className="lg:sticky lg:top-24 lg:self-start">
        <ol className="space-y-1 rounded-xl border border-gray-200 bg-white p-3">
          {STEPS.map((entry, index) => {
            const done = index < stepIndex;
            const active = index === stepIndex;
            return (
              <li key={entry.id}>
                <button
                  type="button"
                  onClick={() => goToStep(index)}
                  disabled={index > stepIndex}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm ${
                    active ? "bg-brand-50 font-semibold text-brand-800" : "text-gray-600"
                  } ${index > stepIndex ? "cursor-default opacity-60" : ""}`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                      done || active ? "bg-brand-600 text-white" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {done ? <Check className="h-3.5 w-3.5" /> : index + 1}
                  </span>
                  <span className="truncate">{entry.label}</span>
                </button>
              </li>
            );
          })}
        </ol>
        <p className="mt-3 px-3 text-xs leading-relaxed text-gray-400">
          You can always edit a field later from the field detail page.
        </p>
      </aside>

      {/* Step panel */}
      <section className="rounded-xl border border-gray-200 bg-white p-5 sm:p-7">
        {/* Step 1 — name */}
        {step.id === "name" && (
          <div>
            <StepHeading
              title="Name your field"
              subtitle="Your fields live on your farm map — a clear name helps you recognise and manage each one."
            />
            <label className="mt-6 block text-sm font-medium text-gray-700" htmlFor="field-name">
              Field name *
            </label>
            <input
              id="field-name"
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && nextStep()}
              placeholder="e.g. East field, Kaveri plot, Home garden"
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm shadow-sm outline-none ring-brand-500/30 focus:border-brand-500 focus:ring-2"
              autoFocus
            />
            <div className="mt-3 flex flex-wrap gap-2">
              {["East field", "Kaveri plot", "Home garden", "Turmeric block"].map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => setFieldName(suggestion)}
                  className="rounded-full border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:border-brand-400 hover:text-brand-700"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2 — location */}
        {step.id === "location" && (
          <div>
            <StepHeading
              title="Where is your field?"
              subtitle="A trusted record starts with where your field is. We use your GPS or a point you place on the map — no guessing."
            />
            <div className="mt-6 grid gap-4 md:grid-cols-[280px_1fr]">
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={handleUseCurrentLocation}
                  disabled={locating}
                  className="flex w-full items-center gap-3 rounded-xl border border-brand-200 bg-brand-50 p-3.5 text-left hover:bg-brand-100/70 disabled:opacity-60"
                >
                  {locating ? (
                    <Crosshair className="h-5 w-5 animate-pulse text-brand-700" />
                  ) : (
                    <MapPin className="h-5 w-5 text-brand-700" />
                  )}
                  <span className="text-sm font-medium text-brand-900">
                    {locating ? "Getting your location…" : "Use My Current Location"}
                  </span>
                </button>

                {geoError && (
                  <p className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-800">
                    <Info className="mt-0.5 h-4 w-4 shrink-0" /> {geoError}
                  </p>
                )}

                {accuracy !== null && accuracy !== undefined && position && (
                  <p className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
                    GPS accuracy: approximately{" "}
                    <span className="font-semibold text-gray-800">{Math.round(accuracy)} m</span>
                    {accuracy >= 1000 && " (coarse — please adjust on the map)"}
                  </p>
                )}

                {position && (
                  <div className="rounded-lg bg-gray-50 p-3 text-xs text-gray-600">
                    Marker at{" "}
                    <span className="font-mono font-semibold text-gray-800">
                      {coordinateLabel(position[0], position[1])}
                    </span>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => setManualShow((show) => !show)}
                  className="text-xs font-medium text-brand-700 hover:text-brand-800"
                >
                  {manualShow ? "Hide manual coordinates" : "Enter coordinates manually"}
                </button>

                {manualShow && (
                  <div className="space-y-2 rounded-lg border border-gray-200 p-3">
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        value={manualLat}
                        onChange={(e) => setManualLat(e.target.value)}
                        placeholder="Latitude (e.g. 13.0839)"
                        className="rounded-lg border border-gray-300 px-2.5 py-2 text-xs outline-none focus:border-brand-500"
                      />
                      <input
                        value={manualLng}
                        onChange={(e) => setManualLng(e.target.value)}
                        placeholder="Longitude (e.g. 77.5601)"
                        className="rounded-lg border border-gray-300 px-2.5 py-2 text-xs outline-none focus:border-brand-500"
                      />
                    </div>
                    <button
                      type="button"
                      onClick={handleManualApply}
                      className="w-full rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
                    >
                      Place marker
                    </button>
                  </div>
                )}
              </div>

              <FieldMap
                position={position}
                onPositionChange={(pos) => {
                  setPosition(pos);
                  setGeoError(null);
                }}
                heightClass="h-[320px]"
              />
            </div>
            <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-gray-400">
              <Info className="mt-0.5 h-4 w-4 shrink-0" />
              Tap the map (or use your GPS) to place a marker. The next step lets you fine-tune it and
              confirm it as the field’s location.
            </p>
          </div>
        )}

        {/* Step 3 — map confirm */}
        {step.id === "map" && (
          <div>
            <StepHeading
              title="Confirm the location"
              subtitle="Drag the marker to the exact point on your field, then confirm. Confirming locks this in as the field’s trusted location."
            />
            <div className="mt-6">
              <FieldMap
                position={position}
                onPositionChange={(pos) => {
                  setPosition(pos);
                  setConfirmed(false);
                }}
                positionDraggable
                heightClass="h-[340px]"
              />
            </div>
            {position && (
              <p className="mt-3 text-xs text-gray-500">
                Marker at{" "}
                <span className="font-mono font-semibold text-gray-800">
                  {coordinateLabel(position[0], position[1])}
                </span>
              </p>
            )}
            <button
              type="button"
              onClick={handleConfirmLocation}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
              disabled={!position || geocoding}
            >
              {geocoding ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Looking up area name…
                </>
              ) : confirmed ? (
                <>
                  <Check className="h-4 w-4" /> Location confirmed — re-confirm to update the area name
                </>
              ) : (
                "Confirm This Location"
              )}
            </button>
          </div>
        )}

        {/* Step 4 — area name (reverse geocode) */}
        {step.id === "place" && (
          <div>
            <StepHeading
              title="Area name"
              subtitle="ANNADATA asks the location service where your coordinates are. Only the values it confirms are stored — we never guess."
            />
            <div className="mt-6 space-y-4">
              {geocoding && (
                <p className="flex items-center gap-2 rounded-lg bg-gray-50 p-4 text-sm text-gray-500">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                  Contacting the location service…
                </p>
              )}

              {!geocoding && place && (
                <div className="space-y-3">
                  <div className="rounded-xl border border-brand-200 bg-brand-50/50 p-4">
                    <p className="text-sm font-semibold text-brand-900">
                      {place.address ?? landStructure(place)}
                    </p>
                    <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
                      {place.locality && <PlaceRow label="Locality / village" value={place.locality} />}
                      {place.sub_district && <PlaceRow label="Sub-district (taluk)" value={place.sub_district} />}
                      {place.district && <PlaceRow label="District" value={place.district} />}
                      {place.state && <PlaceRow label="State" value={place.state} />}
                      {place.country && <PlaceRow label="Country" value={place.country} />}
                    </dl>
                  </div>
                  <p className="flex items-start gap-2 text-xs leading-relaxed text-gray-400">
                    <Info className="mt-0.5 h-4 w-4 shrink-0" /> This area name is stored with your field.
                    You can change it later.
                  </p>
                </div>
              )}

              {!geocoding && placeUnavailable && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <p className="text-sm text-amber-800">{placeUnavailable}</p>
                  <p className="mt-1 text-xs text-amber-700">
                    You can continue — area name is optional. Try again any time.
                  </p>
                  <button
                    type="button"
                    onClick={handleConfirmLocation}
                    className="mt-3 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100"
                  >
                    Try again
                  </button>
                </div>
              )}

              {!geocoding && !place && !placeUnavailable && (
                <p className="rounded-lg bg-gray-50 p-4 text-sm text-gray-500">
                  No area lookup yet. Tap “Continue” to keep going, or re-confirm your location to fetch
                  the area name.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Step 5 — area */}
        {step.id === "area" && (
          <div>
            <StepHeading
              title="Field area"
              subtitle="Optional — acre is the closest legal standard for land records; bigha is for Social Forestry and non-acre leasing. The boundary is a visual helper; your exact numbers stay with you."
            />

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <Card selected={areaMode === "draw"} onClick={() => setAreaMode("draw")}>
                <p className="text-sm font-semibold text-gray-800">Draw a boundary on the map</p>
                <p className="mt-1 text-xs text-gray-500">
                  Tap to add corners on the map — ANNADATA computes an approximate area for you.
                </p>
              </Card>
              <Card selected={areaMode === "manual"} onClick={() => setAreaMode("manual")}>
                <p className="text-sm font-semibold text-gray-800">Enter area manually</p>
                <p className="mt-1 text-xs text-gray-500">If you already know the area and its units.</p>
              </Card>
            </div>

            {areaMode === "draw" && (
              <div className="mt-5">
                <FieldMap
                  drawMode
                  drawingPoints={drawingPoints}
                  position={position}
                  onDrawingPointAdd={(pos) => setDrawingPoints((points) => [...points, pos])}
                  onDrawingPointRemove={(index) =>
                    setDrawingPoints((points) => points.filter((_, i) => i !== index))
                  }
                  onDrawingClear={() => setDrawingPoints([])}
                  heightClass="h-[340px]"
                />
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                  <span>Points: {drawingPoints.length}</span>
                  {drawingPoints.length < 3 ? (
                    <span className="text-gray-400">Add at least 3 points to compute the area.</span>
                  ) : (
                    <span className="flex items-center gap-1 text-brand-700">
                      <Check className="h-3.5 w-3.5" />
                      Approximate area:{" "}
                      <span className="font-semibold">
                        {computedAreaAcres
                          ? `${formatArea(computedAreaAcres.acres)} acres (~${formatArea(computedAreaAcres.sqm / SQM_PER.hectare)} ha)`
                          : "—"}
                      </span>
                    </span>
                  )}
                </div>
                {drawingPoints.length >= 4 && (
                  <p className="mt-2 flex items-start gap-2 rounded-lg bg-gray-50 p-3 text-xs leading-relaxed text-gray-500">
                    <Info className="mt-0.5 h-4 w-4 shrink-0" />
                    This boundary is a rough outline to help you. What ANNADATA records for your field is
                    the area value above.
                  </p>
                )}
              </div>
            )}

            {areaMode === "manual" && (
              <div className="mt-5">
                <div className="grid max-w-sm grid-cols-[1fr_130px] gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-600" htmlFor="manual-area">
                      Area
                    </label>
                    <input
                      id="manual-area"
                      value={manualArea}
                      onChange={(e) => setManualArea(e.target.value)}
                      inputMode="decimal"
                      placeholder="e.g. 2.5"
                      className="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand-500"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600" htmlFor="manual-unit">
                      Unit
                    </label>
                    <select
                      id="manual-unit"
                      value={manualUnit}
                      onChange={(e) => setManualUnit(e.target.value as AreaUnit)}
                      className="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-2 py-2.5 text-sm outline-none focus:border-brand-500"
                    >
                      <option value="acre">Acre</option>
                      <option value="hectare">Hectare</option>
                      <option value="bigha">Bigha</option>
                      <option value="square_metre">Square metre</option>
                    </select>
                  </div>
                </div>
                <p className="mt-2 max-w-sm text-xs leading-relaxed text-gray-400">
                  {manualUnit === "bigha"
                    ? "Bigha has no single legal-standard conversion (not even against acre), so ANNADATA records it exactly as entered and never converts it."
                    : manualUnit === "acre"
                      ? "Acre is the closest legal standard for land records — enter the number exactly as your records show."
                      : manualUnit === "hectare"
                        ? "Hectare is a legal standard used in many records — enter the number exactly as your records show."
                        : "Square metre is stored as entered — no conversion is applied."}
                </p>
              </div>
            )}

            <div className="mt-4">
              {areaMode === "skip" ? (
                <p className="rounded-lg bg-gray-50 p-3 text-xs text-gray-500">
                  Skipped — you can add an area any time from the field detail page.
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => setAreaMode("skip")}
                  className="text-xs font-medium text-gray-500 hover:text-gray-700"
                >
                  Skip area for now
                </button>
              )}
            </div>
          </div>
        )}

        {/* Step 6 — water */}
        {step.id === "water" && (
          <div>
            <StepHeading
              title="Water on your field"
              subtitle="Not sure? That’s honest too — choose “Not sure” and ANNADATA keeps the record open."
            />
            <div className="mt-6 space-y-6">
              <div>
                <p className="text-sm font-semibold text-gray-800">What is the main water source?</p>
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {WATER_SOURCE_CHOICES.map((option) => (
                    <Card
                      key={option.value}
                      selected={waterSource === option.value}
                      onClick={() => setWaterSource(option.value)}
                    >
                      <p className="text-sm font-semibold text-gray-800">{option.label}</p>
                      <p className="mt-1 text-xs text-gray-500">{option.description}</p>
                    </Card>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">How available is water?</p>
                <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {WATER_AVAILABILITY_CHOICES.map((option) => (
                    <Card
                      key={option.value}
                      selected={waterAvailability === option.value}
                      onClick={() => setWaterAvailability(option.value)}
                    >
                      <p className="text-sm font-semibold text-gray-800">{option.label}</p>
                      <p className="mt-1 text-xs text-gray-500">{option.description}</p>
                    </Card>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 7 — soil & finish */}
        {step.id === "soil" && (
          <div>
            <StepHeading
              title="Soil report"
              subtitle="We will never guess your soil. Tell us what you have, and ANNADATA records the honest status."
            />
            <div className="mt-6 space-y-3">
              <Card selected={soilStatus === "not_provided"} onClick={() => setSoilStatus("not_provided")}>
                <p className="text-sm font-semibold text-gray-800">No soil report yet</p>
                <p className="mt-1 text-xs text-gray-500">
                  Your field is fully set up without it. “Available” is reserved for a verified soil
                  report — we record “not provided” until then.
                </p>
              </Card>
              <Card selected={soilStatus === "pending"} onClick={() => setSoilStatus("pending")}>
                <p className="text-sm font-semibold text-gray-800">I have a soil report / will add later</p>
                <p className="mt-1 text-xs text-gray-500">
                  Recorded as “pending”. Uploading and verification arrive in a later stage of ANNADATA.
                </p>
              </Card>
            </div>

            <div className="mt-7 rounded-xl border border-gray-200 bg-gray-50/60 p-4">
              <p className="text-sm font-semibold text-gray-800">Review and create</p>
              <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
                <ReviewRow label="Field name" value={fieldName} />
                <ReviewRow
                  label="Coordinates"
                  value={position ? coordinateLabel(position[0], position[1]) : "—"}
                />
                <ReviewRow
                  label="Area name"
                  value={
                    place
                      ? landStructure(place)
                      : placeUnavailable
                        ? "Unavailable for now"
                        : "Not looked up"
                  }
                />
                <ReviewRow
                  label="Area"
                  value={
                    areaMode === "draw" && computedAreaAcres
                      ? `${formatArea(computedAreaAcres.acres)} acres`
                      : areaMode === "manual" && manualArea
                        ? `${manualArea} ${manualUnit}`
                        : "Not provided"
                  }
                />
                <ReviewRow
                  label="Water source"
                  value={waterSource ? WATER_SOURCE_LABELS[waterSource] : "Not provided"}
                />
                <ReviewRow
                  label="Water availability"
                  value={
                    waterAvailability
                      ? WATER_AVAILABILITY_LABELS[waterAvailability]
                      : "Not provided"
                  }
                />
                <ReviewRow
                  label="Soil"
                  value={
                    soilStatus === "pending" ? "Pending (report to be added)" : "Not provided yet"
                  }
                />
              </dl>
            </div>
          </div>
        )}

        {error && (
          <p className="mt-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <Info className="mt-0.5 h-4 w-4 shrink-0" /> {error}
          </p>
        )}

        {submitting && (
          <p className="mt-4 flex items-center gap-2 text-sm text-gray-500">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            Saving your field…
          </p>
        )}

        <div className="mt-7 flex items-center justify-between border-t border-gray-100 pt-5">
          <button
            type="button"
            onClick={prevStep}
            disabled={isFirst || submitting}
            className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          >
            <ArrowLeft className="h-4 w-4" /> Back
          </button>

          {isLast ? (
            <button
              type="button"
              onClick={handleCreate}
              disabled={submitting}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {submitting ? "Saving…" : "Create Field"} <Check className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={nextStep}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
            >
              Continue <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </section>
    </div>
  );
}