import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { Button, Card, CardHeader, EmptyState, ErrorText, Input, Label } from '../components/ui'
import { apiRequest, RequestError } from '../lib/api'
import type { LabelData, LabelPreview, Paginated, VariantSummary } from '../types'

const TEMPLATES: Record<string, { width: string; height: string; label: string }> = {
  '40x30': { width: '40mm', height: '30mm', label: '40 × 30 mm' },
  '50x30': { width: '50mm', height: '30mm', label: '50 × 30 mm' },
  '33x25': { width: '33mm', height: '25mm', label: '33 × 25 mm' },
}

interface PickedVariant {
  variantId: string
  productName: string
  sku: string
  copies: number
}

export default function LabelPrintPage() {
  const [search, setSearch] = useState('')
  const [template, setTemplate] = useState('40x30')
  const [picked, setPicked] = useState<PickedVariant[]>([])
  const [preview, setPreview] = useState<LabelPreview | null>(null)
  const [error, setError] = useState('')

  const searchQuery = useQuery({
    queryKey: ['variants', search, 'label'],
    queryFn: () =>
      apiRequest<Paginated<VariantSummary>>(
        `/variants?q=${encodeURIComponent(search.trim())}&page_size=20`,
      ),
    enabled: search.trim().length > 0,
  })

  const previewMutation = useMutation({
    mutationFn: () =>
      apiRequest<LabelPreview>('/labels/preview', {
        method: 'POST',
        body: {
          items: picked.map((p) => ({ variant_id: p.variantId, copies: p.copies })),
          template,
        },
      }),
    onSuccess: (data) => {
      setPreview(data)
      setError('')
    },
    onError: (err) =>
      setError(err instanceof RequestError ? err.message : 'Gagal memuat pratinjau.'),
  })

  function addToPick(variant: VariantSummary) {
    setSearch('')
    setPicked((prev) => {
      if (prev.some((p) => p.variantId === variant.id)) return prev
      return [
        ...prev,
        {
          variantId: variant.id,
          productName: variant.product_name ?? variant.sku,
          sku: variant.sku,
          copies: 10,
        },
      ]
    })
  }

  const dims = TEMPLATES[template] ?? TEMPLATES['40x30']
  const totalLabels = picked.reduce((sum, p) => sum + (p.copies || 0), 0)
  const missingBarcode = preview?.labels.some((l) => !l.has_barcode) ?? false

  return (
    <div className="grid grid-cols-1 gap-4 p-6 xl:grid-cols-[380px_1fr]">
      <div className="no-print space-y-4">
        <Card>
          <CardHeader title="Pilih Varian" />
          <div className="space-y-3 p-4">
            <div>
              <Label>Cari nama produk / SKU / barcode</Label>
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Ketik untuk mencari…"
              />
              {search.trim().length > 0 && (
                <div className="mt-1 max-h-56 overflow-y-auto rounded-lg border border-slate-200">
                  {searchQuery.data?.data.length ? (
                    searchQuery.data.data.map((variant) => (
                      <button
                        key={variant.id}
                        type="button"
                        className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                        onClick={() => addToPick(variant)}
                      >
                        <span className="font-medium">{variant.product_name ?? variant.sku}</span>
                        <span className="ml-2 text-xs text-slate-400">{variant.sku}</span>
                      </button>
                    ))
                  ) : (
                    <div className="px-3 py-2 text-sm text-slate-400">
                      {searchQuery.isLoading ? 'Mencari…' : 'Tidak ada hasil.'}
                    </div>
                  )}
                </div>
              )}
            </div>

            <div>
              <Label>Ukuran label</Label>
              <select
                className="w-full rounded-lg border border-slate-300 px-2 py-2 text-sm"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
              >
                {Object.entries(TEMPLATES).map(([value, meta]) => (
                  <option key={value} value={value}>
                    {meta.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title={`Varian Dipilih (${picked.length})`} />
          <div className="space-y-2 p-4">
            {picked.length === 0 ? (
              <EmptyState message="Belum ada varian dipilih." />
            ) : (
              picked.map((item) => (
                <div key={item.variantId} className="flex items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{item.productName}</div>
                    <div className="text-xs text-slate-400">{item.sku}</div>
                  </div>
                  <Input
                    type="number"
                    min={1}
                    value={item.copies}
                    onChange={(e) =>
                      setPicked((prev) =>
                        prev.map((p) =>
                          p.variantId === item.variantId
                            ? { ...p, copies: Number(e.target.value) || 1 }
                            : p,
                        ),
                      )
                    }
                    className="w-20 text-right"
                  />
                  <button
                    type="button"
                    className="text-xs text-red-500 hover:underline"
                    onClick={() =>
                      setPicked((prev) => prev.filter((p) => p.variantId !== item.variantId))
                    }
                  >
                    Hapus
                  </button>
                </div>
              ))
            )}
          </div>
        </Card>

        <ErrorText>{error}</ErrorText>

        <div className="flex gap-2">
          <Button
            className="flex-1"
            disabled={picked.length === 0 || previewMutation.isPending}
            onClick={() => previewMutation.mutate()}
          >
            Pratinjau
          </Button>
          <Button
            variant="secondary"
            className="flex-1"
            disabled={!preview || preview.labels.length === 0}
            onClick={() => window.print()}
          >
            Cetak
          </Button>
        </div>
      </div>

      <Card className="overflow-hidden">
        <CardHeader title={`Pratinjau Label${preview ? ` · ${totalLabels} label` : ''}`} />
        <div className="p-4">
          {missingBarcode && (
            <div className="no-print mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
              Sebagian varian belum punya barcode terdaftar; label memakai SKU sebagai kode.
            </div>
          )}
          {!preview || preview.labels.length === 0 ? (
            <EmptyState message="Pilih varian lalu tekan Pratinjau." />
          ) : (
            <div id="label-print" className="flex flex-wrap gap-2 bg-slate-50 p-3">
              {preview.labels.flatMap((label) =>
                Array.from({ length: label.copies }, (_, index) => (
                  <LabelCard
                    key={`${label.variant_id}-${index}`}
                    label={label}
                    width={dims.width}
                    height={dims.height}
                  />
                )),
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

function LabelCard({
  label,
  width,
  height,
}: {
  label: LabelData
  width: string
  height: string
}) {
  const attrs = Object.values(label.attributes).join(' · ')
  return (
    <div
      className="flex flex-col items-center justify-between border border-slate-300 bg-white p-2 text-center"
      style={{ width, height }}
    >
      <div className="w-full">
        <div className="line-clamp-2 text-[9px] font-semibold leading-tight">
          {label.product_name}
        </div>
        {attrs && <div className="text-[8px] leading-tight text-slate-500">{attrs}</div>}
      </div>
      <img src={label.barcode_svg} alt={label.code} className="max-h-10 w-full object-contain" />
      <div className="num text-[8px] tracking-wide">{label.code}</div>
    </div>
  )
}
