import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button, Card, CardHeader, EmptyState, ErrorText, Input, Label } from '../components/ui'
import { apiRequest, RequestError } from '../lib/api'
import { formatDate, formatNumber, formatRupiah, today } from '../lib/format'
import type { Paginated, Sale } from '../types'
import { useAuth } from '../store/auth'

export default function SalesPage() {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [date, setDate] = useState(today())
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Sale | null>(null)
  const [voidReason, setVoidReason] = useState('')
  const [error, setError] = useState('')

  const salesQuery = useQuery({
    queryKey: ['sales', date, page],
    queryFn: () =>
      apiRequest<Paginated<Sale>>(
        `/sales?from=${date}T00:00:00&to=${date}T23:59:59&page=${page}&page_size=20`,
      ),
  })

  const pageSize = salesQuery.data?.page_size ?? 20
  const totalCount = salesQuery.data?.total ?? 0
  const lastPage = Math.max(Math.ceil(totalCount / pageSize), 1)

  const voidMutation = useMutation({
    mutationFn: (saleId: string) =>
      apiRequest(`/sales/${saleId}/void`, { method: 'POST', body: { reason: voidReason } }),
    onSuccess: () => {
      setSelected(null)
      setVoidReason('')
      setError('')
      void queryClient.invalidateQueries({ queryKey: ['sales'] })
    },
    onError: (err) => setError(err instanceof RequestError ? err.message : 'Gagal void.'),
  })

  return (
    <div className="space-y-4 p-6">
      <Card className="overflow-hidden">
        <CardHeader
          title="Daftar Penjualan"
          actions={
            <div className="flex items-center gap-2">
              <Label>Tanggal</Label>
              <Input
                type="date"
                value={date}
                onChange={(e) => {
                  setDate(e.target.value)
                  setPage(1)
                }}
                className="w-40"
              />
            </div>
          }
        />
        {salesQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Nomor</th>
                <th className="px-4 py-2">Waktu</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Total</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {salesQuery.data?.data.map((sale) => (
                <tr key={sale.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{sale.number}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">{formatDate(sale.sold_at)}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        sale.status === 'completed'
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-red-50 text-red-600'
                      }`}
                    >
                      {sale.status}
                    </span>
                  </td>
                  <td className="num px-4 py-2 text-right font-medium">{formatRupiah(sale.total)}</td>
                  <td className="px-4 py-2 text-right">
                    <Button variant="ghost" onClick={() => setSelected(sale)}>
                      Detail
                    </Button>
                  </td>
                </tr>
              ))}
              {salesQuery.data?.data.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <EmptyState message="Tidak ada transaksi." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-sm">
          <span className="text-slate-400">Total {totalCount} transaksi</span>
          <div className="flex items-center gap-2">
            <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Sebelumnya
            </Button>
            <span className="text-slate-500">
              {page} / {lastPage}
            </span>
            <Button
              variant="secondary"
              disabled={page >= lastPage}
              onClick={() => setPage((p) => p + 1)}
            >
              Berikutnya
            </Button>
          </div>
        </div>
      </Card>

      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="max-h-[90vh] w-full max-w-md overflow-y-auto">
            <CardHeader
              title={`Struk ${selected.number}`}
              actions={
                <button className="text-sm text-slate-400" onClick={() => setSelected(null)}>
                  Tutup
                </button>
              }
            />
            <div className="space-y-3 p-4 text-sm">
              <div className="text-xs text-slate-500">{formatDate(selected.sold_at)}</div>
              <ul className="divide-y divide-dashed divide-slate-200">
                {selected.items.map((item, index) => (
                  <li key={index} className="flex justify-between py-1.5">
                    <span>
                      {item.name_snapshot}
                      <span className="text-slate-400">
                        {' '}
                        {formatNumber(item.quantity)} {item.unit_name_snapshot}
                      </span>
                    </span>
                    <span className="num">{formatRupiah(item.line_total)}</span>
                  </li>
                ))}
              </ul>
              <div className="space-y-1">
                <Row label="Subtotal" value={formatRupiah(selected.subtotal)} />
                <Row label="Diskon" value={formatRupiah(selected.discount_total)} />
                <Row label="Total" value={formatRupiah(selected.total)} bold />
                {selected.payments.map((payment, index) => (
                  <Row
                    key={index}
                    label={`Bayar (${payment.method})`}
                    value={formatRupiah(payment.amount)}
                  />
                ))}
                <Row label="Kembalian" value={formatRupiah(selected.change_total)} />
              </div>

              {selected.status === 'voided' && (
                <div className="rounded-lg bg-red-50 px-3 py-2 text-red-700">
                  Dibatalkan: {selected.void_reason}
                </div>
              )}

              {selected.status === 'completed' && hasPermission('sale.void') && (
                <div className="space-y-2 border-t border-slate-100 pt-3">
                  <Label>Alasan void</Label>
                  <Input
                    value={voidReason}
                    onChange={(e) => setVoidReason(e.target.value)}
                    placeholder="Salah input, pembatalan…"
                  />
                  <ErrorText>{error}</ErrorText>
                  <Button
                    variant="danger"
                    className="w-full"
                    disabled={!voidReason.trim() || voidMutation.isPending}
                    onClick={() => voidMutation.mutate(selected.id)}
                  >
                    Void Transaksi
                  </Button>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

function Row({ label, value, bold = false }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between ${bold ? 'font-bold' : ''}`}>
      <span className={bold ? '' : 'text-slate-500'}>{label}</span>
      <span className="num">{value}</span>
    </div>
  )
}
