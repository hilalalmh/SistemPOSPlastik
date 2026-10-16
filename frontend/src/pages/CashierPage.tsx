import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { Button, Card, ErrorText, Input, Label, Spinner } from '../components/ui'
import { apiRequest, RequestError } from '../lib/api'
import { formatNumber, formatRupiah } from '../lib/format'
import type {
  CatalogItem,
  CashSession,
  QuoteResponse,
  Sale,
} from '../types'

interface CartLine {
  key: string
  catalog: CatalogItem
  unitId: string
  quantity: number
  discount: number
}

interface PaymentLine {
  key: string
  method: string
  amount: number
  reference_no: string
}

const PAYMENT_METHODS = [
  { value: 'cash', label: 'Tunai' },
  { value: 'transfer', label: 'Transfer' },
  { value: 'debit', label: 'Kartu Debit' },
  { value: 'qris', label: 'QRIS' },
]

function newKey() {
  return crypto.randomUUID()
}

export default function CashierPage() {
  const queryClient = useQueryClient()

  const sessionQuery = useQuery({
    queryKey: ['cash-session', 'current'],
    queryFn: () => apiRequest<{ data: CashSession | null }>('/cash-sessions/current'),
  })

  const session = sessionQuery.data?.data ?? null

  const [search, setSearch] = useState('')
  const [cart, setCart] = useState<CartLine[]>([])
  const [idempotencyKey, setIdempotencyKey] = useState(newKey())
  const [receipt, setReceipt] = useState<Sale | null>(null)
  const [error, setError] = useState('')

  const catalogQuery = useQuery({
    queryKey: ['catalog', search],
    queryFn: () =>
      apiRequest<{ data: CatalogItem[] }>(
        `/catalog/search?q=${encodeURIComponent(search)}&limit=24`,
      ),
    enabled: session !== null,
  })

  const quoteItems = useMemo(
    () =>
      cart.map((line) => ({
        variant_id: line.catalog.variant_id,
        unit_id: line.unitId,
        quantity: line.quantity,
        discount_amount: line.discount,
      })),
    [cart],
  )

  const quoteQuery = useQuery({
    queryKey: ['quote', JSON.stringify(quoteItems)],
    queryFn: () =>
      apiRequest<QuoteResponse>('/sales/quotes', { method: 'POST', body: { items: quoteItems } }),
    enabled: quoteItems.length > 0,
  })

  const [payments, setPayments] = useState<PaymentLine[]>([
    { key: newKey(), method: 'cash', amount: 0, reference_no: '' },
  ])

  const total = Number(quoteQuery.data?.total ?? 0)
  const effectivePayments = payments.map((payment) =>
    payment.amount === 0 && payments.length === 1 ? { ...payment, amount: total } : payment,
  )
  const paidTotal = effectivePayments.reduce((sum, p) => sum + (p.amount || 0), 0)
  const cashPaid = effectivePayments
    .filter((p) => p.method === 'cash')
    .reduce((sum, p) => sum + (p.amount || 0), 0)
  const change = Math.max(cashPaid - total, 0)

  function addToCart(item: CatalogItem) {
    setError('')
    setCart((prev) => {
      const existing = prev.find((line) => line.catalog.variant_id === item.variant_id)
      if (existing && existing.unitId === item.base_unit_id) {
        return prev.map((line) =>
          line.key === existing.key ? { ...line, quantity: line.quantity + 1 } : line,
        )
      }
      return [
        ...prev,
        {
          key: newKey(),
          catalog: item,
          unitId: item.base_unit_id,
          quantity: 1,
          discount: 0,
        },
      ]
    })
  }

  async function scanBarcode(event: React.FormEvent) {
    event.preventDefault()
    if (!search.trim()) return
    try {
      const item = await apiRequest<CatalogItem>(`/catalog/barcode/${encodeURIComponent(search.trim())}`)
      addToCart(item)
      setSearch('')
    } catch {
      // fall back to search results already displayed
    }
  }

  const checkout = useMutation({
    mutationFn: async () => {
      if (!session) throw new Error('Shift belum dibuka.')
      return apiRequest<Sale>('/sales', {
        method: 'POST',
        headers: { 'Idempotency-Key': idempotencyKey },
        body: {
          cash_session_id: session.id,
          items: quoteItems,
          payments: effectivePayments
            .filter((p) => p.amount > 0)
            .map((p) => ({
              method: p.method,
              amount: p.amount,
              reference_no: p.reference_no || null,
            })),
        },
      })
    },
    onSuccess: (sale) => {
      setReceipt(sale)
      setCart([])
      setPayments([{ key: newKey(), method: 'cash', amount: 0, reference_no: '' }])
      setIdempotencyKey(newKey())
      setError('')
      void queryClient.invalidateQueries({ queryKey: ['cash-session', 'current'] })
      void queryClient.invalidateQueries({ queryKey: ['catalog'] })
    },
    onError: (err) => {
      setError(err instanceof RequestError ? err.message : 'Checkout gagal.')
    },
  })

  if (sessionQuery.isLoading) {
    return <div className="p-6 text-slate-500">Memuat shift…</div>
  }

  return (
    <div className="flex h-full flex-col">
      <ShiftBar session={session} onChanged={() => void queryClient.invalidateQueries()} />

      {session && (
        <div className="grid flex-1 grid-cols-1 gap-4 overflow-hidden p-4 lg:grid-cols-[1fr_420px]">
          <div className="flex min-h-0 flex-col gap-4">
            <Card className="p-3">
              <form onSubmit={scanBarcode} className="flex gap-2">
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Scan barcode / cari produk…"
                  autoFocus
                />
                <Button type="submit" variant="secondary">
                  Tambah
                </Button>
              </form>
            </Card>

            <Card className="min-h-0 flex-1 overflow-y-auto">
              <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3">
                {catalogQuery.data?.data.map((item) => (
                  <button
                    key={item.variant_id}
                    onClick={() => addToCart(item)}
                    className="rounded-lg border border-slate-200 p-3 text-left transition hover:border-emerald-400 hover:bg-emerald-50"
                  >
                    <div className="line-clamp-2 text-sm font-medium text-slate-800">
                      {item.product_name}
                    </div>
                    <div className="text-xs text-slate-400">{item.sku}</div>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="text-sm font-semibold text-emerald-700">
                        {formatRupiah(item.price_from)}
                      </span>
                      <span className="text-xs text-slate-500">
                        stok {formatNumber(item.stock_base)} {item.base_unit_name}
                      </span>
                    </div>
                  </button>
                ))}
                {catalogQuery.data?.data.length === 0 && (
                  <div className="col-span-full py-8 text-center text-sm text-slate-400">
                    Produk tidak ditemukan.
                  </div>
                )}
              </div>
            </Card>
          </div>

          <Card className="flex min-h-0 flex-col">
            <div className="flex-1 overflow-y-auto border-b border-slate-100">
              {cart.length === 0 ? (
                <div className="py-10 text-center text-sm text-slate-400">Keranjang kosong.</div>
              ) : (
                <ul className="divide-y divide-slate-100">
                  {cart.map((line) => {
                    const quoteLine = quoteQuery.data?.items.find(
                      (q) => q.variant_id === line.catalog.variant_id && q.unit_id === line.unitId,
                    )
                    return (
                      <li key={line.key} className="p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate text-sm font-medium">
                              {line.catalog.product_name}
                            </div>
                            <div className="text-xs text-slate-400">{line.catalog.sku}</div>
                          </div>
                          <button
                            className="text-xs text-red-500 hover:underline"
                            onClick={() =>
                              setCart((prev) => prev.filter((l) => l.key !== line.key))
                            }
                          >
                            Hapus
                          </button>
                        </div>
                        <div className="mt-2 grid grid-cols-3 gap-2">
                          <div>
                            <Label>Satuan</Label>
                            <select
                              className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
                              value={line.unitId}
                              onChange={(e) =>
                                setCart((prev) =>
                                  prev.map((l) =>
                                    l.key === line.key ? { ...l, unitId: e.target.value } : l,
                                  ),
                                )
                              }
                            >
                              {line.catalog.units.map((unit) => (
                                <option key={unit.unit_id} value={unit.unit_id}>
                                  {unit.unit_name}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div>
                            <Label>Qty</Label>
                            <Input
                              type="number"
                              min={0}
                              step="any"
                              value={line.quantity}
                              onChange={(e) =>
                                setCart((prev) =>
                                  prev.map((l) =>
                                    l.key === line.key
                                      ? { ...l, quantity: Number(e.target.value) }
                                      : l,
                                  ),
                                )
                              }
                            />
                          </div>
                          <div>
                            <Label>Diskon</Label>
                            <Input
                              type="number"
                              min={0}
                              value={line.discount}
                              onChange={(e) =>
                                setCart((prev) =>
                                  prev.map((l) =>
                                    l.key === line.key
                                      ? { ...l, discount: Number(e.target.value) }
                                      : l,
                                  ),
                                )
                              }
                            />
                          </div>
                        </div>
                        <div className="mt-2 flex items-center justify-between text-sm">
                          <span className="text-slate-500">
                            @ {formatRupiah(quoteLine?.unit_price)}
                          </span>
                          <span className="font-semibold">
                            {formatRupiah(quoteLine?.line_total)}
                          </span>
                        </div>
                        {quoteLine && !quoteLine.stock_sufficient && (
                          <div className="mt-1 text-xs text-red-600">Stok tidak mencukupi</div>
                        )}
                      </li>
                    )
                  })}
                </ul>
              )}
            </div>

            <div className="space-y-3 p-3">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Subtotal</span>
                <span className="num">{formatRupiah(quoteQuery.data?.subtotal)}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">Diskon</span>
                <span className="num">-{formatRupiah(quoteQuery.data?.discount_total)}</span>
              </div>
              <div className="flex items-center justify-between text-lg font-bold">
                <span>Total</span>
                <span className="num text-emerald-700">{formatRupiah(total)}</span>
              </div>

              <div className="space-y-2 border-t border-slate-100 pt-3">
                {effectivePayments.map((payment) => (
                  <div key={payment.key} className="flex items-center gap-2">
                    <select
                      className="w-28 rounded-lg border border-slate-300 px-2 py-2 text-sm"
                      value={payment.method}
                      onChange={(e) =>
                        setPayments((prev) =>
                          prev.map((p) =>
                            p.key === payment.key ? { ...p, method: e.target.value } : p,
                          ),
                        )
                      }
                    >
                      {PAYMENT_METHODS.map((m) => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                    </select>
                    <Input
                      type="number"
                      min={0}
                      value={payment.amount}
                      onChange={(e) =>
                        setPayments((prev) =>
                          prev.map((p) =>
                            p.key === payment.key ? { ...p, amount: Number(e.target.value) } : p,
                          ),
                        )
                      }
                    />
                    {payments.length > 1 && (
                      <button
                        className="text-xs text-red-500"
                        onClick={() =>
                          setPayments((prev) => prev.filter((p) => p.key !== payment.key))
                        }
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() =>
                    setPayments((prev) => [
                      ...prev,
                      { key: newKey(), method: 'transfer', amount: 0, reference_no: '' },
                    ])
                  }
                >
                  + Tambah pembayaran
                </Button>
              </div>

              <div className="flex items-center justify-between text-sm text-slate-600">
                <span>Dibayar</span>
                <span className="num">{formatRupiah(paidTotal)}</span>
              </div>
              {change > 0 && (
                <div className="flex items-center justify-between text-sm font-semibold text-emerald-700">
                  <span>Kembalian</span>
                  <span className="num">{formatRupiah(change)}</span>
                </div>
              )}

              <ErrorText>{error}</ErrorText>

              <Button
                className="w-full py-3 text-base"
                disabled={cart.length === 0 || paidTotal < total || checkout.isPending}
                onClick={() => checkout.mutate()}
              >
                {checkout.isPending && <Spinner className="border-white/40 border-t-white" />}
                Bayar {formatRupiah(total)}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {receipt && <ReceiptModal sale={receipt} onClose={() => setReceipt(null)} />}
    </div>
  )
}

function ShiftBar({ session, onChanged }: { session: CashSession | null; onChanged: () => void }) {
  const [openingCash, setOpeningCash] = useState(0)
  const [countedCash, setCountedCash] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function openShift() {
    setBusy(true)
    setError('')
    try {
      await apiRequest('/cash-sessions/open', { method: 'POST', body: { opening_cash: openingCash } })
      onChanged()
    } catch (err) {
      setError(err instanceof RequestError ? err.message : 'Gagal membuka shift.')
    } finally {
      setBusy(false)
    }
  }

  async function closeShift() {
    if (!session) return
    setBusy(true)
    setError('')
    try {
      await apiRequest(`/cash-sessions/${session.id}/close`, {
        method: 'POST',
        body: { counted_cash: countedCash },
      })
      onChanged()
    } catch (err) {
      setError(err instanceof RequestError ? err.message : 'Gagal menutup shift.')
    } finally {
      setBusy(false)
    }
  }

  if (!session) {
    return (
      <div className="flex flex-wrap items-end gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <div>
          <Label>Kas awal shift</Label>
          <Input
            type="number"
            min={0}
            value={openingCash}
            onChange={(e) => setOpeningCash(Number(e.target.value))}
            className="w-48"
          />
        </div>
        <Button onClick={openShift} disabled={busy}>
          {busy && <Spinner className="border-white/40 border-t-white" />}
          Buka Shift
        </Button>
        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-slate-200 bg-white px-4 py-3 text-sm">
      <span className="font-medium text-emerald-700">Shift terbuka</span>
      <span className="text-slate-500">
        Kas awal {formatRupiah(session.opening_cash)} · {session.sales_count ?? 0} transaksi ·{' '}
        {formatRupiah(session.sales_total ?? '0')}
      </span>
      <div className="ml-auto flex items-end gap-2">
        <div>
          <Label>Kas fisik</Label>
          <Input
            type="number"
            min={0}
            value={countedCash}
            onChange={(e) => setCountedCash(Number(e.target.value))}
            className="w-40"
          />
        </div>
        <Button variant="secondary" onClick={closeShift} disabled={busy}>
          {busy && <Spinner />}
          Tutup Shift
        </Button>
      </div>
      {error && <span className="text-sm text-red-600">{error}</span>}
    </div>
  )
}

function ReceiptModal({ sale, onClose }: { sale: Sale; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl">
        <div className="text-center">
          <div className="text-lg font-bold text-emerald-700">Transaksi Berhasil</div>
          <div className="text-xs text-slate-400">{sale.number}</div>
        </div>
        <ul className="my-4 divide-y divide-dashed divide-slate-200 text-sm">
          {sale.items.map((item, index) => (
            <li key={index} className="flex justify-between py-1.5">
              <span>
                {item.name_snapshot}{' '}
                <span className="text-slate-400">
                  {formatNumber(item.quantity)} {item.unit_name_snapshot}
                </span>
              </span>
              <span className="num">{formatRupiah(item.line_total)}</span>
            </li>
          ))}
        </ul>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">Subtotal</span>
            <span className="num">{formatRupiah(sale.subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Diskon</span>
            <span className="num">{formatRupiah(sale.discount_total)}</span>
          </div>
          <div className="flex justify-between text-base font-bold">
            <span>Total</span>
            <span className="num">{formatRupiah(sale.total)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Dibayar</span>
            <span className="num">{formatRupiah(sale.paid_total)}</span>
          </div>
          <div className="flex justify-between font-semibold text-emerald-700">
            <span>Kembalian</span>
            <span className="num">{formatRupiah(sale.change_total)}</span>
          </div>
        </div>
        <Button className="mt-4 w-full" onClick={window.print}>
          Cetak
        </Button>
        <Button variant="secondary" className="mt-2 w-full" onClick={onClose}>
          Transaksi Baru
        </Button>
      </div>
    </div>
  )
}
