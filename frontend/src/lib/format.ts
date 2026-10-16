export function formatRupiah(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return 'Rp 0'
  const num = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(num)) return 'Rp 0'
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(num)
}

export function formatNumber(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return '0'
  const num = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(num)) return '0'
  return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 4 }).format(num)
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  return new Intl.DateTimeFormat('id-ID', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return '-'
  const [year, month, day] = value.slice(0, 10).split('-').map(Number)
  if (!year || !month || !day) return value
  return new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium' }).format(
    new Date(year, month - 1, day),
  )
}

export function today(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  return new Date(now.getTime() - offset * 60 * 1000).toISOString().slice(0, 10)
}
