import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Card, CardHeader, EmptyState, Input, Label } from '../components/ui'
import { apiRequest } from '../lib/api'
import { formatNumber, formatRupiah, today } from '../lib/format'
import { useAuth } from '../store/auth'

interface SalesReport {
  from_date: string
  to_date: string
  rows: ReportSaleRow[]
  totals: ReportTotal
}

interface ReportSaleRow {
  period: string
  sales_count: number
  gross_revenue: string
  discount_total: string
  return_total?: string
  net_revenue: string
  net_after_return?: string
  cost_total: string
  gross_profit: string
}

interface ReportTotal {
  period: string
  sales_count: number
  gross_revenue: string
  discount_total: string
  return_total?: string
  net_revenue: string
  net_after_return?: string
  cost_total: string
  gross_profit: string
}

interface GrossProfit {
  net_revenue: string
  cost_total: string
  gross_profit: string
  sales_count: number
}

interface PaymentRow {
  method: string
  count: number
  total: string
}

interface PaymentsReport {
  from_date: string
  to_date: string
  total: string
  data: PaymentRow[]
}

interface CashierRow {
  cashier_id: string
  cashier_name?: string | null
  sales_count: number
  net_revenue: string
  cost_total: string
  gross_profit: string
}

interface CashiersReport {
  from_date: string
  to_date: string
  data: CashierRow[]
}

interface TopProductRow {
  variant_id: string
  product_name?: string | null
  sku?: string | null
  quantity_sold: string
  revenue: string
}

interface PurchasesReport {
  from_date: string
  to_date: string
  total: string
  data: { supplier_id: string | null; supplier_name: string; purchases_count: number; total: string }[]
}

const PAYMENT_LABELS: Record<string, string> = {
  cash: 'Tunai',
  transfer: 'Transfer',
  qris: 'QRIS',
  card: 'Kartu',
  other: 'Lainnya',
}

function firstOfMonth() {
  const now = today()
  return now.slice(0, 8) + '01'
}

export default function ReportsPage() {
  const hasPermission = useAuth((state) => state.hasPermission)
  const [from, setFrom] = useState(firstOfMonth())
  const [to, setTo] = useState(today())
  const [groupBy, setGroupBy] = useState('day')
  const [topBy, setTopBy] = useState('value')

  const salesQuery = useQuery({
    queryKey: ['report-sales', from, to, groupBy],
    queryFn: () =>
      apiRequest<SalesReport>(
        `/reports/sales?from=${from}&to=${to}&group_by=${groupBy}`,
      ),
  })

  const profitQuery = useQuery({
    queryKey: ['report-profit', from, to],
    queryFn: () => apiRequest<GrossProfit>(`/reports/gross-profit?from=${from}&to=${to}`),
    enabled: hasPermission('report.profit'),
  })

  const paymentsQuery = useQuery({
    queryKey: ['report-payments', from, to],
    queryFn: () => apiRequest<PaymentsReport>(`/reports/sales/payments?from=${from}&to=${to}`),
  })

  const cashiersQuery = useQuery({
    queryKey: ['report-cashiers', from, to],
    queryFn: () => apiRequest<CashiersReport>(`/reports/cashiers?from=${from}&to=${to}`),
  })

  const topQuery = useQuery({
    queryKey: ['report-top', from, to, topBy],
    queryFn: () =>
      apiRequest<{ data: TopProductRow[] }>(
        `/reports/products/top?from=${from}&to=${to}&by=${topBy}&limit=10`,
      ),
  })

  const purchasesQuery = useQuery({
    queryKey: ['report-purchases', from, to],
    queryFn: () => apiRequest<PurchasesReport>(`/reports/purchases?from=${from}&to=${to}`),
    enabled: hasPermission('report.purchase'),
  })

  const totals = salesQuery.data?.totals

  return (
    <div className="space-y-4 p-6">
      <Card>
        <CardHeader title="Filter Periode" />
        <div className="flex flex-wrap items-end gap-3 p-4">
          <div>
            <Label>Dari</Label>
            <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="w-44" />
          </div>
          <div>
            <Label>Sampai</Label>
            <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="w-44" />
          </div>
          <div>
            <Label>Kelompok</Label>
            <select
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
            >
              <option value="day">Harian</option>
              <option value="week">Mingguan</option>
              <option value="month">Bulanan</option>
            </select>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400">Penjualan Bersih</div>
          <div className="num mt-1 text-2xl font-bold text-slate-800">
            {formatRupiah(totals?.net_revenue ?? profitQuery.data?.net_revenue)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400">HPP</div>
          <div className="num mt-1 text-2xl font-bold text-slate-800">
            {formatRupiah(totals?.cost_total ?? profitQuery.data?.cost_total)}
          </div>
        </Card>
        <Card className="p-4">
          <div className="text-xs uppercase tracking-wide text-slate-400">Laba Kotor</div>
          <div className="num mt-1 text-2xl font-bold text-emerald-700">
            {formatRupiah(totals?.gross_profit ?? profitQuery.data?.gross_profit)}
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader title="Rincian Penjualan" />
        {salesQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Periode</th>
                <th className="px-4 py-2 text-right">Transaksi</th>
                <th className="px-4 py-2 text-right">Kotor</th>
                <th className="px-4 py-2 text-right">Diskon</th>
                <th className="px-4 py-2 text-right">Bersih</th>
                <th className="px-4 py-2 text-right">Laba Kotor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {salesQuery.data?.rows.map((row) => (
                <tr key={row.period} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{row.period}</td>
                  <td className="num px-4 py-2 text-right">{row.sales_count}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.gross_revenue)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.discount_total)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.net_revenue)}</td>
                  <td className="num px-4 py-2 text-right text-emerald-700">
                    {formatRupiah(row.gross_profit)}
                  </td>
                </tr>
              ))}
              {salesQuery.data?.rows.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState message="Tidak ada data pada periode ini." />
                  </td>
                </tr>
              )}
            </tbody>
            {totals && (
              <tfoot className="border-t border-slate-200 bg-slate-50 font-semibold">
                <tr>
                  <td className="px-4 py-2">Total</td>
                  <td className="num px-4 py-2 text-right">{formatNumber(totals.sales_count)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(totals.gross_revenue)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(totals.discount_total)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(totals.net_revenue)}</td>
                  <td className="num px-4 py-2 text-right text-emerald-700">
                    {formatRupiah(totals.gross_profit)}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        )}
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader title="Metode Pembayaran" />
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Metode</th>
                <th className="px-4 py-2 text-right">Transaksi</th>
                <th className="px-4 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paymentsQuery.data?.data.map((row) => (
                <tr key={row.method} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{PAYMENT_LABELS[row.method] ?? row.method}</td>
                  <td className="num px-4 py-2 text-right">{formatNumber(row.count)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.total)}</td>
                </tr>
              ))}
              {(paymentsQuery.data?.data.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={3}>
                    <EmptyState message="Tidak ada pembayaran." />
                  </td>
                </tr>
              )}
            </tbody>
            {paymentsQuery.data && (
              <tfoot className="border-t border-slate-200 bg-slate-50 font-semibold">
                <tr>
                  <td className="px-4 py-2">Total</td>
                  <td className="px-4 py-2" />
                  <td className="num px-4 py-2 text-right">{formatRupiah(paymentsQuery.data.total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </Card>

        <Card className="overflow-hidden">
          <CardHeader
            title="Produk Terlaris"
            actions={
              <select
                className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
                value={topBy}
                onChange={(e) => setTopBy(e.target.value)}
              >
                <option value="value">Berdasarkan Nilai</option>
                <option value="quantity">Berdasarkan Jumlah</option>
              </select>
            }
          />
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Produk</th>
                <th className="px-4 py-2 text-right">Terjual</th>
                <th className="px-4 py-2 text-right">Pendapatan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {topQuery.data?.data.map((row) => (
                <tr key={row.variant_id} className="hover:bg-slate-50">
                  <td className="px-4 py-2">
                    <div className="font-medium">{row.product_name}</div>
                    <div className="text-xs text-slate-400">{row.sku}</div>
                  </td>
                  <td className="num px-4 py-2 text-right">{formatNumber(row.quantity_sold)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.revenue)}</td>
                </tr>
              ))}
              {(topQuery.data?.data.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={3}>
                    <EmptyState message="Belum ada penjualan." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader title="Penjualan per Kasir" />
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Kasir</th>
                <th className="px-4 py-2 text-right">Transaksi</th>
                <th className="px-4 py-2 text-right">Bersih</th>
                <th className="px-4 py-2 text-right">Laba Kotor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {cashiersQuery.data?.data.map((row) => (
                <tr key={row.cashier_id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{row.cashier_name ?? '-'}</td>
                  <td className="num px-4 py-2 text-right">{formatNumber(row.sales_count)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.net_revenue)}</td>
                  <td className="num px-4 py-2 text-right text-emerald-700">
                    {formatRupiah(row.gross_profit)}
                  </td>
                </tr>
              ))}
              {(cashiersQuery.data?.data.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={4}>
                    <EmptyState message="Belum ada penjualan." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>

        {hasPermission('report.purchase') && (
        <Card className="overflow-hidden">
          <CardHeader title="Pembelian per Supplier" />
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Supplier</th>
                <th className="px-4 py-2 text-right">Dokumen</th>
                <th className="px-4 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {purchasesQuery.data?.data.map((row) => (
                <tr key={row.supplier_id ?? row.supplier_name} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{row.supplier_name}</td>
                  <td className="num px-4 py-2 text-right">{formatNumber(row.purchases_count)}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.total)}</td>
                </tr>
              ))}
              {(purchasesQuery.data?.data.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={3}>
                    <EmptyState message="Belum ada pembelian." />
                  </td>
                </tr>
              )}
            </tbody>
            {purchasesQuery.data && (
              <tfoot className="border-t border-slate-200 bg-slate-50 font-semibold">
                <tr>
                  <td className="px-4 py-2">Total</td>
                  <td className="px-4 py-2" />
                  <td className="num px-4 py-2 text-right">{formatRupiah(purchasesQuery.data.total)}</td>
                </tr>
              </tfoot>
            )}
          </table>
        </Card>
        )}
      </div>
    </div>
  )
}
