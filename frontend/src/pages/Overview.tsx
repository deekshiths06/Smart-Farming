import { Link } from "react-router-dom";
import {
  ArrowRight,
  CloudSun,
  Droplets,
  FlaskConical,
  Leaf,
  MapPin,
  MapPinned,
  Plus,
  Sprout,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useFields } from "../hooks/useFields";
import { useWeather } from "../hooks/useWeather";
import { FieldCard } from "../components/ui/FieldCard";
import { WeatherSummaryCard } from "../components/ui/WeatherSummaryCard";
import { Skeleton } from "../components/ui/Skeleton";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorAlert } from "../components/ui/ErrorAlert";
import { ImageWithFallback } from "../components/ui/ImageWithFallback";
import { Button } from "../components/ui/Button";

function Stat({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="group flex items-start gap-3 rounded-card border border-border bg-surface p-4 shadow-card transition-shadow hover:shadow-pop">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100">
        {icon}
      </span>
      <div className="min-w-0">
        <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
        <p className="font-display mt-0.5 text-2xl font-extrabold tracking-tight text-ink">{value}</p>
        {hint && <p className="mt-0.5 truncate text-[11px] text-ink-muted">{hint}</p>}
      </div>
    </div>
  );
}

const QUICK_LINKS = [
  {
    to: "/soil",
    title: "Soil intelligence",
    body: "See pH, NPK and more — measured against what each crop needs.",
    image: "/assets/fertile-soil.jpg",
    alt: "Hands sifting fertile soil in a garden bed",
  },
  {
    to: "/crops",
    title: "Crop recommendations",
    body: "Crops ranked for this season, with the reasoning spelled out.",
    image: "/assets/crop-rows.jpg",
    alt: "Straight rows of young crops on a farm",
  },
];

export default function Overview() {
  const { user } = useAuth();
  const { fields, loading, error, reload } = useFields();
  const { data: weather, loading: weatherLoading, reload: reloadWeather } = useWeather(fields[0]?.id);

  const firstName = user?.name?.trim().split(/\s+/)[0] ?? "farmer";
  const today = new Date();
  const greeting = today.getHours() < 12 ? "Good morning" : today.getHours() < 18 ? "Good afternoon" : "Good evening";
  const dateLabel = today.toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const confirmedCount = fields.filter((field) => field.location_confirmed).length;
  const waterCount = fields.filter((field) => field.water_source).length;
  const soilReadyCount = fields.filter((field) => field.soil_status === "available").length;

  return (
    <div className="space-y-6">
      <section className="relative isolate overflow-hidden rounded-panel shadow-soft">
        <ImageWithFallback
          src="/assets/welcome-harvest.jpg"
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="hero-gradient-left absolute inset-0" aria-hidden="true" />
        <div className="leaf-pattern absolute inset-0 opacity-30" />
        <div className="relative px-6 py-8 sm:px-8 lg:px-10 lg:py-10">
          <p className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-widest text-brand-300">
            <Leaf className="h-3.5 w-3.5" />
            {dateLabel}
          </p>
          <h1 className="font-display mt-2 text-balance text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            {greeting}, {firstName}.
          </h1>
          <p className="mt-2 max-w-xl text-balance text-sm leading-relaxed text-white/80 sm:text-[15px]">
            ANNADATA keeps an honest record of your fields — where they are, how they're irrigated
            and what the weather is doing right now.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Link to="/fields/create">
              <Button className="bg-brand-400 text-forest-950 hover:bg-brand-300" rightIcon={<Plus className="h-4 w-4" />}>
                Add a field
              </Button>
            </Link>
            <Link to="/weather">
              <Button variant="outline" className="border-white/35 bg-transparent text-white hover:border-white/70 hover:bg-white/10 hover:text-white">
                Check the weather
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {error && (
        <ErrorAlert title="Fields could not be loaded" message={error} onRetry={() => void reload()} />
      )}

      {loading ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[...Array(4)].map((_, index) => (
            <Skeleton key={index} className="h-[104px] rounded-card" />
          ))}
        </div>
      ) : fields.length === 0 ? (
        <EmptyState
          icon={<Sprout className="h-8 w-8" />}
          title="Know your first field"
          description="Add your field with GPS and a map — where it is, how big it is, and its water and soil story. This is the foundation every ANNADATA decision will build on."
          action={
            <Link to="/fields/create">
              <Button rightIcon={<Plus className="h-4 w-4" />}>Create your first field</Button>
            </Link>
          }
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <Stat icon={<MapPinned className="h-5 w-5" />} label="Fields recorded" value={fields.length} hint="All-time record" />
            <Stat
              icon={<MapPin className="h-5 w-5" />}
              label="GPS confirmed"
              value={confirmedCount}
              hint={`${fields.length - confirmedCount} still need confirming`}
            />
            <Stat icon={<Droplets className="h-5 w-5" />} label="Water recorded" value={waterCount} hint="Sources on file" />
            <Stat
              icon={<FlaskConical className="h-5 w-5" />}
              label="Soil ready"
              value={soilReadyCount}
              hint="Verified soil reports"
            />
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {QUICK_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className="group relative overflow-hidden rounded-panel border border-border bg-surface shadow-card transition-shadow hover:shadow-pop"
              >
                <div className="relative h-32 overflow-hidden sm:h-36">
                  <ImageWithFallback
                    src={link.image}
                    alt={link.alt}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                    wrapperClassName="h-full w-full bg-gradient-to-tr from-brand-100 via-forest-100 to-forest-200"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-forest-950/55 via-forest-950/10 to-transparent" />
                </div>
                <div className="flex items-start justify-between gap-3 p-5">
                  <div>
                    <h2 className="font-display text-base font-bold tracking-tight text-ink">{link.title}</h2>
                    <p className="mt-1 text-sm leading-relaxed text-ink-soft">{link.body}</p>
                  </div>
                  <ArrowRight className="mt-1 h-5 w-5 shrink-0 text-brand-600 transition-transform group-hover:translate-x-1" />
                </div>
              </Link>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-display text-lg font-bold tracking-tight text-ink">Your fields</h2>
                  <p className="text-xs text-ink-muted">The most recent {Math.min(fields.length, 3) > 1 ? "3" : "one"} of {fields.length}</p>
                </div>
                {fields.length > 3 && (
                  <Link
                    to="/fields"
                    className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 transition-colors hover:text-brand-800"
                  >
                    View all <ArrowRight className="h-4 w-4" />
                  </Link>
                )}
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {fields.slice(0, 3).map((field) => (
                  <FieldCard key={field.id} field={field} />
                ))}
              </div>
            </section>

            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-bold tracking-tight text-ink">Live weather</h2>
                {fields.length > 0 && (
                  <Link
                    to="/weather"
                    className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 transition-colors hover:text-brand-800"
                  >
                    Full forecast <ArrowRight className="h-4 w-4" />
                  </Link>
                )}
              </div>
              {fields.length > 0 ? (
                <WeatherSummaryCard
                  response={weather}
                  loading={weatherLoading}
                  onReload={() => void reloadWeather()}
                />
              ) : (
                <Skeleton className="h-56 rounded-card" />
              )}
            </section>
          </div>
        </>
      )}

      <p className="flex items-center justify-center gap-1.5 text-center text-xs text-ink-muted">
        <CloudSun className="h-3.5 w-3.5" />
        Weather shown here is read live at your field's coordinates — nothing is invented.
      </p>
    </div>
  );
}