import { AlertTriangle, Cpu, History, ScanSearch } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { analyze, health, prepareUpload } from './api'
import { Capture } from './components/capture'
import { Results } from './components/results'
import type { Entry } from './types'

const STAGES = ['Reading the photo', 'Checking capture quality', 'Finding the leaf', 'Measuring the surface']

const PIPELINE = [
  {
    title: 'Normalise',
    body: 'Decodes JPEG, PNG or WebP with EXIF orientation, rejects files over 10 MB or 40 megapixels, and resizes to 1024 px with area interpolation.',
    tech: 'cv2.imdecode · cv2.resize(INTER_AREA)',
  },
  {
    title: 'Check the capture',
    body: 'Measures lighting (LAB lightness), specular glare, sharpness on the leaf at a fixed 512 px scale, framing and resolution.',
    tech: 'COLOR_BGR2LAB · Laplacian variance',
  },
  {
    title: 'Find the leaf',
    body: 'Computes the excess-green index (2g − r − b), thresholds it with Otsu, gates by hue, keeps plant-sized components and fills enclosed spots.',
    tech: 'THRESH_OTSU · connectedComponentsWithStats · MORPH_CLOSE',
  },
  {
    title: 'Classify the surface',
    body: 'Labels every leaf pixel as healthy green, yellowing, brown or dark, or other (glare, pale) using transparent HSV rules.',
    tech: 'COLOR_BGR2HSV · inRange-style masks',
  },
  {
    title: 'Detect spots',
    body: 'Cleans the discoloured mask, rejoins patches split by veins and counts compact spots. Broad yellowing is reported separately.',
    tech: 'MORPH_OPEN · component size limits',
  },
]

export default function App() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [active, setActive] = useState<Entry | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [stage, setStage] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [opencv, setOpencv] = useState<string | null>(null)
  const results = useRef<HTMLDivElement>(null)

  useEffect(() => {
    health().then((info) => setOpencv(info?.opencv_version ?? null))
  }, [])

  useEffect(() => {
    if (!pending) return
    setStage(0)
    const timer = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 450)
    return () => clearInterval(timer)
  }, [pending])

  async function run(file: File) {
    setError(null)
    setActive(null)
    let preview: string | null = null
    try {
      const upload = await prepareUpload(file)
      preview = URL.createObjectURL(upload)
      setPending(preview)
      if (window.matchMedia('(max-width: 1023px)').matches) {
        requestAnimationFrame(() => results.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
      }
      const analysis = await analyze(upload, file.name)
      const entry = { analysis, original: preview, name: file.name, at: new Date() }
      setEntries((list) => [entry, ...list].slice(0, 12))
      setActive(entry)
    } catch (e) {
      if (preview) URL.revokeObjectURL(preview)
      setError((e as Error).message)
    } finally {
      setPending(null)
    }
  }

  return (
    <div className="min-h-dvh">
      <header className="border-b border-line">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
          <a href="/" className="flex items-center gap-2.5 rounded-lg">
            <img src="/icon.svg" alt="" className="size-8" />
            <span className="text-lg font-bold tracking-tight">
              AGROF <span className="font-medium text-ink-soft">Vision</span>
            </span>
          </a>
          <div className="flex items-center gap-4">
            <a href="#how" className="hidden text-sm font-semibold text-ink-soft hover:text-ink sm:block">
              How it works
            </a>
            <span className="flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1.5 font-mono text-xs">
              <span className={`size-2 rounded-full ${opencv ? 'bg-leaf' : 'bg-line'}`} aria-hidden="true" />
              {opencv ? `OpenCV ${opencv}` : 'Connecting…'}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-20 sm:px-6">
        <section className="flex flex-col gap-4 py-10 md:flex-row md:items-end md:justify-between md:py-14">
          <div className="max-w-2xl">
            <p className="label-caps">Leaf health screening · OpenCV AI Competition</p>
            <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl">Check a leaf in seconds.</h1>
            <p className="mt-3 text-lg text-ink-soft">
              Snap one leaf. AGROF Vision checks the photo, outlines the leaf and measures yellowing, browning and spots
              — with explainable computer vision, not a black box.
            </p>
          </div>
          <ul className="flex flex-wrap gap-2 text-xs font-semibold">
            {['Results in under a second', 'Photos never stored', 'Runs locally or on AWS Lambda'].map((t) => (
              <li key={t} className="rounded-full border border-line bg-surface px-3 py-1.5">
                {t}
              </li>
            ))}
          </ul>
        </section>

        <div className="grid items-start gap-6 lg:grid-cols-[22rem_1fr] xl:grid-cols-[24rem_1fr]">
          <div className="lg:sticky lg:top-6">
            <Capture busy={pending !== null} onFile={run} />
          </div>

          <div ref={results} className="min-w-0 scroll-mt-4" aria-live="polite" aria-busy={pending !== null}>
            {error && (
              <div
                role="alert"
                className="mb-5 flex gap-3 rounded-2xl bg-danger-soft p-4 text-sm font-semibold text-danger"
              >
                <AlertTriangle className="size-5 shrink-0" aria-hidden="true" />
                {error}
              </div>
            )}
            {pending ? (
              <Analysing preview={pending} stage={stage} />
            ) : active ? (
              <Results
                key={active.analysis.id}
                analysis={active.analysis}
                original={active.original}
                name={active.name}
                onReset={() => {
                  setActive(null)
                  window.scrollTo({ top: 0, behavior: 'smooth' })
                }}
              />
            ) : (
              <Empty />
            )}

            {entries.length > 1 && (
              <section className="mt-8" aria-labelledby="history-title">
                <h2 id="history-title" className="flex items-center gap-2 text-sm font-semibold">
                  <History className="size-4 text-ink-soft" aria-hidden="true" /> This session
                </h2>
                <ul className="mt-3 flex gap-3 overflow-x-auto pb-2">
                  {entries.map((entry) => (
                    <li key={entry.analysis.id} className="shrink-0">
                      <button
                        type="button"
                        onClick={() => setActive(entry)}
                        aria-current={entry === active}
                        className={`w-40 overflow-hidden rounded-2xl border-2 bg-surface text-left ${
                          entry === active ? 'border-leaf' : 'border-transparent'
                        }`}
                      >
                        <img src={entry.analysis.images.overlay} alt="" className="aspect-[4/3] w-full object-cover" />
                        <span className="block truncate px-3 pt-2 text-xs font-semibold">
                          {entry.analysis.condition}
                        </span>
                        <span className="block px-3 pb-2 font-mono text-[0.7rem] text-ink-soft">
                          {entry.at.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · Q
                          {entry.analysis.quality.score}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </div>

        <section id="how" className="mt-24 scroll-mt-6" aria-labelledby="how-title">
          <div className="flex items-center gap-3">
            <Cpu className="size-6 text-leaf" aria-hidden="true" />
            <h2 id="how-title" className="text-3xl font-bold tracking-tight">
              How it works
            </h2>
          </div>
          <p className="mt-2 max-w-2xl text-ink-soft">
            Five classical OpenCV stages with thresholds you can read and tune. Every number on the results page traces
            back to one of them.
          </p>
          <ol className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {PIPELINE.map(({ title, body, tech }, index) => (
              <li key={title} className="card flex flex-col p-5">
                <span className="font-mono text-sm font-semibold text-leaf">0{index + 1}</span>
                <h3 className="mt-2 font-semibold">{title}</h3>
                <p className="mt-2 flex-1 text-sm text-ink-soft">{body}</p>
                <p className="mt-4 font-mono text-[0.7rem] text-ink-soft">{tech}</p>
              </li>
            ))}
          </ol>
          <div className="mt-6 rounded-3xl border border-line bg-raised p-6 text-sm">
            <p className="font-semibold">Known limits</p>
            <p className="mt-2 text-ink-soft">
              Colour rules can be confused by purple or variegated leaves, strongly tinted light, and green backgrounds
              such as grass. Leaves that are mostly brown may not be detected. Thresholds were tuned on synthetic leaves
              and need evaluation on labelled field photos before any agronomic use.
            </p>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <p className="mx-auto max-w-7xl px-4 py-6 text-xs text-ink-soft sm:px-6">
          AGROF Vision · MIT licensed · Screening aid only — not a diagnosis.
        </p>
      </footer>
    </div>
  )
}

function Empty() {
  return (
    <div className="card flex min-h-[28rem] flex-col items-center justify-center p-10 text-center">
      <span className="grid size-16 place-items-center rounded-2xl bg-raised text-leaf">
        <ScanSearch className="size-8" aria-hidden="true" />
      </span>
      <h2 className="mt-5 text-xl font-semibold">2 · Your analysis appears here</h2>
      <p className="mt-2 max-w-sm text-sm text-ink-soft">
        Add a photo or try a sample. You’ll get an annotated image, a tissue map, capture checks and plain-language
        findings.
      </p>
    </div>
  )
}

function Analysing({ preview, stage }: { preview: string; stage: number }) {
  return (
    <div className="overflow-hidden rounded-3xl bg-panel text-panel-ink">
      <div className="relative grid place-items-center bg-black/30 p-3">
        <div className="relative">
          <img src={preview} alt="Photo being analysed" className="max-h-[32rem] w-auto rounded-xl opacity-70" />
          <div className="scan-line absolute inset-x-0 h-0.5 bg-lime shadow-[0_0_24px_4px_var(--color-lime)]" />
        </div>
      </div>
      <ol className="grid gap-2 p-5 sm:grid-cols-4">
        {STAGES.map((label, index) => (
          <li
            key={label}
            className={`flex items-center gap-2 text-sm ${index <= stage ? 'text-panel-ink' : 'text-panel-ink/40'}`}
          >
            <span
              className={`size-2 rounded-full ${index < stage ? 'bg-lime' : index === stage ? 'animate-pulse bg-lime' : 'bg-panel-line'}`}
            />
            {label}
          </li>
        ))}
      </ol>
    </div>
  )
}
