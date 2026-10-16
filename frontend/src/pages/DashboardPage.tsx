import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { BarChart } from '../components/BarChart'
import { Card, CardHeader, EmptyState } from '../components/ui'
import { apiRequest } from '../lib/api'
import { formatNumber, formatRupiah, today } from '../lib/format'
import type { DashboardData, SalesTrendReport, TopProduct } from '../types'

const RANGE_OPTIONS = [7, 14, 30]

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  const offset = d.getTimezoneOffset()
  return new Date(d.getTime() - offset * 60000).toISOString().slice(0, 10)
}

function shortDate(iso: string): string {
  const [, month, day] = iso.split('-')
  return `${day}/${month}`
}

export default function DashboardPage() {
  const date = today()
  const [range, setRange] = useState(14)
  const from = daysAgo(range - 1)

  const dashboardQuery = useQuery({
    queryKey: ['dashboard', date],
    queryFn: () => apiRequest<DashboardData>(`/reports/dashboard?target=${date}`),
  })

  const topQuery = useQuery({
    queryKey: ['top-products'],
    queryFn: () => apiRequest<{ data: TopProduct[] }>('/reports/top-products?limit=10'),
  })

  const trendQuery = useQuery({
    queryKey: ['dashboard-trend', from, date],
    queryFn: () =>
      apiRequest<SalesTrendReport>(`/reports/sales?from=${from}&to=${date}&group_by=day`),
  })

  const data = dashboardQuery.data

  const trendMap = new Map((trendQuery.data?.rows ?? []).map((row) => [row.period, row]))
  const trendData = Array.from({ length: range }, (_, index) => {
    const iso = daysAgo(range - 1 - index)
    const row = trendMap.get(iso)
    return { label: shortDate(iso), value: Number(row?.net_revenue ?? 0) }
  })
  const trendTotal = trendData.reduce((sum, point) => sum + point.value, 0)

  return (
    <div className="space-y-4 p-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Dashboard</h1>
        <p className="text-sm text-slate-500">Ringkasan operasional hari ini</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Transaksi" value={formatNumber(data?.sales_count ?? 0)} />
        <Stat label="Omzet Kotor" value={formatRupiah(data?.gross_revenue)} />
        <Stat label="Penjualan Bersih" value={formatRupiah(data?.net_revenue)} />
        <Stat label="Stok Menipis" value={formatNumber(data?.low_stock_count ?? 0)} accent />
      </div>

      <Card>
        <CardHeader
          title="Tren Penjualan"
          actions={
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-500">
                Total {formatRupiah(trendTotal)}
              </span>
              <select
                className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
                value={range}
                onChange={(e) => setRange(Number(e.target.value))}
              >
                {RANGE_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option} hari
                  </option>
                ))}
              </select>
            </div>
          }
        />
        {trendQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : trendTotal === 0 ? (
          <EmptyState message="Belum ada penjualan pada periode ini." />
        ) : (
          <BarChart data={trendData} valueFormatter={(value) => formatRupiah(value)} />
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Metode Pembayaran" />
          {data && data.payment_breakdown.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {data.payment_breakdown.map((row) => (
                <li key={row.method} className="flex items-center justify-between px-4 py-3 text-sm">
                  <span className="capitalize text-slate-600">{row.method}</span>
                  <span className="text-slate-400">{row.count} trx</span>
                  <span className="num font-medium">{formatRupiah(row.amount)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="Belum ada transaksi hari ini." />
          )}
        </Card>

        <Card>
          <CardHeader title="Produk Terlaris (30 hari)" />
          {topQuery.data && topQuery.data.data.length > 0 ? (
            <ul className="divide-y divide-slate-100">
              {topQuery.data.data.map((row) => (
                <li key={row.variant_id} className="flex items-center justify-between px-4 py-3 text-sm">
                  <span className="min-w-0 flex-1 truncate text-slate-700">
                    {row.product_name}
                    <span className="ml-2 text-xs text-slate-400">{row.sku}</span>
                  </span>
                  <span className="text-slate-400">{formatNumber(row.quantity_sold)}</span>
                  <span className="num ml-4 font-medium">{formatRupiah(row.revenue)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="Belum ada data produk terlaris." />
          )}
        </Card>
      </div>
    </div>
  )
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string
  value: string
  accent?: boolean
}) {
  return (
    <Card className="p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`num mt-1 text-2xl font-bold ${accent ? 'text-amber-600' : 'text-slate-800'}`}>
        {value}
      </div>
    </Card>
  )
}
