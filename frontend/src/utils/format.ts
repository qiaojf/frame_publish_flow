import { getCurrentLocale } from '@/locales'

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(getCurrentLocale(), {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: getCurrentLocale() === 'en-US',
    timeZone: import.meta.env.VITE_DISPLAY_TIME_ZONE || 'Asia/Tokyo',
  }).format(date)
}

export function formatBytes(value?: number): string {
  if (value === undefined || value === null) return '—'
  if (value === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exponent = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  const amount = value / 1024 ** exponent
  return `${new Intl.NumberFormat(getCurrentLocale(), { maximumFractionDigits: exponent === 0 ? 0 : 1 }).format(amount)} ${units[exponent]}`
}

export function pickFilename(header?: string, fallback = 'video.mp4'): string {
  const match = header?.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i)
  return match ? decodeURIComponent(match[1].replace(/\"/g, '').trim()) : fallback
}
