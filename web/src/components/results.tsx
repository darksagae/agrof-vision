import { AlertTriangle, CheckCircle2, Download, Info, RotateCcw, XCircle } from 'lucide-react'
import type { Analysis, Check, Status } from '../types'
import { Viewer } from './viewer'

const pct = (value: number) => `${Math.round(value * 1000) / 10}%`

const CONDITION_STYLE: Record<string, string> = {
  'Mostly green': 'text-leaf',
  'Some discolouration': 'text-amber',
  'Extensive discolouration': 'text-rust',
  'No leaf detected': 'text-ink-soft',
}

const STATUS: Record<Status, { icon: typeof CheckCircle2; className: string; label: string }> = {
  pass: { icon: CheckCircle2, className: 'text-leaf', label: 'Pass' },
  warn: { icon: AlertTriangle, className: 'text-amber', label: 'Check' },
  fail: { icon: XCircle, className: 'text-danger', label: 'Retake' },
}

export function Results({
  analysis,
  original,
  name,
  onReset,
}: {
  analysis: Analysis
  original: string
  name: string
  onReset: () => void
}) {
  function download(href: string, filename: string) {
    const link = document.createElement('a')
    link.href = href
    link.download = filename
    link.click()
  }

  function downloadReport() {
    const { images: _images, ...report } = analysis
    const url = URL.createObjectURL(
      new Blob([JSON.stringify({ file: name, ...report }, null, 2)], { type: 'application/json' }),
    )
    download(url, `agrof-${analysis.id.slice(0, 8)}.json`)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  return (
    <div className="space-y-5">
      <Viewer analysis={analysis} original={original} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Leaf condition">
          <span className={`text-lg leading-tight font-semibold ${CONDITION_STYLE[analysis.condition] ?? ''}`}>
            {analysis.condition}
          </span>
        </Stat>
        <Stat label="Photo quality">
          <span className="flex items-baseline gap-2">
            <span className="font-mono text-2xl font-semibold">{analysis.quality.score}</span>
            <span className="text-sm text-ink-soft capitalize">{analysis.quality.grade}</span>
          </span>
        </Stat>
        <Stat label="Spot-like areas">
          <span className="font-mono text-2xl font-semibold">{analysis.lesions.count}</span>
        </Stat>
        <Stat label="Leaf in frame">
          <span className="font-mono text-2xl font-semibold">{pct(analysis.leaf.coverage)}</span>
        </Stat>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="card p-5 sm:p-6" aria-labelledby="tissue-title">
          <h3 id="tissue-title" className="font-semibold">
            Leaf surface
          </h3>
          <p className="mt-1 text-sm text-ink-soft">Share of the detected leaf area by colour class.</p>
          {analysis.leaf.detected ? (
            <>
              <div className="mt-5 flex h-4 overflow-hidden rounded-full bg-raised" aria-hidden="true">
                <span className="bg-[#2fa86a]" style={{ width: pct(analysis.tissue.healthy) }} />
                <span className="bg-[#f2c230]" style={{ width: pct(analysis.tissue.yellowing) }} />
                <span className="bg-[#9c4a1e]" style={{ width: pct(analysis.tissue.browning) }} />
                <span className="bg-[#9aa5a0]" style={{ width: pct(analysis.tissue.other) }} />
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-3">
                <Share label="Healthy green" value={analysis.tissue.healthy} swatch="bg-[#2fa86a]" />
                <Share label="Yellowing" value={analysis.tissue.yellowing} swatch="bg-[#f2c230]" />
                <Share label="Brown or dark" value={analysis.tissue.browning} swatch="bg-[#9c4a1e]" />
                <Share label="Other (glare, pale)" value={analysis.tissue.other} swatch="bg-[#9aa5a0]" />
              </dl>
              <p className="mt-4 flex items-baseline justify-between gap-3 border-t border-line pt-4 text-sm">
                <span className="text-ink-soft">Discolouration index (yellowing + brown)</span>
                <span className="font-mono font-semibold">{pct(analysis.discolouration_index)}</span>
              </p>
            </>
          ) : (
            <p className="mt-5 rounded-2xl bg-raised p-4 text-sm">
              No leaf was found, so the surface could not be measured.
            </p>
          )}
        </section>

        <section className="card p-5 sm:p-6" aria-labelledby="quality-title">
          <h3 id="quality-title" className="font-semibold">
            Capture checks
          </h3>
          <p className="mt-1 text-sm text-ink-soft">A poor photo gives unreliable measurements.</p>
          <ul className="mt-4 divide-y divide-line">
            {analysis.quality.checks.map((check) => (
              <CheckRow key={check.id} check={check} />
            ))}
          </ul>
        </section>
      </div>

      <section className="card p-5 sm:p-6" aria-labelledby="findings-title">
        <h3 id="findings-title" className="font-semibold">
          What this means
        </h3>
        <ul className="mt-4 space-y-3">
          {analysis.findings.map((finding) => (
            <li key={finding.text} className="flex gap-3 text-sm">
              {finding.level === 'warn' ? (
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber" aria-hidden="true" />
              ) : (
                <Info className="mt-0.5 size-4 shrink-0 text-leaf" aria-hidden="true" />
              )}
              {finding.text}
            </li>
          ))}
        </ul>
        <p className="mt-5 rounded-2xl bg-warn-soft p-4 text-sm">{analysis.disclaimer}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          <button type="button" className="btn btn-secondary" onClick={downloadReport}>
            <Download className="size-4" aria-hidden="true" /> Report (JSON)
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => download(analysis.images.overlay, `agrof-${analysis.id.slice(0, 8)}-annotated.jpg`)}
          >
            <Download className="size-4" aria-hidden="true" /> Annotated image
          </button>
          <button type="button" className="btn btn-primary sm:ml-auto" onClick={onReset}>
            <RotateCcw className="size-4" aria-hidden="true" /> Check another leaf
          </button>
        </div>
      </section>
    </div>
  )
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="card flex flex-col justify-between gap-2 p-4">
      <span className="label-caps">{label}</span>
      {children}
    </div>
  )
}

function Share({ label, value, swatch }: { label: string; value: number; swatch: string }) {
  return (
    <div className="rounded-2xl bg-raised p-3">
      <dt className="flex items-center gap-2 text-xs text-ink-soft">
        <span className={`size-2.5 rounded-full ${swatch}`} />
        {label}
      </dt>
      <dd className="mt-1 font-mono text-xl font-semibold">{pct(value)}</dd>
    </div>
  )
}

function CheckRow({ check }: { check: Check }) {
  const { icon: Icon, className, label } = STATUS[check.status]
  const value =
    check.unit === '%'
      ? `${check.value.toFixed(1)}%`
      : check.unit
        ? `${Math.round(check.value)} ${check.unit}`
        : Math.round(check.value)
  return (
    <li className="flex gap-3 py-3">
      <Icon className={`mt-0.5 size-5 shrink-0 ${className}`} aria-label={label} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-semibold">{check.label}</span>
          <span className="font-mono text-xs text-ink-soft">{value}</span>
        </div>
        <p className="mt-0.5 text-sm text-ink-soft">{check.message}</p>
      </div>
    </li>
  )
}
