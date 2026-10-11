export type Status = 'pass' | 'warn' | 'fail'

export type Check = { id: string; label: string; value: number; unit: string; status: Status; message: string }

export type Lesion = { x: number; y: number; width: number; height: number; area_fraction: number }

export type Analysis = {
  id: string
  opencv_version: string
  processing_ms: number
  image: { width: number; height: number; analyzed_width: number; analyzed_height: number }
  quality: { score: number; grade: 'good' | 'fair' | 'poor'; checks: Check[] }
  leaf: { detected: boolean; coverage: number }
  tissue: { healthy: number; yellowing: number; browning: number; other: number }
  discolouration_index: number
  condition: string
  lesions: { count: number; area_fraction: number; largest_fraction: number; boxes: Lesion[] }
  findings: { level: 'info' | 'warn'; text: string }[]
  images: { overlay: string; tissue: string }
  thresholds: { exg: number }
  disclaimer: string
}

export type Entry = { analysis: Analysis; original: string; name: string; at: Date }
