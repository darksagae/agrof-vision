import { useState } from 'react'
import type { Analysis } from '../types'

const VIEWS = [
  { id: 'overlay', label: 'Annotated' },
  { id: 'tissue', label: 'Tissue map' },
  { id: 'original', label: 'Original' },
] as const

type View = (typeof VIEWS)[number]['id']

const LEGEND = [
  { label: 'Healthy', className: 'bg-[#2fa86a]' },
  { label: 'Yellowing', className: 'bg-[#f2c230]' },
  { label: 'Browning', className: 'bg-[#9c4a1e]' },
  { label: 'Other', className: 'bg-[#9aa5a0]' },
]

export function Viewer({ analysis, original }: { analysis: Analysis; original: string }) {
  const [view, setView] = useState<View>('overlay')
  const src = view === 'original' ? original : analysis.images[view]
  return (
    <section
      className="overflow-hidden rounded-3xl border border-line bg-surface text-ink shadow-(--shadow-card)"
      aria-label="Analysed image"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div role="tablist" aria-label="Image view" className="flex gap-1 rounded-xl bg-raised p-1">
          {VIEWS.map(({ id, label }) => (
            <button
              key={id}
              role="tab"
              aria-selected={view === id}
              onClick={() => setView(id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
                view === id ? 'bg-brand text-on-brand' : 'text-ink-soft hover:text-ink'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="font-mono text-xs text-ink-soft">
          {analysis.image.analyzed_width}×{analysis.image.analyzed_height} · {analysis.processing_ms} ms · OpenCV{' '}
          {analysis.opencv_version}
        </p>
      </div>
      <div className="grid place-items-center bg-raised p-3">
        <img
          src={src}
          alt={
            view === 'overlay'
              ? 'Photo with the detected leaf outlined and spots boxed'
              : view === 'tissue'
                ? 'Leaf coloured by tissue class'
                : 'Original photo'
          }
          className="max-h-[32rem] w-auto rounded-xl"
        />
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-2 border-t border-line px-4 py-3 text-xs">
        {view === 'tissue' ? (
          LEGEND.map(({ label, className }) => (
            <span key={label} className="flex items-center gap-2">
              <span className={`size-3 rounded-sm ${className}`} /> {label}
            </span>
          ))
        ) : view === 'overlay' ? (
          <>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-5 rounded-sm bg-white ring-1 ring-ink/40" /> Detected leaf
            </span>
            <span className="flex items-center gap-2">
              <span className="size-3 rounded-sm border-2 border-[#ff4d6d]" /> Spot-like area
            </span>
          </>
        ) : (
          <span className="text-ink-soft">As uploaded (after any on-device resize)</span>
        )}
      </div>
    </section>
  )
}
