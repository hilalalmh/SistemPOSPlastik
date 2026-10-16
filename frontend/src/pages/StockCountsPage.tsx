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
import { formatDate, formatNumber } from '../lib/format'
import type { Paginated, StockCount, StockCountListItem } from '../types'
import { useAuth } from '../store/auth'

const STATUS_LABELS: Record<string, string> = {
  counting: 'Berhitung',
  confirmed: 'Selesai',
  cancelled: 'Dibatalkan',
}

const STATUS_STYLES: Record<string, string> = {
  counting: 'bg-amber-50 text-amber-700',
  confirmed: 'bg-emerald-50 text-emerald-700',
  cancelled: 'bg-red-50 text-red-600',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[status] ?? 'bg-slate-100'}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

export default function StockCountsPage() {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const listQuery = useQuery({
    queryKey: ['stock-counts', page],
    queryFn: () =>
      apiRequest<Paginated<StockCountListItem>>(`/stock-counts?page=${page}&page_size=20`),
  })

  const pageSize = listQuery.data?.page_size ?? 20
  const totalCount = listQuery.data?.total ?? 0
  const lastPage = Math.max(Math.ceil(totalCount / pageSize), 1)

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['stock-counts'] })
  }

  return (
    <div className="space-y-4 p-6">
      <Card className="overflow-hidden">
        <CardHeader
          title="Stok Opname"
          actions={
            hasPermission('stockcount.create') && (
              <Button onClick={() => setCreateOpen(true)}>Buat Opname</Button>
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
                <th className="px-4 py-2">Dibuat</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">Selesai</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {listQuery.data?.data.map((count) => (
                <tr key={count.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{count.number}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {formatDate(count.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={count.status} />
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {count.confirmed_at ? formatDate(count.confirmed_at) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Button variant="ghost" onClick={() => setSelectedId(count.id)}>
                      Detail
                    </Button>
                  </td>
                </tr>
              ))}
              {listQuery.data?.data.length === 0 && (
                <tr>
                  <td colSpan={5}>
                    <EmptyState message="Belum ada stok opname." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-sm">
          <span className="text-slate-400">Total {totalCount} opname</span>
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
        <CreateStockCountModal
          onClose={() => setCreateOpen(false)}
          onCreated={(id) => {
            setCreateOpen(false)
            refresh()
            setSelectedId(id)
          }}
        />
      )}

      {selectedId && (
        <StockCountDetailModal
          countId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
        />
      )}
    </div>
  )
}

function CreateStockCountModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<{ id: string; number: string; status: string }>('/stock-counts', {
        method: 'POST',
        body: { notes: notes.trim() || null },
      }),
    onSuccess: (data) => onCreated(data.id),
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal membuat opname.'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader
          title="Buat Stok Opname"
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        <div className="space-y-4 p-4">
          <p className="text-sm text-slate-500">
            Semua varian aktif akan dimasukkan ke daftar hitung dengan stok sistem saat ini.
          </p>
          <div>
            <Label>Catatan (opsional)</Label>
            <Input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Opname akhir bulan…"
            />
          </div>
          <ErrorText>{error}</ErrorText>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={onClose}>
              Batal
            </Button>
            <Button disabled={createMutation.isPending} onClick={() => createMutation.mutate()}>
              {createMutation.isPending && <Spinner className="border-white/40 border-t-white" />}
              Mulai Opname
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

function StockCountDetailModal({
  countId,
  onClose,
  onChanged,
}: {
  countId: string
  onClose: () => void
  onChanged: () => void
}) {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [counts, setCounts] = useState<Record<string, string>>({})
  const [error, setError] = useState('')

  const detailQuery = useQuery({
    queryKey: ['stock-count', countId],
    queryFn: () => apiRequest<StockCount>(`/stock-counts/${countId}`),
  })
  const count = detailQuery.data

  function handleSuccess() {
    void queryClient.invalidateQueries({ queryKey: ['stock-counts'] })
    void queryClient.invalidateQueries({ queryKey: ['stock-count', countId] })
    void queryClient.invalidateQueries({ queryKey: ['stock'] })
    void queryClient.invalidateQueries({ queryKey: ['movements'] })
    onChanged()
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/stock-counts/${countId}/items`, {
        method: 'PATCH',
        body: {
          items: (count?.items ?? [])
            .filter((item) => {
              const value = counts[item.variant_id]
              return value !== undefined && value !== ''
            })
            .map((item) => ({
              variant_id: item.variant_id,
              counted_quantity: Number(counts[item.variant_id]),
            })),
        },
      }),
    onSuccess: () => {
      setError('')
      setCounts({})
      handleSuccess()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menyimpan hitungan.'),
  })

  const confirmMutation = useMutation({
    mutationFn: () => apiRequest(`/stock-counts/${countId}/confirm`, { method: 'POST' }),
    onSuccess: () => {
      setError('')
      handleSuccess()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal konfirmasi opname.'),
  })

  const cancelMutation = useMutation({
    mutationFn: () => apiRequest(`/stock-counts/${countId}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      setError('')
      handleSuccess()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal membatalkan opname.'),
  })

  const editable = count?.status === 'counting' && hasPermission('stockcount.count')
  const canConfirm = count?.status === 'counting' && hasPermission('stockcount.confirm')
  const hasInput = Object.values(counts).some((v) => v !== '')

  function valueFor(variantId: string, counted?: string | null) {
    return counts[variantId] ?? counted ?? ''
  }

  function fillWithSystem() {
    if (!count) return
    const next: Record<string, string> = {}
    for (const item of count.items) {
      next[item.variant_id] = item.system_quantity
    }
    setCounts(next)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-6">
      <Card className="w-full max-w-3xl">
        <CardHeader
          title={count ? `Opname ${count.number}` : 'Detail Opname'}
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        {!count ? (
          <EmptyState message="Memuat…" />
        ) : (
          <div className="space-y-4 p-4">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <div className="text-xs text-slate-400">Status</div>
                <StatusBadge status={count.status} />
              </div>
              <div>
                <div className="text-xs text-slate-400">Dibuat</div>
                <div className="font-medium">{formatDate(count.created_at)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Catatan</div>
                <div className="font-medium">{count.notes ?? '-'}</div>
              </div>
            </div>

            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-2">Produk</th>
                  <th className="px-3 py-2 text-right">Stok Sistem</th>
                  <th className="px-3 py-2 text-right">Hasil Hitung</th>
                  <th className="px-3 py-2 text-right">Selisih</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {count.items.map((item) => {
                  const value = valueFor(item.variant_id, item.counted_quantity)
                  const diff =
                    value === '' ? null : Number(value) - Number(item.system_quantity)
                  return (
                    <tr key={item.id}>
                      <td className="px-3 py-2">
                        <div className="font-medium">{item.product_name}</div>
                        <div className="text-xs text-slate-400">
                          {item.sku}
                          {item.unit_name ? ` · ${item.unit_name}` : ''}
                        </div>
                      </td>
                      <td className="num px-3 py-2 text-right">
                        {formatNumber(item.system_quantity)}
                      </td>
                      <td className="px-3 py-2 text-right">
                        {editable ? (
                          <Input
                            type="number"
                            step="any"
                            value={value}
                            onChange={(e) =>
                              setCounts((prev) => ({
                                ...prev,
                                [item.variant_id]: e.target.value,
                              }))
                            }
                            className="w-24 text-right"
                          />
                        ) : (
                          <span className="num">
                            {item.counted_quantity != null
                              ? formatNumber(item.counted_quantity)
                              : '-'}
                          </span>
                        )}
                      </td>
                      <td
                        className={`num px-3 py-2 text-right ${
                          diff == null
                            ? 'text-slate-400'
                            : diff === 0
                              ? 'text-slate-500'
                              : diff > 0
                                ? 'text-emerald-700'
                                : 'text-red-600'
                        }`}
                      >
                        {diff == null ? '-' : `${diff > 0 ? '+' : ''}${formatNumber(diff)}`}
                      </td>
                    </tr>
                  )
                })}
                {count.items.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState message="Tidak ada item untuk dihitung." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            <ErrorText>{error}</ErrorText>

            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-3">
              {editable && (
                <>
                  <Button variant="ghost" onClick={fillWithSystem}>
                    Samakan dengan sistem
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={!hasInput || saveMutation.isPending}
                    onClick={() => saveMutation.mutate()}
                  >
                    {saveMutation.isPending && <Spinner />}
                    Simpan Hitungan
                  </Button>
                </>
              )}
              {canConfirm && (
                <>
                  <Button
                    variant="danger"
                    disabled={cancelMutation.isPending}
                    onClick={() => cancelMutation.mutate()}
                  >
                    Batalkan
                  </Button>
                  <Button
                    disabled={confirmMutation.isPending}
                    onClick={() => confirmMutation.mutate()}
                  >
                    {confirmMutation.isPending && <Spinner className="border-white/40 border-t-white" />}
                    Konfirmasi & Sesuaikan Stok
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
