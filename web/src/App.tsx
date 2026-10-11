import { AlertTriangle, History, ScanSearch } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { analyze, prepareUpload } from './api'
import { Capture } from './components/capture'
import { Results } from './components/results'
import type { Entry } from './types'

const STAGES = ['Reading the photo', 'Checking capture quality', 'Finding the leaf', 'Measuring the surface']

export default function App() {
  const [entries, setEntries] = useState<Entry[]>([])
  const [active, setActive] = useState<Entry | null>(null)
  const [pending, setPending] = useState<string | null>(null)
  const [stage, setStage] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const results = useRef<HTMLDivElement>(null)

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
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6 pb-16 sm:px-6 lg:py-8">
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
                          entry === active ? 'border-ink' : 'border-transparent'
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
      </main>

      <footer className="border-t border-line">
        <p className="mx-auto max-w-7xl px-4 py-6 text-xs text-ink-soft sm:px-6">
          Screening aid only — not a diagnosis. Photos are analysed in memory and never stored.
        </p>
      </footer>
    </div>
  )
}

function Empty() {
  return (
    <div className="card hidden min-h-[24rem] flex-col items-center justify-center p-10 text-center lg:flex">
      <span className="grid size-16 place-items-center rounded-2xl bg-raised text-ink">
        <ScanSearch className="size-8" aria-hidden="true" />
      </span>
      <p className="mt-4 text-ink-soft">Results appear here.</p>
    </div>
  )
}

function Analysing({ preview, stage }: { preview: string; stage: number }) {
  return (
    <div className="overflow-hidden rounded-3xl border border-line bg-surface text-ink shadow-(--shadow-card)">
      <div className="relative grid place-items-center bg-raised p-3">
        <div className="relative">
          <img src={preview} alt="Photo being analysed" className="max-h-[32rem] w-auto rounded-xl opacity-70" />
          <div className="scan-line absolute inset-x-0 h-0.5 bg-brand shadow-[0_0_18px_3px_rgb(255_255_255/0.9)]" />
        </div>
      </div>
      <ol className="grid gap-2 p-5 sm:grid-cols-4">
        {STAGES.map((label, index) => (
          <li
            key={label}
            className={`flex items-center gap-2 text-sm ${index <= stage ? 'text-ink' : 'text-ink-soft/60'}`}
          >
            <span
              className={`size-2 rounded-full ${index < stage ? 'bg-brand' : index === stage ? 'animate-pulse bg-brand' : 'bg-line'}`}
            />
            {label}
          </li>
        ))}
      </ol>
    </div>
  )
}
