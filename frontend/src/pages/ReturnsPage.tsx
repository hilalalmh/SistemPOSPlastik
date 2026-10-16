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
import type { Paginated, ReturnableSale, Sale, SaleReturn } from '../types'
import { useAuth } from '../store/auth'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  confirmed: 'Selesai',
  cancelled: 'Dibatalkan',
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-amber-50 text-amber-700',
  confirmed: 'bg-emerald-50 text-emerald-700',
  cancelled: 'bg-red-50 text-red-600',
}

const CONDITION_LABELS: Record<string, string> = {
  resellable: 'Layak jual',
  damaged: 'Rusak',
  writeoff: 'Tidak masuk stok',
}

const REFUND_LABELS: Record<string, string> = {
  cash: 'Tunai',
  transfer: 'Transfer',
  none: 'Tanpa pengembalian',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-600'}`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

export default function ReturnsPage() {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const listQuery = useQuery({
    queryKey: ['returns', page],
    queryFn: () => apiRequest<Paginated<SaleReturn>>(`/returns?page=${page}&page_size=25`),
  })

  const pageSize = listQuery.data?.page_size ?? 25
  const totalCount = listQuery.data?.total ?? 0
  const lastPage = Math.max(Math.ceil(totalCount / pageSize), 1)

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['returns'] })
  }

  return (
    <div className="space-y-4 p-6">
      <Card className="overflow-hidden">
        <CardHeader
          title="Retur Penjualan"
          actions={
            hasPermission('return.create') && (
              <Button onClick={() => setCreateOpen(true)}>Buat Retur</Button>
            )
          }
        />
        {listQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Nomor</th>
                <th className="px-4 py-2">Tanggal</th>
                <th className="px-4 py-2">Nilai Retur</th>
                <th className="px-4 py-2">Alasan</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {listQuery.data?.data.map((ret) => (
                <tr key={ret.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{ret.number}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {formatDate(ret.created_at)}
                  </td>
                  <td className="num px-4 py-2">{formatRupiah(ret.refund_amount)}</td>
                  <td className="max-w-[16rem] truncate px-4 py-2 text-slate-500">{ret.reason}</td>
                  <td className="px-4 py-2">
                    <StatusBadge status={ret.status} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Button variant="ghost" onClick={() => setSelectedId(ret.id)}>
                      Detail
                    </Button>
                  </td>
                </tr>
              ))}
              {listQuery.data?.data.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState message="Belum ada retur penjualan." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-sm">
          <span className="text-slate-400">Total {totalCount} retur</span>
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

      {createOpen && (
        <CreateReturnModal
          onClose={() => setCreateOpen(false)}
          onCreated={(id) => {
            setCreateOpen(false)
            refresh()
            setSelectedId(id)
          }}
        />
      )}

      {selectedId && (
        <ReturnDetailModal
          returnId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
        />
      )}
    </div>
  )
}

function CreateReturnModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const [searchText, setSearchText] = useState('')
  const [query, setQuery] = useState('')
  const [selectedSaleId, setSelectedSaleId] = useState<string | null>(null)
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  const [conditions, setConditions] = useState<Record<string, string>>({})
  const [reason, setReason] = useState('')
  const [refundMethod, setRefundMethod] = useState('cash')
  const [error, setError] = useState('')

  const searchQuery = useQuery({
    queryKey: ['sale-search', query],
    queryFn: () => apiRequest<Paginated<Sale>>(`/sales?q=${encodeURIComponent(query)}&page_size=8`),
    enabled: query.length >= 3,
  })

  const itemsQuery = useQuery({
    queryKey: ['returnable-items', selectedSaleId],
    queryFn: () => apiRequest<ReturnableSale>(`/sales/${selectedSaleId}/returnable-items`),
    enabled: !!selectedSaleId,
  })

  const createMutation = useMutation({
    mutationFn: () => {
      const items = (itemsQuery.data?.items ?? [])
        .filter((item) => {
          const value = quantities[item.id]
          return value !== undefined && value !== '' && Number(value) > 0
        })
        .map((item) => ({
          sale_item_id: item.sale_item_id,
          quantity: Number(quantities[item.id]),
          condition: conditions[item.id] ?? 'resellable',
        }))
      return apiRequest<SaleReturn>('/returns', {
        method: 'POST',
        body: {
          sale_id: selectedSaleId,
          reason: reason.trim(),
          refund_method: refundMethod === 'none' ? null : refundMethod,
          items,
        },
      })
    },
    onSuccess: (data) => onCreated(data.id),
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal membuat retur.'),
  })

  const selectedSale = searchQuery.data?.data.find((s) => s.id === selectedSaleId)
  const hasItems = Object.values(quantities).some((v) => v !== '' && Number(v) > 0)

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4">
      <Card className="my-6 w-full max-w-2xl">
        <CardHeader
          title="Buat Retur Penjualan"
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        <div className="space-y-4 p-4">
          <div>
            <Label>Cari nomor transaksi</Label>
            <div className="flex gap-2">
              <Input
                value={searchText}
                placeholder="SLS-202601-000001"
                onChange={(e) => setSearchText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') setQuery(searchText.trim())
                }}
              />
              <Button variant="secondary" onClick={() => setQuery(searchText.trim())}>
                Cari
              </Button>
            </div>
          </div>

          {query.length >= 3 && (
            <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-200">
              {searchQuery.isLoading ? (
                <EmptyState message="Mencari…" />
              ) : searchQuery.data && searchQuery.data.data.length > 0 ? (
                searchQuery.data.data.map((sale) => (
                  <button
                    key={sale.id}
                    type="button"
                    onClick={() => {
                      setSelectedSaleId(sale.id)
                      setQuantities({})
                      setConditions({})
                    }}
                    className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50 ${
                      selectedSaleId === sale.id ? 'bg-emerald-50' : ''
                    }`}
                  >
                    <span className="font-medium">{sale.number}</span>
                    <span className="text-xs text-slate-500">
                      {formatDate(sale.sold_at)} · {formatRupiah(sale.total)}
                    </span>
                  </button>
                ))
              ) : (
                <EmptyState message="Transaksi tidak ditemukan." />
              )}
            </div>
          )}

          {selectedSale && (
            <div className="space-y-2">
              <div className="text-sm text-slate-500">
                Retur untuk transaksi <span className="font-medium">{selectedSale.number}</span>
              </div>
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
                  <tr>
                    <th className="px-3 py-2">Produk</th>
                    <th className="px-3 py-2 text-right">Dapat Diretur</th>
                    <th className="px-3 py-2">Jumlah</th>
                    <th className="px-3 py-2">Kondisi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {itemsQuery.data?.items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-3 py-2">
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-slate-400">{item.sku}</div>
                      </td>
                      <td className="num px-3 py-2 text-right">
                        {formatNumber(item.remaining_quantity)}
                      </td>
                      <td className="px-3 py-2">
                        <Input
                          type="number"
                          step="any"
                          min="0"
                          max={item.remaining_quantity}
                          value={quantities[item.id] ?? ''}
                          onChange={(e) =>
                            setQuantities((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          className="w-24 text-right"
                          disabled={Number(item.remaining_quantity) <= 0}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <select
                          value={conditions[item.id] ?? 'resellable'}
                          onChange={(e) =>
                            setConditions((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                        >
                          <option value="resellable">Layak jual</option>
                          <option value="damaged">Rusak</option>
                          <option value="writeoff">Tidak masuk stok</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                  {itemsQuery.data?.items.length === 0 && (
                    <tr>
                      <td colSpan={4}>
                        <EmptyState message="Tidak ada item yang dapat diretur." />
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Alasan retur</Label>
              <Input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Barang rusak / salah beli…"
              />
            </div>
            <div>
              <Label>Pengembalian dana</Label>
              <select
                value={refundMethod}
                onChange={(e) => setRefundMethod(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              >
                <option value="cash">Tunai</option>
                <option value="transfer">Transfer</option>
                <option value="none">Tanpa pengembalian</option>
              </select>
            </div>
          </div>

          <ErrorText>{error}</ErrorText>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <Button variant="secondary" onClick={onClose}>
              Batal
            </Button>
            <Button
              disabled={!selectedSaleId || !hasItems || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending && <Spinner className="border-white/40 border-t-white" />}
              Simpan Retur
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

function ReturnDetailModal({
  returnId,
  onClose,
  onChanged,
}: {
  returnId: string
  onClose: () => void
  onChanged: () => void
}) {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [error, setError] = useState('')

  const detailQuery = useQuery({
    queryKey: ['return', returnId],
    queryFn: () => apiRequest<SaleReturn>(`/returns/${returnId}`),
  })
  const ret = detailQuery.data

  const canAct = hasPermission('return.create') || hasPermission('return.confirm')

  function handleSuccess() {
    void queryClient.invalidateQueries({ queryKey: ['returns'] })
    void queryClient.invalidateQueries({ queryKey: ['return', returnId] })
    void queryClient.invalidateQueries({ queryKey: ['stock'] })
    void queryClient.invalidateQueries({ queryKey: ['movements'] })
    onChanged()
  }

  const confirmMutation = useMutation({
    mutationFn: () => apiRequest(`/returns/${returnId}/confirm`, { method: 'POST' }),
    onSuccess: () => {
      setError('')
      handleSuccess()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal konfirmasi retur.'),
  })

  const cancelMutation = useMutation({
    mutationFn: () => apiRequest(`/returns/${returnId}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      setError('')
      handleSuccess()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal membatalkan retur.'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader
          title={ret ? `Retur ${ret.number}` : 'Detail Retur'}
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        {!ret ? (
          <EmptyState message="Memuat…" />
        ) : (
          <div className="space-y-4 p-4">
            <div className="grid grid-cols-4 gap-3 text-sm">
              <div>
                <div className="text-xs text-slate-400">Status</div>
                <StatusBadge status={ret.status} />
              </div>
              <div>
                <div className="text-xs text-slate-400">Tanggal</div>
                <div className="font-medium">{formatDate(ret.created_at)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Pengembalian</div>
                <div className="font-medium">
                  {ret.refund_method ? (REFUND_LABELS[ret.refund_method] ?? ret.refund_method) : '-'}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Nilai Retur</div>
                <div className="font-medium">{formatRupiah(ret.refund_amount)}</div>
              </div>
            </div>

            <div>
              <div className="text-xs text-slate-400">Alasan</div>
              <div className="text-sm">{ret.reason}</div>
            </div>

            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-2">Produk</th>
                  <th className="px-3 py-2">Kondisi</th>
                  <th className="px-3 py-2 text-right">Jumlah</th>
                  <th className="px-3 py-2 text-right">Nilai</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ret.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3 py-2">
                      <div className="font-medium">{item.product_name}</div>
                      <div className="text-xs text-slate-400">{item.sku}</div>
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {CONDITION_LABELS[item.condition] ?? item.condition}
                    </td>
                    <td className="num px-3 py-2 text-right">{formatNumber(item.quantity)}</td>
                    <td className="num px-3 py-2 text-right">
                      {formatRupiah(item.refund_amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <ErrorText>{error}</ErrorText>

            <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
              <Button variant="secondary" onClick={onClose}>
                Tutup
              </Button>
              {ret.status === 'draft' && canAct && (
                <Button
                  variant="danger"
                  disabled={cancelMutation.isPending}
                  onClick={() => cancelMutation.mutate()}
                >
                  Batalkan
                </Button>
              )}
              {ret.status === 'draft' && hasPermission('return.confirm') && (
                <Button
                  disabled={confirmMutation.isPending}
                  onClick={() => confirmMutation.mutate()}
                >
                  {confirmMutation.isPending && (
                    <Spinner className="border-white/40 border-t-white" />
                  )}
                  Konfirmasi Retur
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
