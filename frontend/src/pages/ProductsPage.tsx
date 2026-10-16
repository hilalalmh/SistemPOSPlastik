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
import type { Category, Paginated, Product, Unit, VariantSummary } from '../types'

interface ProductDetail extends Product {
  variants: VariantSummary[]
}

export default function ProductsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState('')

  const productsQuery = useQuery({
    queryKey: ['products', search],
    queryFn: () =>
      apiRequest<Paginated<Product>>(`/products?q=${encodeURIComponent(search)}&page_size=50`),
  })

  const categoriesQuery = useQuery({
    queryKey: ['categories'],
    queryFn: () => apiRequest<Category[]>('/categories'),
  })

  const unitsQuery = useQuery({
    queryKey: ['units'],
    queryFn: () => apiRequest<Unit[]>('/units'),
  })

  const detailQuery = useQuery({
    queryKey: ['product-detail', selected],
    queryFn: () => apiRequest<ProductDetail>(`/products/${selected}`),
    enabled: selected !== null,
  })

  const [newProduct, setNewProduct] = useState({ name: '', brand: '', category_id: '' })
  const [newVariant, setNewVariant] = useState({
    sku: '',
    barcode: '',
    attribute_size: '',
    attribute_color: '',
    base_unit_id: '',
    min_stock: '',
    price: '',
  })

  const createProduct = useMutation({
    mutationFn: (body: unknown) => apiRequest('/products', { method: 'POST', body }),
    onSuccess: () => {
      setNewProduct({ name: '', brand: '', category_id: '' })
      setError('')
      void queryClient.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menyimpan produk.'),
  })

  const createVariant = useMutation({
    mutationFn: (body: unknown) => apiRequest('/variants', { method: 'POST', body }),
    onSuccess: () => {
      setNewVariant({
        sku: '',
        barcode: '',
        attribute_size: '',
        attribute_color: '',
        base_unit_id: '',
        min_stock: '',
        price: '',
      })
      setError('')
      void queryClient.invalidateQueries({ queryKey: ['product-detail'] })
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal menambah varian.'),
  })

  const detail = detailQuery.data

  function submitProduct(event: React.FormEvent) {
    event.preventDefault()
    if (!newProduct.name.trim()) return
    setError('')
    createProduct.mutate({
      name: newProduct.name.trim(),
      brand: newProduct.brand || null,
      category_id: newProduct.category_id || null,
    })
  }

  function submitVariant(event: React.FormEvent) {
    event.preventDefault()
    if (!detail || !newVariant.sku.trim() || !newVariant.base_unit_id) return
    setError('')
    createVariant.mutate({
      product_id: detail.id,
      sku: newVariant.sku.trim(),
      barcode: newVariant.barcode || null,
      attribute_size: newVariant.attribute_size || null,
      attribute_color: newVariant.attribute_color || null,
      base_unit_id: newVariant.base_unit_id,
      min_stock: newVariant.min_stock ? Number(newVariant.min_stock) : null,
      prices: newVariant.price
        ? [{ unit_id: newVariant.base_unit_id, min_qty: 0, unit_price: Number(newVariant.price) }]
        : [],
    })
  }

  return (
    <div className="grid grid-cols-1 gap-4 p-6 lg:grid-cols-[1fr_360px]">
      <Card className="overflow-hidden">
        <CardHeader
          title="Daftar Produk"
          actions={
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari produk…"
              className="w-56"
            />
          }
        />
        {productsQuery.isLoading ? (
          <EmptyState message="Memuat…" />
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400">
              <tr>
                <th className="px-4 py-2">Nama</th>
                <th className="px-4 py-2">Merek</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {productsQuery.data?.data.map((product) => (
                <tr key={product.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2 font-medium">{product.name}</td>
                  <td className="px-4 py-2 text-slate-500">{product.brand ?? '-'}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        product.is_active
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {product.is_active ? 'Aktif' : 'Nonaktif'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <Button variant="ghost" onClick={() => setSelected(product.id)}>
                      Detail
                    </Button>
                  </td>
                </tr>
              ))}
              {productsQuery.data?.data.length === 0 && (
                <tr>
                  <td colSpan={4}>
                    <EmptyState message="Belum ada produk." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader title="Tambah Produk" />
          <form onSubmit={submitProduct} className="space-y-3 p-4">
            <div>
              <Label>Nama produk</Label>
              <Input
                value={newProduct.name}
                onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
                required
              />
            </div>
            <div>
              <Label>Merek</Label>
              <Input
                value={newProduct.brand}
                onChange={(e) => setNewProduct({ ...newProduct, brand: e.target.value })}
              />
            </div>
            <div>
              <Label>Kategori</Label>
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={newProduct.category_id}
                onChange={(e) => setNewProduct({ ...newProduct, category_id: e.target.value })}
              >
                <option value="">-</option>
                {categoriesQuery.data?.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <Button type="submit" className="w-full" disabled={createVariant.isPending}>
              Simpan Produk
            </Button>
          </form>
        </Card>

        {detail && (
          <Card>
            <CardHeader title={`Varian: ${detail.name}`} />
            <div className="border-b border-slate-100 p-4">
              {detail.variants.length === 0 ? (
                <p className="text-sm text-slate-400">Belum ada varian.</p>
              ) : (
                <ul className="space-y-2">
                  {detail.variants.map((variant) => (
                    <li key={variant.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">
                      <div className="font-medium">{variant.sku}</div>
                      <div className="text-xs text-slate-400">
                        {[variant.attribute_size, variant.attribute_color]
                          .filter(Boolean)
                          .join(' · ') || '-'}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <form onSubmit={submitVariant} className="space-y-3 p-4">
              <div>
                <Label>SKU</Label>
                <Input
                  value={newVariant.sku}
                  onChange={(e) => setNewVariant({ ...newVariant, sku: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Barcode</Label>
                  <Input
                    value={newVariant.barcode}
                    onChange={(e) => setNewVariant({ ...newVariant, barcode: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Ukuran</Label>
                  <Input
                    value={newVariant.attribute_size}
                    onChange={(e) =>
                      setNewVariant({ ...newVariant, attribute_size: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Warna</Label>
                  <Input
                    value={newVariant.attribute_color}
                    onChange={(e) =>
                      setNewVariant({ ...newVariant, attribute_color: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label>Stok minimum</Label>
                  <Input
                    type="number"
                    min={0}
                    value={newVariant.min_stock}
                    onChange={(e) => setNewVariant({ ...newVariant, min_stock: e.target.value })}
                  />
                </div>
              </div>
              <div>
                <Label>Satuan dasar</Label>
                <select
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  value={newVariant.base_unit_id}
                  onChange={(e) => setNewVariant({ ...newVariant, base_unit_id: e.target.value })}
                  required
                >
                  <option value="">-</option>
                  {unitsQuery.data?.map((unit) => (
                    <option key={unit.id} value={unit.id}>
                      {unit.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label>Harga jual (per satuan dasar)</Label>
                <Input
                  type="number"
                  min={0}
                  value={newVariant.price}
                  onChange={(e) => setNewVariant({ ...newVariant, price: e.target.value })}
                />
              </div>
              <Button type="submit" className="w-full" disabled={createVariant.isPending}>
                {createVariant.isPending && <Spinner className="border-white/40 border-t-white" />}
                Tambah Varian
              </Button>
            </form>
          </Card>
        )}

        <ErrorText>{error}</ErrorText>
      </div>
    </div>
  )
}
