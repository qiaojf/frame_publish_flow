export function cleanUrl(value?: string | null): string {
  return typeof value === 'string' ? value.trim() : ''
}
