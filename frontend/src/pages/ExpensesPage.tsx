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
import { formatDateOnly, formatRupiah, today } from '../lib/format'
import type { Expense, ExpenseCategory, ExpenseReport, Paginated } from '../types'
import { useAuth } from '../store/auth'

const METHOD_LABELS: Record<string, string> = {
  cash: 'Tunai',
  transfer: 'Transfer',
  other: 'Lainnya',
}

function monthStart() {
  const now = new Date()
  const offset = now.getTimezoneOffset()
  const local = new Date(now.getTime() - offset * 60 * 1000)
  return `${local.toISOString().slice(0, 7)}-01`
}

export default function ExpensesPage() {
  const hasPermission = useAuth((state) => state.hasPermission)
  const [dateFrom, setDateFrom] = useState(monthStart())
  const [dateTo, setDateTo] = useState(today())
  const [categoryId, setCategoryId] = useState('')
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)

  const queryClient = useQueryClient()

  const categoriesQuery = useQuery({
    queryKey: ['expense-categories'],
    queryFn: () => apiRequest<{ data: ExpenseCategory[] }>('/expense-categories'),
  })

  const reportQuery = useQuery({
    queryKey: ['expense-report', dateFrom, dateTo],
    queryFn: () =>
      apiRequest<ExpenseReport>(`/reports/expenses?from=${dateFrom}&to=${dateTo}`),
  })

  const listQuery = useQuery({
    queryKey: ['expenses', page, dateFrom, dateTo, categoryId],
    queryFn: () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: '25',
        date_from: dateFrom,
        date_to: dateTo,
      })
      if (categoryId) params.set('category_id', categoryId)
      return apiRequest<Paginated<Expense>>(`/expenses?${params.toString()}`)
    },
  })

  const pageSize = listQuery.data?.page_size ?? 25
  const totalCount = listQuery.data?.total ?? 0
  const lastPage = Math.max(Math.ceil(totalCount / pageSize), 1)

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ['expenses'] })
    void queryClient.invalidateQueries({ queryKey: ['expense-report'] })
  }

  return (
    <div className="space-y-4 p-6">
      <Card>
        <CardHeader
          title="Pengeluaran"
          actions={
            hasPermission('expense.update') && (
              <Button onClick={() => setCreateOpen(true)}>Catat Pengeluaran</Button>
            )
          }
        />
        <div className="grid grid-cols-2 gap-3 p-4 md:grid-cols-4">
          <div>
            <Label>Dari tanggal</Label>
            <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </div>
          <div>
            <Label>Sampai tanggal</Label>
            <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </div>
          <div>
            <Label>Kategori</Label>
            <select
              value={categoryId}
              onChange={(e) => {
                setCategoryId(e.target.value)
                setPage(1)
              }}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            >
              <option value="">Semua kategori</option>
              {categoriesQuery.data?.data.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <div className="w-full rounded-lg bg-slate-50 px-3 py-2">
              <div className="text-xs text-slate-400">Total periode</div>
              <div className="text-lg font-semibold text-slate-700">
                {formatRupiah(reportQuery.data?.total)}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {reportQuery.data && reportQuery.data.by_category.length > 0 && (
        <Card className="overflow-hidden">
          <CardHeader title="Ringkasan per Kategori" />
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Kategori</th>
                <th className="px-4 py-2 text-right">Jumlah</th>
                <th className="px-4 py-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {reportQuery.data.by_category.map((row) => (
                <tr key={row.category_id ?? 'none'}>
                  <td className="px-4 py-2">{row.category_name}</td>
                  <td className="num px-4 py-2 text-right">{row.count}</td>
                  <td className="num px-4 py-2 text-right">{formatRupiah(row.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Card className="overflow-hidden">
        <CardHeader title="Daftar Pengeluaran" />
        {listQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Tanggal</th>
                <th className="px-4 py-2">Kategori</th>
                <th className="px-4 py-2">Metode</th>
                <th className="px-4 py-2">Keterangan</th>
                <th className="px-4 py-2 text-right">Nominal</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {listQuery.data?.data.map((expense) => (
                <tr key={expense.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {formatDateOnly(expense.expense_date)}
                  </td>
                  <td className="px-4 py-2">{expense.category_name ?? '-'}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {METHOD_LABELS[expense.payment_method] ?? expense.payment_method}
                  </td>
                  <td className="max-w-[18rem] truncate px-4 py-2 text-slate-500">
                    {expense.description ?? '-'}
                  </td>
                  <td className="num px-4 py-2 text-right font-medium">
                    {formatRupiah(expense.amount)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {hasPermission('expense.update') && (
                      <CancelButton expense={expense} onChanged={refresh} />
                    )}
                  </td>
                </tr>
              ))}
              {listQuery.data?.data.length === 0 && (
                <tr>
                  <td colSpan={6}>
                    <EmptyState message="Belum ada pengeluaran pada periode ini." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2 text-sm">
          <span className="text-slate-400">Total {totalCount} pengeluaran</span>
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
        <CreateExpenseModal
          categories={categoriesQuery.data?.data ?? []}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false)
            refresh()
            void queryClient.invalidateQueries({ queryKey: ['expense-categories'] })
          }}
        />
      )}
    </div>
  )
}

function CancelButton({ expense, onChanged }: { expense: Expense; onChanged: () => void }) {
  const [error, setError] = useState('')
  const mutation = useMutation({
    mutationFn: () => apiRequest(`/expenses/${expense.id}/cancel`, { method: 'POST' }),
    onSuccess: () => {
      setError('')
      onChanged()
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal membatalkan.'),
  })

  if (expense.cancelled_at) {
    return <span className="text-xs text-red-500">Dibatalkan</span>
  }
  return (
    <span className="inline-flex items-center gap-2">
      {error && <span className="text-xs text-red-600">{error}</span>}
      <Button
        variant="ghost"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        Batalkan
      </Button>
    </span>
  )
}

function CreateExpenseModal({
  categories,
  onClose,
  onCreated,
}: {
  categories: ExpenseCategory[]
  onClose: () => void
  onCreated: () => void
}) {
  const [localCategories, setLocalCategories] = useState<ExpenseCategory[]>(categories)
  const [categoryId, setCategoryId] = useState('')
  const [expenseDate, setExpenseDate] = useState(today())
  const [amount, setAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('cash')
  const [description, setDescription] = useState('')
  const [showAddCategory, setShowAddCategory] = useState(false)
  const [newCategory, setNewCategory] = useState('')
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<Expense>('/expenses', {
        method: 'POST',
        body: {
          category_id: categoryId || null,
          expense_date: expenseDate,
          amount: Number(amount),
          payment_method: paymentMethod,
          description: description.trim() || null,
        },
      }),
    onSuccess: () => onCreated(),
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menyimpan pengeluaran.'),
  })

  const categoryMutation = useMutation({
    mutationFn: () =>
      apiRequest<ExpenseCategory>('/expense-categories', {
        method: 'POST',
        body: { name: newCategory.trim() },
      }),
    onSuccess: (category) => {
      setLocalCategories((prev) => [...prev, category])
      setCategoryId(category.id)
      setNewCategory('')
      setError('')
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menambah kategori.'),
  })

  const valid = Number(amount) > 0 && expenseDate !== ''

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader
          title="Catat Pengeluaran"
          actions={
            <Button variant="ghost" onClick={onClose}>
              Tutup
            </Button>
          }
        />
        <div className="space-y-3 p-4">
          <div>
            <Label>Kategori</Label>
            <div className="flex gap-2">
              <select
                value={categoryId}
                onChange={(e) => setCategoryId(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
              >
                <option value="">Tanpa kategori</option>
                {localCategories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
              <Button variant="secondary" onClick={() => setShowAddCategory((v) => !v)}>
                +
              </Button>
            </div>
          </div>

          {showAddCategory && (
            <div className="flex gap-2">
              <Input
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                placeholder="Nama kategori baru"
              />
              <Button
                variant="secondary"
                disabled={!newCategory.trim() || categoryMutation.isPending}
                onClick={() => categoryMutation.mutate()}
              >
                Tambah
              </Button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Tanggal</Label>
              <Input
                type="date"
                value={expenseDate}
                onChange={(e) => setExpenseDate(e.target.value)}
              />
            </div>
            <div>
              <Label>Nominal</Label>
              <Input
                type="number"
                step="any"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0"
                className="text-right"
              />
            </div>
          </div>

          <div>
            <Label>Metode pembayaran</Label>
            <select
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
            >
              <option value="cash">Tunai</option>
              <option value="transfer">Transfer</option>
              <option value="other">Lainnya</option>
            </select>
          </div>

          <div>
            <Label>Keterangan (opsional)</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Bayar listrik bulan ini…"
            />
          </div>

          <ErrorText>{error}</ErrorText>

          <div className="flex justify-end gap-2 border-t border-slate-100 pt-3">
            <Button variant="secondary" onClick={onClose}>
              Batal
            </Button>
            <Button
              disabled={!valid || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending && <Spinner className="border-white/40 border-t-white" />}
              Simpan
            </Button>
          </div>
        </div>
      </Card>
    </div>
  )
}

