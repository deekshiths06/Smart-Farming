import { Link } from "react-router-dom";
import {
  ArrowRight,
  CloudSun,
  Compass,
  Leaf,
  MapPin,
  ScanLine,
  Sprout,
  Trees,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Logo } from "../components/ui/Logo";
import { ImageWithFallback } from "../components/ui/ImageWithFallback";
import { useAuth } from "../hooks/useAuth";

const NAV_LINKS = [
  { label: "Why ANNADATA", href: "#why" },
  { label: "How it works", href: "#how" },
  { label: "Features", href: "#features" },
];

const FEATURES = [
  {
    icon: <MapPin className="h-5 w-5" />,
    title: "Confirmed field location",
    body: "Every field is pinned by its real map location — the exact piece of land you farm, never a guess.",
    image: "/assets/field-aerial.jpg",
    alt: "Aerial view of agricultural fields",
  },
  {
    icon: <ScanLine className="h-5 w-5" />,
    title: "Soil intelligence",
    body: "Record soil test results and water availability for each field, and see them at a glance against crop needs.",
    image: "/assets/fertile-soil.jpg",
    alt: "Hands sifting fertile soil in a garden bed",
  },
  {
    icon: <Sprout className="h-5 w-5" />,
    title: "Year-round crop guidance",
    body: "Get ranked, honest recommendations for every season — with the reasons behind each score clearly explained.",
    image: "/assets/crops/rice.jpg",
    alt: "Lush green rice paddy in a field",
  },
];

const STEPS = [
  {
    number: "01",
    title: "Record your field",
    body: "Create a field, drop a pin on the exact plot, and let ANNADATA confirm its location, size and climate zone.",
  },
  {
    number: "02",
    title: "Add soil and water",
    body: "Enter the soil test results and irrigation water availability for your field — one field at a time.",
  },
  {
    number: "03",
    title: "Grow with confidence",
    body: "Read the weather at your field's coordinates and compare crops side by side before you sow.",
  },
];

export default function Landing() {
  const { status, user } = useAuth();
  const authenticated = status === "authenticated" && !!user;
  const homePath = authenticated ? "/dashboard" : "/login";

  return (
    <div className="flex min-h-screen flex-col bg-canvas font-sans text-ink">
      <header className="absolute inset-x-0 top-0 z-40">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 sm:px-8">
          <Link
            to="/"
            className="inline-flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-forest-950"
            aria-label="ANNADATA home"
          >
            <Logo inverted showWordmark={false} className="h-9 w-9" />
            <span className="text-lg font-extrabold tracking-tight text-white">ANNADATA</span>
          </Link>

          <nav className="hidden items-center gap-8 text-sm font-medium text-white/80 lg:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="transition-colors hover:text-white"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button
                variant="outline"
                className="border-white/35 bg-transparent text-white hover:border-white/70 hover:bg-white/10 hover:text-white"
              >
                Log in
              </Button>
            </Link>
            <Link to={homePath}>
              <Button className="bg-brand-400 text-forest-950 hover:bg-brand-300">
                {authenticated ? "Open your dashboard" : "Get started"}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="relative isolate flex min-h-[92vh] items-center overflow-hidden bg-forest-950">
          <ImageWithFallback
            src="/assets/hero-field.jpg"
            alt="A wide green agricultural field under soft morning light"
            className="absolute inset-0 h-full w-full object-cover"
            wrapperClassName="absolute inset-0 h-full w-full bg-gradient-to-tr from-forest-950 via-forest-900 to-forest-800"
          />
          <div className="hero-gradient absolute inset-0" />
          <div className="leaf-pattern absolute inset-0 opacity-40" />

          <div className="relative mx-auto w-full max-w-7xl px-5 pb-20 pt-36 sm:px-8">
            <div className="max-w-2xl">
              <p className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-white backdrop-blur">
                <Leaf className="h-3.5 w-3.5 text-brand-300" />
                Smart crop decision support for farmers
              </p>

              <h1 className="font-display mt-6 text-balance text-4xl font-extrabold leading-[1.05] tracking-tight text-white sm:text-6xl">
                Know your field.
                <span className="block text-brand-300">Grow smarter.</span>
              </h1>

              <p className="mt-5 max-w-xl text-balance text-base leading-relaxed text-white/75 sm:text-lg">
                ANNADATA turns your field's real location, soil and weather into clear,
                honest crop recommendations — so every sowing decision has a reason behind it.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link to={homePath}>
                  <Button size="lg" className="bg-brand-400 text-forest-950 hover:bg-brand-300">
                    {authenticated ? "Open your dashboard" : "Get started"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
                <a href="#how">
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-white/35 bg-transparent text-white hover:border-white/70 hover:bg-white/10 hover:text-white"
                  >
                    See how it works
                  </Button>
                </a>
              </div>

              <p className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium text-white/60">
                <span className="inline-flex items-center gap-1.5">
                  <Compass className="h-3.5 w-3.5 text-brand-300" />
                  Field-level precision
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <CloudSun className="h-3.5 w-3.5 text-brand-300" />
                  Live weather at your land
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Trees className="h-3.5 w-3.5 text-brand-300" />
                  Honest comparisons
                </span>
              </p>
            </div>
          </div>
          <div className="pointer-events-none absolute bottom-0 inset-x-0 h-24 bg-gradient-to-t from-canvas/90 to-transparent" />
        </section>

        {/* Why / features */}
        <section id="why" className="scroll-mt-20">
          <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-24">
            <div className="max-w-2xl">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
                Why ANNADATA
              </p>
              <h2 className="font-display mt-3 text-balance text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
                Advice tied to your actual field — not averages
              </h2>
              <p className="mt-4 text-balance text-base leading-relaxed text-ink-soft">
                Every recommendation is computed from the piece of land you farm: its confirmed
                coordinates, your soil test results and the real weather at that spot.
              </p>
            </div>

            <div className="mt-12 grid gap-6 md:grid-cols-3">
              {FEATURES.map((feature) => (
                <article
                  key={feature.title}
                  className="group flex flex-col overflow-hidden rounded-card border border-border bg-surface shadow-card"
                >
                  <div className="relative aspect-[16/10] overflow-hidden">
                    <ImageWithFallback
                      src={feature.image}
                      alt={feature.alt}
                      className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                      wrapperClassName="h-full w-full bg-gradient-to-tr from-brand-100 via-forest-100 to-forest-200"
                    />
                    <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-forest-950/50 to-transparent" />
                    <div className="absolute bottom-3 left-4 flex h-10 w-10 items-center justify-center rounded-xl bg-white/95 text-brand-700 shadow-card">
                      {feature.icon}
                    </div>
                  </div>
                  <div className="flex flex-1 flex-col p-6">
                    <h3 className="font-display text-lg font-bold tracking-tight text-ink">
                      {feature.title}
                    </h3>
                    <p className="mt-2 flex-1 text-sm leading-relaxed text-ink-soft">
                      {feature.body}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* How it works */}
        <section id="how" className="scroll-mt-20 bg-surface-sunken">
          <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-24">
            <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1fr]">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-700">
                  How it works
                </p>
                <h2 className="font-display mt-3 text-balance text-3xl font-extrabold tracking-tight text-ink sm:text-4xl">
                  Three steps to a better sowing decision
                </h2>
                <p className="mt-4 max-w-lg text-balance text-base leading-relaxed text-ink-soft">
                  No complicated setup. Record your field once, then let ANNADATA do the
                  reading and the reasoning.
                </p>

                <ol className="mt-10 space-y-8">
                  {STEPS.map((step) => (
                    <li key={step.number} className="flex gap-4">
                      <span className="font-display flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-sm font-extrabold tracking-tight text-brand-700 shadow-card">
                        {step.number}
                      </span>
                      <div>
                        <h3 className="font-display text-base font-bold tracking-tight text-ink">
                          {step.title}
                        </h3>
                        <p className="mt-1 text-sm leading-relaxed text-ink-soft">{step.body}</p>
                      </div>
                    </li>
                  ))}
                </ol>

                <Link to={homePath} className="mt-10 inline-block">
                  <Button size="lg" className="bg-forest-800 text-white hover:bg-forest-900">
                    {authenticated ? "Open your dashboard" : "Get started with ANNADATA"}
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>

              <div className="relative overflow-hidden rounded-panel shadow-pop">
                <ImageWithFallback
                  src="/assets/farmer-tractor.jpg"
                  alt="A farmer on a tractor working a large green field"
                  className="aspect-[4/3] w-full object-cover"
                  wrapperClassName="aspect-[4/3] w-full bg-gradient-to-tr from-forest-800 via-forest-700 to-forest-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-forest-950/60 via-transparent to-transparent" />
                <div className="absolute bottom-5 left-5 right-5 rounded-card border border-white/15 bg-white/10 p-4 backdrop-blur">
                  <p className="text-sm font-semibold text-white">
                    Advice computed for the exact plot you farm
                  </p>
                  <p className="mt-0.5 text-xs text-white/70">
                    Location · soil · water · live weather — all per field.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* CTA band */}
        <section className="relative isolate overflow-hidden bg-forest-950">
          <ImageWithFallback
            src="/assets/crop-rows.jpg"
            alt="Straight rows of young crops on a farm"
            className="absolute inset-0 h-full w-full object-cover"
            wrapperClassName="absolute inset-0 h-full w-full bg-forest-950"
          />
          <div className="absolute inset-0 bg-forest-950/80" />
          <div className="leaf-pattern absolute inset-0 opacity-30" />
          <div className="relative mx-auto max-w-7xl px-5 py-20 text-center sm:px-8 sm:py-24">
            <h2 className="font-display mx-auto max-w-2xl text-balance text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              Your land deserves decisions backed by evidence
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-balance text-base leading-relaxed text-white/70">
              Create your first field, add its soil, and see crops ranked for your season —
              with the reasoning fully explained.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <Link to={homePath}>
                <Button size="lg" className="bg-brand-400 text-forest-950 hover:bg-brand-300">
                  {authenticated ? "Open your dashboard" : "Get started"}
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link to="/register">
                <Button
                  size="lg"
                  variant="outline"
                  className="border-white/35 bg-transparent text-white hover:border-white/70 hover:bg-white/10 hover:text-white"
                >
                  Create an account
                </Button>
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-forest-950">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-5 py-10 sm:flex-row sm:items-center sm:px-8">
          <div className="inline-flex items-center gap-2.5">
            <Logo inverted showWordmark={false} className="h-8 w-8" />
            <div>
              <p className="text-sm font-extrabold tracking-tight text-white">ANNADATA</p>
              <p className="text-xs text-white/55">Intelligent farming. Better decisions.</p>
            </div>
          </div>
          <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-white/65">
            <Link to="/login" className="transition-colors hover:text-white">
              Log in
            </Link>
            <Link to="/register" className="transition-colors hover:text-white">
              Create an account
            </Link>
            <Link to="/dashboard" className="transition-colors hover:text-white">
              Dashboard
            </Link>
          </nav>
          <p className="text-xs text-white/45">
            © {new Date().getFullYear()} ANNADATA. Decisions for real fields.
          </p>
        </div>
      </footer>
    </div>
  );
}