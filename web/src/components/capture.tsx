import { Camera, ImageUp } from 'lucide-react'
import { useRef, useState } from 'react'

const SAMPLES = [
  { id: 'healthy', label: 'Healthy' },
  { id: 'spotted', label: 'Spotted' },
  { id: 'yellowing', label: 'Yellowing' },
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
      <h2 id="capture-title" className="text-lg font-semibold">
        Leaf photo
      </h2>

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
          dragging ? 'border-ink bg-raised' : 'border-line bg-raised'
        }`}
      >
        <span className="grid size-14 place-items-center rounded-2xl bg-brand text-on-brand">
          <ImageUp className="size-7" aria-hidden="true" />
        </span>
        <p className="mt-4 font-semibold">Drop a photo here</p>
        <p className="mt-1 text-sm text-ink-soft">One leaf, plain background, even light.</p>
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
        <p className="label-caps">Or try a sample</p>
        <div className="mt-3 grid grid-cols-3 gap-3">
          {SAMPLES.map(({ id, label }) => (
            <button
              key={id}
              type="button"
              disabled={busy}
              onClick={() => sample(id)}
              className="group overflow-hidden rounded-2xl border border-line bg-raised text-left transition-colors hover:border-ink disabled:opacity-50"
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
    </section>
  )
}
