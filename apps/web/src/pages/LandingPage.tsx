import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Logo, LogoMark } from '../components/ui/Logo'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import { TechLogos } from '../components/landing/TechLogos'

/* ---------------------------------- Icons ---------------------------------- */

function Icon({ name, className = 'h-5 w-5' }: { name: string; className?: string }) {
  const paths: Record<string, string> = {
    camera:
      'M2 7a2 2 0 0 1 2-2h2l1.5-2h5L14 5h2a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V7zm10 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
    focus:
      'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM12 2v3M12 19v3M17.5 4.8l-2 2.2M8.5 17l-2 2.2M22 12h-3M5 12H2',
    fingerprint:
      'M12 11c0 2 .5 3.5 1.5 5M8 12c0-2.2 1.8-4 4-4s4 1.8 4 4c0 3-.8 5.5-2.2 7.4M5 14c-.6 1.9-.8 3.7-.5 5.5M12 15v3.5M7 16.5c0 2 .3 3.5 1 5M17 7.5A5.6 5.6 0 0 0 6 11c0 3 .6 5.8 1.8 8.2M15 8.4A4 4 0 0 0 8 12M15 17c-1 1.8-1.7 3.5-2 5',
    refresh:
      'M4 12a8 8 0 1 1 2.34 5.66M4 12v-6M4 12h6',
    chart: 'M4 20h16M6 16v-5M10 16V8M14 16v-7M18 16v-4',
    flask:
      'M9 3h6M10 3v6l-5.5 8a2.5 2.5 0 0 0 2.1 3.8h10.8a2.5 2.5 0 0 0 2.1-3.8L14 9V3M7.2 14h9.6',
    arrowRight: 'M5 12h14M13 5l7 7-7 7',
    check: 'M20 6L9 17l-5-5',
    sparkles:
      'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15z',
  }
  const d = paths[name]
  if (!d) return null
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  )
}

/* ------------------------------- Scroll reveal ------------------------------ */

function Reveal({ children, delay = 0 }: { children: ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (!('IntersectionObserver' in window)) {
      setVisible(true)
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true)
            observer.disconnect()
          }
        }
      },
      { threshold: 0.12 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className="transition-all duration-700 ease-out motion-reduce:transition-none"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        transitionDelay: `${delay}ms`,
      }}
    >
      {children}
    </div>
  )
}

/* ------------------------------- Hero mock ---- ----------------------------- */

const FRUITS = [
  { left: '18%', top: '34%', delay: '0s', sway: '5.5s', label: 'Fruit #7', score: 98 },
  { left: '42%', top: '22%', delay: '1.2s', sway: '7s', label: 'Fruit #7', score: 96 },
  { left: '63%', top: '41%', delay: '2.4s', sway: '6s', label: 'Fruit #7', score: 97 },
  { left: '52%', top: '64%', delay: '0.6s', sway: '8s', label: 'Fruit #7', score: 95 },
  { left: '30%', top: '72%', delay: '1.8s', sway: '6.5s', label: 'Fruit #7', score: 99 },
]

function HeroMock() {
  return (
    <div className="relative mx-auto w-full max-w-3xl">
      <div
        className="blob blob-orange blob-slow"
        style={{ width: '28rem', height: '28rem', left: '-6rem', top: '-10rem' }}
      />
      <div
        className="blob blob-pink blob-fast"
        style={{ width: '24rem', height: '24rem', right: '-8rem', bottom: '-8rem' }}
      />
      <div className="glass ring-glow relative overflow-hidden rounded-3xl p-3">
        <div className="noise pointer-events-none absolute inset-0" />
        <div className="rounded-2xl bg-surface-950/70 p-3">
          <div className="flex items-center justify-between px-1 pb-2">
            <div className="flex items-center gap-2">
              <LogoMark className="h-5 w-5" />
              <span className="text-xs font-medium text-surface-300">Orchard A — North Row</span>
            </div>
            <span className="flex items-center gap-1.5 rounded-full bg-orchard-500/15 px-2.5 py-1 text-[10px] font-medium text-orchard-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              LIVE
            </span>
          </div>
          <div className="relative aspect-video overflow-hidden rounded-xl bg-gradient-to-br from-surface-900 via-surface-800 to-surface-900">
            <div className="blob blob-emerald" style={{ width: '18rem', height: '18rem', left: '20%', top: '-30%', opacity: 0.35 }} />
            <div className="blob blob-sky" style={{ width: '16rem', height: '16rem', right: '8%', bottom: '-40%', opacity: 0.3 }} />
            {FRUITS.map((f, i) => (
              <div
                key={i}
                className="absolute"
                style={{ left: f.left, top: f.top, animation: `sway ${f.sway} ease-in-out ${f.delay} infinite` }}
              >
                <span
                  className="absolute inset-0 -m-2 rounded-3xl border"
                  style={{ borderColor: 'rgba(251,191,36,0.75)', animation: 'pulse-ring 2.4s ease-in-out infinite' }}
                />
                <div className="h-3 w-3 rounded-full bg-orchard-300 shadow-[0_0_12px_rgba(251,191,36,0.9)]" />
              </div>
            ))}
            <div className="absolute bottom-3 left-3 rounded-lg bg-black/55 px-2 py-1 backdrop-blur">
              <p className="text-[10px] text-surface-200">17 fruits · 0 occluded · tracking stable</p>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-2">
            {[
              ['Detected', 17, 'text-orchard-300'],
              ['ID Recovery', '0.92', 'text-emerald-300'],
              ['Count MAE', '1.3', 'text-orchard-300'],
              ['ID Switches', 3, 'text-surface-200'],
            ].map(([label, value, cls]) => (
              <div key={label as string} className="rounded-lg border border-surface-800 bg-surface-900/60 px-2.5 py-2">
                <p className="text-[10px] text-surface-500">{label}</p>
                <p className={`mt-0.5 font-mono text-sm font-semibold ${cls}`}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* --------------------------------- Features -------------------------------- */

const FEATURES = [
  {
    icon: 'camera',
    title: 'Per-frame detection',
    body: 'Fruit boxes are emitted every frame by pluggable detectors — mock-first by default, real models (YOLO) drop in behind the same interface.',
  },
  {
    icon: 'focus',
    title: 'Camera motion compensation',
    body: 'Pan-tilt drift is estimated and corrected before tracking, so swaying cameras never corrupt trajectories.',
  },
  {
    icon: 'fingerprint',
    title: 'Identity learning',
    body: 'Quality-aware prototypes are learned per fruit, embedding each mango into its own persistent identity.',
  },
  {
    icon: 'refresh',
    title: 'Re-identification',
    body: 'After occlusion or track loss, identity memory recovers the exact same fruit — no double counting.',
  },
  {
    icon: 'chart',
    title: 'Counting & analytics',
    body: 'Live per-frame aggregates, confidence distributions, embedding projections, and processing-speed telemetry.',
  },
  {
    icon: 'flask',
    title: 'Evaluation harness',
    body: 'Benchmark every run against ground truth with IDF1, HOTA, ID switches, fragmentation, count MAE/MAPE.',
  },
]

/* --------------------------------- Pipeline -------------------------------- */

const STEPS = [
  { n: '01', title: 'Detect', body: 'Fruit bounding boxes per frame over the whole orchard video.' },
  { n: '02', title: 'Compensate', body: 'Estimate pan/tilt drift and shift boxes before tracking.' },
  { n: '03', title: 'Track', body: 'Associate boxes into stable fruit trajectories across frames.' },
  { n: '04', title: 'Remember', body: 'Build quality-aware identity prototypes for every fruit.' },
  { n: '05', title: 'Re-identify', body: 'Query identity memory to recover fruit after occlusions.' },
  { n: '06', title: 'Evaluate', body: 'Score IDF1, HOTA, count MAE/MAPE and identity recovery.' },
]

/* ------------------------------ Page sections ------------------------------ */

function Navbar() {
  return (
    <header className="fixed inset-x-0 top-0 z-40">
      <div className="mx-auto max-w-6xl px-4 pt-4">
        <nav className="glass flex items-center justify-between rounded-2xl px-4 py-2.5">
          <Link to="/" className="font-display flex items-center gap-2 text-sm font-semibold">
            <LogoMark className="h-7 w-7" />
            OrchardVision
          </Link>
          <div className="hidden items-center gap-6 text-sm text-surface-400 md:flex">
            <a href="#features" className="transition-colors hover:text-surface-100">
              Features
            </a>
            <a href="#pipeline" className="transition-colors hover:text-surface-100">
              How it works
            </a>
            <a href="#stack" className="transition-colors hover:text-surface-100">
              Stack
            </a>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              to="/dashboard"
              className="bg-mango rounded-full px-4 py-2 text-sm font-semibold text-surface-950 shadow-[0_8px_24px_-8px_rgba(249,115,22,0.6)] transition-transform hover:scale-[1.03] active:scale-[0.98]"
            >
              Launch console
            </Link>
          </div>
        </nav>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-28">
      <div
        className="blob blob-orange blob-slow"
        style={{ width: '40rem', height: '40rem', left: '-12rem', top: '-16rem' }}
      />
      <div
        className="blob blob-sky blob-fast"
        style={{ width: '30rem', height: '30rem', right: '-10rem', top: '4rem', opacity: 0.3 }}
      />
      <div
        className="blob blob-pink"
        style={{ width: '26rem', height: '26rem', left: '30%', bottom: '-12rem', opacity: 0.3 }}
      />
      <div className="relative mx-auto max-w-6xl px-4">
        <div className="mx-auto max-w-3xl text-center">
          <Reveal>
            <span className="glass inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium text-orchard-300">
              <Icon name="sparkles" className="h-3.5 w-3.5" />
              Self-supervised identity learning for orchards
            </span>
          </Reveal>
          <Reveal delay={80}>
            <h1 className="font-display mt-6 text-4xl font-bold leading-[1.05] tracking-tight text-surface-50 sm:text-6xl">
              Every mango, <span className="text-gradient">counted once.</span>
            </h1>
          </Reveal>
          <Reveal delay={160}>
            <p className="mx-auto mt-6 max-w-2xl text-base text-surface-400 sm:text-lg">
              OrchardVision tracks fruit across swaying, pan-tilt camera feeds — learning a
              persistent identity for each mango so counts stay correct over hours of occlusions,
              wind, and motion.
            </p>
          </Reveal>
          <Reveal delay={240}>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                to="/dashboard"
                className="bg-mango flex w-full items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-surface-950 shadow-[0_12px_32px_-10px_rgba(249,115,22,0.65)] transition-transform hover:scale-[1.03] active:scale-[0.98] sm:w-auto"
              >
                Open the console
                <Icon name="arrowRight" className="h-4 w-4" />
              </Link>
              <a
                href="#pipeline"
                className="glass flex w-full items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-surface-200 transition-colors hover:text-surface-50 sm:w-auto"
              >
                See the pipeline
              </a>
            </div>
          </Reveal>
        </div>
        <Reveal delay={320}>
          <div className="mt-16 sm:mt-20">
            <HeroMock />
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Stack() {
  return (
    <section id="stack" className="relative py-20">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <div className="text-center">
            <p className="text-xs font-medium tracking-widest text-surface-500 uppercase">
              Powered by
            </p>
            <h2 className="font-display mt-2 text-2xl font-semibold text-surface-50">
              A battle-tested stack
            </h2>
          </div>
        </Reveal>
        <Reveal delay={120}>
          <div className="mt-10">
            <TechLogos />
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Stats() {
  const stats = [
    ['6', 'Pipeline stages', 'detect → re-identify'],
    ['0', 'Labeled frames', 'fully self-supervised'],
    ['1:1', 'Fruit identity', 'each mango, its own ID'],
    ['24/7', 'Orchard eyes', 'long-run monitoring'],
  ]
  return (
    <section className="relative py-10">
      <div className="mx-auto max-w-6xl px-4">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {stats.map(([value, label, sub], i) => (
            <Reveal key={label} delay={i * 80}>
              <div className="glass card-glow cursor-pointer rounded-2xl p-6 text-center">
                <p className="text-gradient font-display text-4xl font-bold">{value}</p>
                <p className="mt-2 text-sm font-medium text-surface-200">{label}</p>
                <p className="mt-1 text-xs text-surface-500">{sub}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Features() {
  return (
    <section id="features" className="relative py-20">
      <div
        className="blob blob-pink blob-slow"
        style={{ width: '30rem', height: '30rem', right: '-12rem', top: '6rem', opacity: 0.22 }}
      />
      <div className="relative mx-auto max-w-6xl px-4">
        <Reveal>
          <div className="max-w-2xl">
            <p className="text-xs font-medium tracking-widest text-orchard-400 uppercase">
              Features
            </p>
            <h2 className="font-display mt-2 text-3xl font-semibold tracking-tight text-surface-50 sm:text-4xl">
              Built for the messy realities of an orchard
            </h2>
            <p className="mt-4 text-surface-400">
              Cameras sway, fruit hides behind leaves, and occlusions happen constantly.
              OrchardVision was designed around those failures — not around clean demo footage.
            </p>
          </div>
        </Reveal>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, i) => (
            <Reveal key={feature.title} delay={(i % 3) * 90}>
              <div className="glass card-glow group h-full cursor-pointer rounded-2xl p-6">
                <div className="bg-mango-soft flex h-11 w-11 items-center justify-center rounded-xl text-orchard-300 transition-transform duration-300 group-hover:scale-110">
                  <Icon name={feature.icon} />
                </div>
                <h3 className="font-display mt-4 text-lg font-semibold text-surface-50">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-surface-400">{feature.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Pipeline() {
  return (
    <section id="pipeline" className="relative py-20">
      <div
        className="blob blob-emerald blob-slow"
        style={{ width: '28rem', height: '28rem', left: '-10rem', bottom: '0', opacity: 0.18 }}
      />
      <div className="relative mx-auto max-w-6xl px-4">
        <Reveal>
          <div className="text-center">
            <p className="text-xs font-medium tracking-widest text-orchard-400 uppercase">
              How it works
            </p>
            <h2 className="font-display mt-2 text-3xl font-semibold tracking-tight text-surface-50 sm:text-4xl">
              Six stages from raw feed to reliable counts
            </h2>
          </div>
        </Reveal>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((step, i) => (
            <Reveal key={step.n} delay={(i % 3) * 90}>
              <div className="glass card-glow relative h-full cursor-pointer overflow-hidden rounded-2xl p-6">
                <span className="text-gradient font-display absolute top-3 right-5 text-3xl font-bold opacity-40">
                  {step.n}
                </span>
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orchard-500/15 font-mono text-sm font-semibold text-orchard-300">
                  {step.n}
                </div>
                <h3 className="font-display mt-4 text-lg font-semibold text-surface-50">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-surface-400">{step.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

function Cta() {
  return (
    <section className="relative py-20">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal>
          <div className="bg-mango relative overflow-hidden rounded-3xl px-6 py-16 text-center shadow-[0_24px_80px_-24px_rgba(249,115,22,0.55)] sm:px-16">
            <div className="noise pointer-events-none absolute inset-0" />
            <h2 className="font-display relative text-3xl font-bold tracking-tight text-surface-950 sm:text-4xl">
              Stop guessing your yield.
            </h2>
            <p className="relative mx-auto mt-4 max-w-xl text-sm text-orchard-900 sm:text-base">
              Spin up the console, upload an orchard video, and watch identities form, persist, and
              re-cover through every occlusion.
            </p>
            <div className="relative mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link
                to="/dashboard"
                className="flex w-full items-center justify-center gap-2 rounded-full bg-surface-950 px-7 py-3 text-sm font-semibold text-surface-50 shadow-lg transition-transform hover:scale-[1.03] active:scale-[0.98] sm:w-auto"
              >
                Launch the console
                <Icon name="arrowRight" className="h-4 w-4" />
              </Link>
              <a
                href="#features"
                className="flex w-full items-center justify-center gap-2 rounded-full border border-orchard-800/40 px-7 py-3 text-sm font-semibold text-surface-950 transition-colors hover:bg-orchard-100/40 sm:w-auto"
              >
                Explore features
              </a>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="relative py-12">
      <div className="mx-auto max-w-6xl px-4">
        <div className="glass rounded-2xl px-6 py-8">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div>
              <Logo />
              <p className="mt-2 max-w-xs text-xs text-surface-500">
                Visibility-aware, self-supervised identity learning for long-term fruit tracking
                and counting in mango orchards.
              </p>
            </div>
            <div className="flex gap-10 text-sm">
              <div className="space-y-2">
                <p className="text-xs font-medium tracking-widest text-surface-500 uppercase">Explore</p>
                <ul className="space-y-1.5 text-surface-400">
                  <li>
                    <a href="#features" className="transition-colors hover:text-surface-100">Features</a>
                  </li>
                  <li>
                    <a href="#pipeline" className="transition-colors hover:text-surface-100">Pipeline</a>
                  </li>
                  <li>
                    <a href="#stack" className="transition-colors hover:text-surface-100">Stack</a>
                  </li>
                </ul>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium tracking-widest text-surface-500 uppercase">Product</p>
                <ul className="space-y-1.5 text-surface-400">
                  <li>
                    <Link to="/dashboard" className="transition-colors hover:text-surface-100">Console</Link>
                  </li>
                  <li>
                    <Link to="/dashboard" className="transition-colors hover:text-surface-100">Dashboard</Link>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div className="mt-8 flex flex-col items-center justify-between gap-2 border-t border-surface-800 pt-5 text-xs text-surface-600 sm:flex-row">
            <span>© 2026 OrchardVision Research</span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" aria-hidden="true" />
              Mock-first inference, ready for real models
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}

/* ----------------------------------- Page ----------------------------------- */

export function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-clip">
      <Navbar />
      <main>
        <Hero />
        <Stats />
        <Features />
        <Pipeline />
        <Stack />
        <Cta />
      </main>
      <Footer />
    </div>
  )
}