import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { Button, Card, CardHeader, EmptyState, ErrorText, Input, Label } from '../components/ui'
import { apiRequest, RequestError } from '../lib/api'
import { formatDate, formatNumber, formatRupiah } from '../lib/format'
import type { CatalogItem, CatalogUnit, Paginated, Purchase, Supplier } from '../types'
import { useAuth } from '../store/auth'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Draft',
  ordered: 'Dipesan',
  partially_received: 'Diterima Sebagian',
  received: 'Diterima',
  cancelled: 'Dibatalkan',
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-slate-100 text-slate-600',
  ordered: 'bg-amber-50 text-amber-700',
  partially_received: 'bg-blue-50 text-blue-700',
  received: 'bg-emerald-50 text-emerald-700',
  cancelled: 'bg-red-50 text-red-600',
}

interface DraftLine {
  key: string
  variantId: string
  productName: string
  sku: string
  units: CatalogUnit[]
  unitId: string
  quantity: number
  unitCost: number
  discount: number
}

function newKey() {
  return crypto.randomUUID()
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[status] ?? 'bg-slate-100'}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

export default function PurchasesPage() {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const listQuery = useQuery({
    queryKey: ['purchases', status, page],
    queryFn: () =>
      apiRequest<Paginated<Purchase>>(
        `/purchases?page=${page}&page_size=20${status ? `&status=${status}` : ''}`,
      ),
  })

  const pageSize = listQuery.data?.page_size ?? 20
  const totalCount = listQuery.data?.total ?? 0
  const lastPage = Math.max(Math.ceil(totalCount / pageSize), 1)

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['purchases'] })
  }

  return (
    <div className="space-y-4 p-6">
      <Card className="overflow-hidden">
        <CardHeader
          title="Pembelian & Penerimaan"
          actions={
            <div className="flex items-center gap-2">
              <select
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value)
                  setPage(1)
                }}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
              >
                <option value="">Semua status</option>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              {hasPermission('purchase.update') && (
                <Button onClick={() => setCreateOpen(true)}>Buat Pembelian</Button>
              )}
            </div>
          }
        />
        {listQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Nomor</th>
                <th className="px-4 py-2">Supplier</th>
                <th className="px-4 py-2">Tanggal</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-right">Total</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {listQuery.data?.data.map((purchase) => (
                <tr key={purchase.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{purchase.number}</td>
                  <td className="px-4 py-2">{purchase.supplier_name ?? '-'}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {formatDate(purchase.created_at)}
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={purchase.status} />
                  </td>
                  <td className="num px-4 py-2 text-right font-medium">
                    {formatRupiah(purchase.total)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Button variant="ghost" onClick={() => setSelectedId(purchase.id)}>
                      Detail
                    </Button>
                  </td>
                </tr>
              ))}
              {listQuery.data?.data.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState message="Belum ada pembelian." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-sm">
          <span className="text-slate-400">Total {totalCount} pembelian</span>
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
        <CreatePurchaseModal
          onClose={() => setCreateOpen(false)}
          onSaved={() => {
            setCreateOpen(false)
            refresh()
          }}
        />
      )}

      {selectedId && (
        <PurchaseDetailModal
          purchaseId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
        />
      )}
    </div>
  )
}

function CreatePurchaseModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const queryClient = useQueryClient()
  const [supplierId, setSupplierId] = useState('')
  const [invoiceNo, setInvoiceNo] = useState('')
  const [notes, setNotes] = useState('')
  const [additionalCost, setAdditionalCost] = useState('0')
  const [headerDiscount, setHeaderDiscount] = useState('0')
  const [lines, setLines] = useState<DraftLine[]>([])
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [newSupplier, setNewSupplier] = useState('')
  const [showSupplierInput, setShowSupplierInput] = useState(false)

  const suppliersQuery = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => apiRequest<Paginated<Supplier>>('/suppliers?page_size=100'),
  })

  const catalogQuery = useQuery({
    queryKey: ['catalog', 'purchase', search],
    queryFn: () =>
      apiRequest<{ data: CatalogItem[] }>(`/catalog/search?q=${encodeURIComponent(search)}&limit=12`),
    enabled: search.trim().length > 0,
  })

  const supplierMutation = useMutation({
    mutationFn: () =>
      apiRequest<Supplier>('/suppliers', { method: 'POST', body: { name: newSupplier.trim() } }),
    onSuccess: (supplier) => {
      setSupplierId(supplier.id)
      setNewSupplier('')
      setShowSupplierInput(false)
      void queryClient.invalidateQueries({ queryKey: ['suppliers'] })
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menambah supplier.'),
  })

  const createMutation = useMutation({
    mutationFn: (order: boolean) =>
      apiRequest<Purchase>('/purchases', {
        method: 'POST',
        body: {
          supplier_id: supplierId,
          invoice_no: invoiceNo || null,
          notes: notes || null,
          additional_cost: Number(additionalCost) || 0,
          discount_amount: Number(headerDiscount) || 0,
          order,
          items: lines.map((line) => ({
            variant_id: line.variantId,
            unit_id: line.unitId,
            quantity: line.quantity,
            unit_cost: line.unitCost,
            discount_amount: line.discount,
          })),
        },
      }),
    onSuccess: onSaved,
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menyimpan pembelian.'),
  })

  const subtotal = lines.reduce((sum, l) => sum + l.quantity * l.unitCost, 0)
  const itemDiscount = lines.reduce((sum, l) => sum + l.discount, 0)
  const grandTotal =
    subtotal - itemDiscount - (Number(headerDiscount) || 0) + (Number(additionalCost) || 0)

  function addLine(item: CatalogItem) {
    setError('')
    setSearch('')
    setLines((prev) => {
      if (prev.some((l) => l.variantId === item.variant_id)) return prev
      return [
        ...prev,
        {
          key: newKey(),
          variantId: item.variant_id,
          productName: item.product_name,
          sku: item.sku,
          units: item.units,
          unitId: item.base_unit_id,
          quantity: 1,
          unitCost: 0,
          discount: 0,
        },
      ]
    })
  }

  function updateLine(key: string, patch: Partial<DraftLine>) {
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)))
  }

  const canSubmit = supplierId !== '' && lines.length > 0

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-6">
      <Card className="w-full max-w-3xl">
        <CardHeader
          title="Buat Pembelian"
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        <div className="space-y-4 p-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Supplier</Label>
              <div className="flex gap-2">
                <select
                  value={supplierId}
                  onChange={(e) => setSupplierId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
                >
                  <option value="">Pilih supplier…</option>
                  {suppliersQuery.data?.data.map((supplier) => (
                    <option key={supplier.id} value={supplier.id}>
                      {supplier.name}
                    </option>
                  ))}
                </select>
                <Button variant="secondary" onClick={() => setShowSupplierInput((v) => !v)}>
                  + Baru
                </Button>
              </div>
              {showSupplierInput && (
                <div className="mt-2 flex gap-2">
                  <Input
                    value={newSupplier}
                    onChange={(e) => setNewSupplier(e.target.value)}
                    placeholder="Nama supplier baru"
                  />
                  <Button
                    disabled={!newSupplier.trim() || supplierMutation.isPending}
                    onClick={() => supplierMutation.mutate()}
                  >
                    Simpan
                  </Button>
                </div>
              )}
            </div>
            <div>
              <Label>No. Invoice / Nota</Label>
              <Input value={invoiceNo} onChange={(e) => setInvoiceNo(e.target.value)} />
            </div>
          </div>

          <div>
            <Label>Cari produk untuk ditambahkan</Label>
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Nama atau SKU…"
            />
            {search.trim().length > 0 && (
              <div className="mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-200">
                {catalogQuery.data?.data.length ? (
                  catalogQuery.data.data.map((item) => (
                    <button
                      key={item.variant_id}
                      type="button"
                      className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                      onClick={() => addLine(item)}
                    >
                      <span className="font-medium">{item.product_name}</span>
                      <span className="ml-2 text-xs text-slate-400">{item.sku}</span>
                    </button>
                  ))
                ) : (
                  <div className="px-3 py-2 text-sm text-slate-400">Tidak ada hasil.</div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-2">Produk</th>
                  <th className="px-3 py-2">Satuan</th>
                  <th className="px-3 py-2 text-right">Qty</th>
                  <th className="px-3 py-2 text-right">Harga/unit</th>
                  <th className="px-3 py-2 text-right">Diskon</th>
                  <th className="px-3 py-2 text-right">Subtotal</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {lines.map((line) => (
                  <tr key={line.key}>
                    <td className="px-3 py-2">
                      <div className="font-medium">{line.productName}</div>
                      <div className="text-xs text-slate-400">{line.sku}</div>
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={line.unitId}
                        onChange={(e) => updateLine(line.key, { unitId: e.target.value })}
                        className="rounded-lg border border-slate-300 px-1.5 py-1 text-xs"
                      >
                        {line.units.map((unit) => (
                          <option key={unit.unit_id} value={unit.unit_id}>
                            {unit.unit_name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        value={line.quantity}
                        onChange={(e) =>
                          updateLine(line.key, { quantity: Number(e.target.value) || 0 })
                        }
                        className="w-20 text-right"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        value={line.unitCost}
                        onChange={(e) =>
                          updateLine(line.key, { unitCost: Number(e.target.value) || 0 })
                        }
                        className="w-28 text-right"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <Input
                        type="number"
                        min="0"
                        step="any"
                        value={line.discount}
                        onChange={(e) =>
                          updateLine(line.key, { discount: Number(e.target.value) || 0 })
                        }
                        className="w-24 text-right"
                      />
                    </td>
                    <td className="num px-3 py-2 text-right">
                      {formatRupiah(line.quantity * line.unitCost - line.discount)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="ghost"
                        onClick={() => setLines((prev) => prev.filter((l) => l.key !== line.key))}
                      >
                        Hapus
                      </Button>
                    </td>
                  </tr>
                ))}
                {lines.length === 0 && (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState message="Belum ada item." />
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-3">
              <div>
                <Label>Biaya tambahan (ongkir, dll)</Label>
                <Input
                  type="number"
                  min="0"
                  step="any"
                  value={additionalCost}
                  onChange={(e) => setAdditionalCost(e.target.value)}
                />
              </div>
              <div>
                <Label>Diskon nota</Label>
                <Input
                  type="number"
                  min="0"
                  step="any"
                  value={headerDiscount}
                  onChange={(e) => setHeaderDiscount(e.target.value)}
                />
              </div>
              <div>
                <Label>Catatan</Label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1 text-sm">
              <Row label="Subtotal" value={formatRupiah(subtotal)} />
              <Row label="Diskon item" value={formatRupiah(itemDiscount)} />
              <Row label="Diskon nota" value={formatRupiah(Number(headerDiscount) || 0)} />
              <Row label="Biaya tambahan" value={formatRupiah(Number(additionalCost) || 0)} />
              <Row label="Total" value={formatRupiah(grandTotal)} bold />
            </div>
          </div>

          <ErrorText>{error}</ErrorText>

          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              disabled={!canSubmit || createMutation.isPending}
              onClick={() => createMutation.mutate(false)}
            >
              Simpan Draft
            </Button>
            <Button
              disabled={!canSubmit || createMutation.isPending}
              onClick={() => createMutation.mutate(true)}
            >
              Simpan & Pesan
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

function PurchaseDetailModal({
  purchaseId,
  onClose,
  onChanged,
}: {
  purchaseId: string
  onClose: () => void
  onChanged: () => void
}) {
  const queryClient = useQueryClient()
  const hasPermission = useAuth((state) => state.hasPermission)
  const [receiveAmounts, setReceiveAmounts] = useState<Record<string, string>>({})
  const [receiveNote, setReceiveNote] = useState('')
  const [error, setError] = useState('')

  const detailQuery = useQuery({
    queryKey: ['purchase', purchaseId],
    queryFn: () => apiRequest<Purchase>(`/purchases/${purchaseId}`),
  })
  const purchase = detailQuery.data

  function handleSuccess() {
    void queryClient.invalidateQueries({ queryKey: ['purchases'] })
    void queryClient.invalidateQueries({ queryKey: ['purchase', purchaseId] })
    onChanged()
  }

  const actionMutation = useMutation({
    mutationFn: (segment: 'order' | 'cancel') =>
      apiRequest(`/purchases/${purchaseId}/${segment}`, { method: 'POST' }),
    onSuccess: handleSuccess,
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal memproses pembelian.'),
  })

  const receiveMutation = useMutation({
    mutationFn: () =>
      apiRequest(`/purchases/${purchaseId}/receive`, {
        method: 'POST',
        body: {
          items: (purchase?.items ?? [])
            .map((item) => ({
              purchase_item_id: item.id,
              quantity: Number(receiveAmounts[item.id] ?? '0') || 0,
            }))
            .filter((line) => line.quantity > 0),
          notes: receiveNote || null,
        },
      }),
    onSuccess: () => {
      setReceiveAmounts({})
      setReceiveNote('')
      setError('')
      handleSuccess()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menerima barang.'),
  })

  const receivable =
    purchase !== undefined &&
    !['cancelled', 'received'].includes(purchase.status) &&
    hasPermission('purchase.receive')
  const hasReceiveInput = Object.values(receiveAmounts).some((v) => (Number(v) || 0) > 0)

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-6">
      <Card className="w-full max-w-3xl">
        <CardHeader
          title={purchase ? `Pembelian ${purchase.number}` : 'Detail Pembelian'}
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        {!purchase ? (
          <EmptyState message="Memuat…" />
        ) : (
          <div className="space-y-4 p-4">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <Field label="Supplier" value={purchase.supplier_name ?? '-'} />
              <Field label="Invoice" value={purchase.invoice_no ?? '-'} />
              <div>
                <div className="text-xs text-slate-400">Status</div>
                <StatusBadge status={purchase.status} />
              </div>
            </div>

            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="px-3 py-2">Produk</th>
                  <th className="px-3 py-2 text-right">Dipesan</th>
                  <th className="px-3 py-2 text-right">Diterima</th>
                  <th className="px-3 py-2 text-right">Sisa</th>
                  <th className="px-3 py-2 text-right">Harga/unit</th>
                  {receivable && <th className="px-3 py-2 text-right">Terima sekarang</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {purchase.items.map((item) => (
                  <tr key={item.id}>
                    <td className="px-3 py-2">
                      <div className="font-medium">{item.product_name}</div>
                      <div className="text-xs text-slate-400">{item.sku}</div>
                    </td>
                    <td className="num px-3 py-2 text-right">{formatNumber(item.quantity)}</td>
                    <td className="num px-3 py-2 text-right">
                      {formatNumber(item.received_quantity)}
                    </td>
                    <td className="num px-3 py-2 text-right">
                      {formatNumber(item.remaining_quantity)}
                    </td>
                    <td className="num px-3 py-2 text-right">{formatRupiah(item.unit_cost)}</td>
                    {receivable && (
                      <td className="px-3 py-2 text-right">
                        <Input
                          type="number"
                          min="0"
                          step="any"
                          value={receiveAmounts[item.id] ?? ''}
                          placeholder={item.remaining_quantity}
                          onChange={(e) =>
                            setReceiveAmounts((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                          className="w-24 text-right"
                        />
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="ml-auto max-w-xs space-y-1 text-sm">
              <Row label="Subtotal" value={formatRupiah(purchase.subtotal)} />
              <Row label="Diskon" value={formatRupiah(purchase.discount_total)} />
              <Row label="Biaya tambahan" value={formatRupiah(purchase.additional_cost)} />
              <Row label="Total" value={formatRupiah(purchase.total)} bold />
            </div>

            {receivable && (
              <div>
                <Label>Catatan penerimaan (opsional)</Label>
                <Input
                  value={receiveNote}
                  onChange={(e) => setReceiveNote(e.target.value)}
                  placeholder="Kondisi barang, no. surat jalan…"
                />
              </div>
            )}

            {purchase.receipts.length > 0 && (
              <div className="text-sm">
                <div className="mb-1 font-medium text-slate-600">Riwayat penerimaan</div>
                <ul className="space-y-1">
                  {purchase.receipts.map((receipt) => (
                    <li key={receipt.id} className="rounded-lg bg-slate-50 px-3 py-2">
                      <div className="flex justify-between">
                        <span className="font-medium">{receipt.number}</span>
                        <span className="text-xs text-slate-400">
                          {formatDate(receipt.received_at)}
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        {receipt.items.length} item ·{' '}
                        {formatNumber(
                          receipt.items.reduce((s, i) => s + Number(i.base_quantity), 0),
                        )}{' '}
                        satuan dasar
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <ErrorText>{error}</ErrorText>

            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-3">
              {purchase.status === 'draft' && hasPermission('purchase.update') && (
                <Button
                  variant="secondary"
                  disabled={actionMutation.isPending}
                  onClick={() => actionMutation.mutate('order')}
                >
                  Tandai Dipesan
                </Button>
              )}
              {['draft', 'ordered'].includes(purchase.status) &&
                hasPermission('purchase.update') && (
                  <Button
                    variant="danger"
                    disabled={actionMutation.isPending}
                    onClick={() => actionMutation.mutate('cancel')}
                  >
                    Batalkan
                  </Button>
                )}
              {receivable && (
                <Button
                  disabled={!hasReceiveInput || receiveMutation.isPending}
                  onClick={() => receiveMutation.mutate()}
                >
                  Terima Barang
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-medium">{value}</div>
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
