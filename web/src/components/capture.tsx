import { Camera, ImageUp, ShieldCheck, Sun, Focus, Leaf, Maximize } from 'lucide-react'
import { useRef, useState } from 'react'

const SAMPLES = [
  { id: 'healthy', label: 'Healthy' },
  { id: 'spotted', label: 'Spotted' },
  { id: 'yellowing', label: 'Yellowing' },
]

const TIPS = [
  { icon: Leaf, text: 'One leaf, against a plain background' },
  { icon: Maximize, text: 'Fill about half of the frame' },
  { icon: Sun, text: 'Even daylight, no harsh sun or flash' },
  { icon: Focus, text: 'Hold steady and tap the leaf to focus' },
]

export function Capture({ busy, onFile }: { busy: boolean; onFile: (file: File) => void }) {
  const picker = useRef<HTMLInputElement>(null)
  const camera = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function take(files: FileList | null) {
    const file = files?.[0]
    if (file) onFile(file)
  }

  async function sample(id: string) {
    const response = await fetch(`/samples/${id}.jpg`)
    const blob = await response.blob()
    onFile(new File([blob], `${id}-sample.jpg`, { type: 'image/jpeg' }))
  }

  return (
    <section className="card p-5 sm:p-6" aria-labelledby="capture-title">
      <div className="flex items-center justify-between">
        <h2 id="capture-title" className="text-lg font-semibold">
          1 · Add a leaf photo
        </h2>
        <span className="label-caps">JPEG · PNG · WebP</span>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          if (!busy) take(e.dataTransfer.files)
        }}
        className={`mt-4 flex flex-col items-center rounded-2xl border-2 border-dashed px-5 py-8 text-center transition-colors ${
          dragging ? 'border-leaf bg-ok-soft' : 'border-line bg-raised'
        }`}
      >
        <span className="grid size-14 place-items-center rounded-2xl bg-forest text-on-forest">
          <ImageUp className="size-7" aria-hidden="true" />
        </span>
        <p className="mt-4 font-semibold">Drop a photo here</p>
        <p className="mt-1 text-sm text-ink-soft">Up to 10 MB. Large photos are resized on your device first.</p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <button type="button" className="btn btn-primary" disabled={busy} onClick={() => picker.current?.click()}>
            <ImageUp className="size-4" aria-hidden="true" /> Choose photo
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => camera.current?.click()}>
            <Camera className="size-4" aria-hidden="true" /> Use camera
          </button>
        </div>
        <input
          ref={picker}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          tabIndex={-1}
          aria-label="Choose a leaf photo"
          onChange={(e) => (take(e.target.files), (e.target.value = ''))}
        />
        <input
          ref={camera}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          tabIndex={-1}
          aria-label="Take a leaf photo"
          onChange={(e) => (take(e.target.files), (e.target.value = ''))}
        />
      </div>

      <div className="mt-6">
        <p className="label-caps">Or try a synthetic sample</p>
        <div className="mt-3 grid grid-cols-3 gap-3">
          {SAMPLES.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              disabled={busy}
              onClick={() => sample(id)}
              className="group overflow-hidden rounded-2xl border border-line bg-raised text-left transition-colors hover:border-leaf disabled:opacity-50"
            >
              <img
                src={`/samples/${id}.jpg`}
                alt=""
                className="aspect-[4/3] w-full object-cover transition-transform duration-300 group-hover:scale-105"
              />
              <span className="block px-3 py-2 text-xs font-semibold">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-2xl bg-raised p-4">
        <p className="label-caps">For a reliable reading</p>
        <ul className="mt-3 grid gap-2.5 text-sm">
          {TIPS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-center gap-3">
              <Icon className="size-4 shrink-0 text-leaf" aria-hidden="true" />
              {text}
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-4 flex items-center gap-2 text-xs text-ink-soft">
        <ShieldCheck className="size-4 shrink-0 text-leaf" aria-hidden="true" />
        Photos are analysed in memory and never stored.
      </p>
    </section>
  )
}
