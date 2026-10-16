import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorText,
  Input,
  Label,
  Spinner,
} from '../components/ui'
import { apiRequest, RequestError } from '../lib/api'
import { formatDate, formatNumber, formatRupiah } from '../lib/format'
import type { Movement, Paginated } from '../types'

interface StockBalanceRow {
  variant_id: string
  product_name?: string | null
  sku?: string | null
  unit_name?: string | null
  quantity: string
  avg_cost: string
  min_stock?: string | null
  low_stock: boolean
}

export default function InventoryPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    variant_id: '',
    adjustment_type: 'increase',
    quantity: '',
    reason: '',
  })

  const stockQuery = useQuery({
    queryKey: ['stock', search, lowOnly],
    queryFn: () =>
      apiRequest<Paginated<StockBalanceRow>>(
        `/inventory/stock?q=${encodeURIComponent(search)}&low_stock=${lowOnly}&page_size=100`,
      ),
  })

  const movementsQuery = useQuery({
    queryKey: ['movements'],
    queryFn: () => apiRequest<Paginated<Movement>>('/inventory/movements?page_size=15'),
  })

  const adjustment = useMutation({
    mutationFn: (body: unknown) =>
      apiRequest('/inventory/adjustments', { method: 'POST', body }),
    onSuccess: () => {
      setForm({ variant_id: '', adjustment_type: 'increase', quantity: '', reason: '' })
      setError('')
      void queryClient.invalidateQueries({ queryKey: ['stock'] })
      void queryClient.invalidateQueries({ queryKey: ['movements'] })
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menyimpan penyesuaian.'),
  })

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!form.variant_id || !form.quantity || !form.reason.trim()) return
    adjustment.mutate({
      variant_id: form.variant_id,
      adjustment_type: form.adjustment_type,
      quantity: Number(form.quantity),
      reason: form.reason.trim(),
    })
  }

  const rows = stockQuery.data?.data ?? []
  const variantOptions = Array.from(
    new Map(rows.map((row) => [row.variant_id, `${row.product_name} (${row.sku})`])).entries(),
  )

  return (
    <div className="grid grid-cols-1 gap-4 p-6 xl:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        <Card className="overflow-hidden">
          <CardHeader
            title="Stok Barang"
            actions={
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1 text-xs text-slate-500">
                  <input
                    type="checkbox"
                    checked={lowOnly}
                    onChange={(e) => setLowOnly(e.target.checked)}
                  />
                  Hanya menipis
                </label>
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Cari SKU/produk…"
                  className="w-48"
                />
              </div>
            }
          />
          {stockQuery.isLoading ? (
            <EmptyState message="Memuat…" />
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-4 py-2">Produk</th>
                  <th className="px-4 py-2 text-right">Stok</th>
                  <th className="px-4 py-2 text-right">HPP rata-rata</th>
                  <th className="px-4 py-2 text-right">Nilai</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((row) => (
                  <tr key={row.variant_id} className="hover:bg-slate-50">
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{row.product_name}</span>
                        {row.low_stock && (
                          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                            Menipis
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400">{row.sku}</div>
                    </td>
                    <td className="num px-4 py-2 text-right">
                      {formatNumber(row.quantity)} {row.unit_name}
                    </td>
                    <td className="num px-4 py-2 text-right">{formatRupiah(row.avg_cost)}</td>
                    <td className="num px-4 py-2 text-right">
                      {formatRupiah(Number(row.quantity) * Number(row.avg_cost))}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState message="Tidak ada data stok." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </Card>

        <Card className="overflow-hidden">
          <CardHeader title="Pergerakan Stok Terbaru" />
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Waktu</th>
                <th className="px-4 py-2">Produk</th>
                <th className="px-4 py-2">Jenis</th>
                <th className="px-4 py-2 text-right">Jumlah</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {movementsQuery.data?.data.map((movement) => (
                <tr key={movement.id}>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {formatDate(movement.created_at)}
                  </td>
                  <td className="px-4 py-2">{movement.product_name}</td>
                  <td className="px-4 py-2 capitalize text-slate-500">
                    {(movement.type ?? '').replace(/_/g, ' ')}
                  </td>
                  <td
                    className={`num px-4 py-2 text-right ${
                      Number(movement.quantity) < 0 ? 'text-red-600' : 'text-emerald-700'
                    }`}
                  >
                    {formatNumber(movement.quantity)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card className="h-fit">
        <CardHeader title="Penyesuaian Stok" />
        <form onSubmit={submit} className="space-y-3 p-4">
          <div>
            <Label>Varian</Label>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={form.variant_id}
              onChange={(e) => setForm({ ...form, variant_id: e.target.value })}
              required
            >
              <option value="">Pilih varian…</option>
              {variantOptions.map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label>Jenis</Label>
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={form.adjustment_type}
              onChange={(e) => setForm({ ...form, adjustment_type: e.target.value })}
            >
              <option value="increase">Tambah (+)</option>
              <option value="decrease">Kurangi (-)</option>
            </select>
          </div>
          <div>
            <Label>Jumlah (satuan dasar)</Label>
            <Input
              type="number"
              min={0}
              step="any"
              value={form.quantity}
              onChange={(e) => setForm({ ...form, quantity: e.target.value })}
              required
            />
          </div>
          <div>
            <Label>Alasan</Label>
            <Input
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              placeholder="Rusak, hilang, koreksi…"
              required
            />
          </div>
          <ErrorText>{error}</ErrorText>
          <Button type="submit" className="w-full" disabled={adjustment.isPending}>
            {adjustment.isPending && <Spinner className="border-white/40 border-t-white" />}
            Simpan Penyesuaian
          </Button>
        </form>
      </Card>
    </div>
  )
}
