import type { Analysis } from './types'

const MAX_EDGE = 2048
const SHRINK_ABOVE_BYTES = 2.5 * 1024 * 1024

/** Shrinks big phone photos in the browser so uploads stay fast on slow networks. */
export async function prepareUpload(file: File): Promise<Blob> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    throw new Error('Choose a JPEG, PNG or WebP photo.')
  }
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height))
    if (scale === 1 && file.size <= SHRINK_ABOVE_BYTES) {
      bitmap.close()
      return file
    }
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (blob) => (blob ? resolve(blob) : reject(new Error('Could not prepare the photo.'))),
        'image/jpeg',
        0.9,
      ),
    )
  } catch (error) {
    if (file.size > 10 * 1024 * 1024) throw new Error('Photos must be 10 MB or smaller.')
    if (error instanceof Error && error.message.startsWith('Could not')) throw error
    return file
  }
}

export async function analyze(file: Blob, name: string): Promise<Analysis> {
  const body = new FormData()
  body.append('image', file, name)
  let response: Response
  try {
    response = await fetch('/api/analyze', { method: 'POST', body })
  } catch {
    throw new Error('Could not reach the analyser. Check your connection and try again.')
  }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.error ?? 'Analysis failed. Please try another photo.')
  return data as Analysis
}

export async function health(): Promise<{ opencv_version: string } | null> {
  try {
    const response = await fetch('/api/health')
    return response.ok ? await response.json() : null
  } catch {
    return null
  }
}
