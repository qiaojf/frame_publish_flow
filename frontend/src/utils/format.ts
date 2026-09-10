export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

export function formatBytes(value?: number): string {
  if (value === undefined || value === null) return '—'
  if (value === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const exponent = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1)
  return `${(value / 1024 ** exponent).toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`
}

export function pickFilename(header?: string, fallback = 'video.mp4'): string {
  const match = header?.match(/filename\*?=(?:UTF-8''|\")?([^\";]+)/i)
  return match ? decodeURIComponent(match[1].replace(/\"/g, '').trim()) : fallback
}
