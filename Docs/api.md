# API Contract — Sistem POS Toko Plastik

**Dokumen:** `api.md`
**Status:** Kontrak baseline MVP
**Sumber:** `production.md` Bagian 8, `erd.md`, `decisions.md`
**Versi:** 1.0
**Base URL:** `/api/v1`

Kontrak ini adalah rancangan awal. Endpoint, schema, status code, dan error code menjadi acuan implementasi FastAPI dan frontend React.

---

## 1. Konvensi Umum

### 1.1 Format
- Media type: `application/json; charset=utf-8`.
- Penamaan field: `snake_case`.
- Uang dikirim sebagai **string desimal** (contoh `"50000.00"`) untuk mencegah galat floating point; frontend hanya menampilkan.
- Kuantitas/faktor konversi dikirim sebagai string desimal.
- Waktu: ISO-8601 UTC (contoh `2026-10-16T05:30:00Z`). Tampilan memakai `Asia/Jakarta`.

### 1.2 Autentikasi
- Menggunakan access + refresh token JWT (Bearer) atau sesi `HttpOnly` cookie. Pilihan final ditentukan saat implementasi; kontrak ini netral dan mengasumsikan header `Authorization: Bearer <access_token>`.
- Endpoint sensitif memerlukan permission spesifik (lihat kolom **Izin**).

### 1.3 Idempotensi
- Endpoint mutasi kritis menerima header `Idempotency-Key: <uuid>`.
- Wajib pada: `POST /sales`, `POST /purchases/{id}/receive`, `POST /returns` [P1], `POST /sales/{id}/void`.
- Jika key sama dengan request body yang sama dikirim ulang, server mengembalikan respons pertama tanpa membuat data baru.
- Jika key sama dengan body berbeda, server mengembalikan `409 IDEMPOTENCY_CONFLICT`.

### 1.4 Pagination & Filter
Query umum pada endpoint daftar:
- `page` (default 1), `page_size` (default 25, maks 100).
- `q` (pencarian teks), `sort` (contoh `-created_at`), plus filter spesifik per resource.
Respons daftar:
```json
{
  "data": [ ... ],
  "meta": { "page": 1, "page_size": 25, "total": 120, "total_pages": 5 }
}
```

### 1.5 Format Error
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Kuantitas melebihi stok tersedia.",
    "details": [
      { "field": "items[0].quantity", "message": "Stok tersedia 100 lembar." }
    ],
    "request_id": "req_01H..."
  }
}
```

Kode error umum:

| HTTP | `code` | Keterangan |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Input tidak valid |
| 401 | `UNAUTHENTICATED` | Token tidak ada/kadaluarsa |
| 403 | `FORBIDDEN` | Tidak memiliki permission |
| 404 | `NOT_FOUND` | Resource tidak ditemukan |
| 409 | `CONFLICT` | Konflik data (SKU duplikat, dsb.) |
| 409 | `INSUFFICIENT_STOCK` | Stok tidak cukup |
| 409 | `IDEMPOTENCY_CONFLICT` | Key sama, body berbeda |
| 422 | `BUSINESS_RULE_VIOLATION` | Melanggar aturan bisnis (mis. harga tidak valid) |
| 429 | `RATE_LIMITED` | Melebihi batas permintaan |
| 500 | `INTERNAL_ERROR` | Kesalahan server |

---

## 2. Autentikasi & Pengguna

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| POST | `/auth/login` | Login | publik (rate limited) |
| POST | `/auth/refresh` | Perbarui token | token refresh |
| POST | `/auth/logout` | Logout | terautentikasi |
| GET | `/auth/me` | Profil pengguna aktif | terautentikasi |
| POST | `/auth/change-password` | Ubah password sendiri | terautentikasi |
| POST | `/auth/forgot-password` | Minta reset password | publik (rate limited) |
| POST | `/auth/reset-password` | Selesaikan reset | publik (token) |

### Contoh `POST /auth/login`
Request:
```json
{ "username": "kasir1", "password": "rahasia" }
```
Respons `200`:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "name": "Budi",
    "role": "cashier",
    "permissions": ["sale.create", "sale.void"]
  }
}
```
Error: `401 UNAUTHENTICATED` (kredensial salah), `423` (akun terkunci) → gunakan `409 CONFLICT` dengan kode `ACCOUNT_LOCKED`, `429 RATE_LIMITED`.

### Pengguna & RBAC

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/users` | Daftar pengguna | `user.read` |
| POST | `/users` | Tambah pengguna | `user.create` |
| GET | `/users/{id}` | Detail pengguna | `user.read` |
| PATCH | `/users/{id}` | Ubah pengguna | `user.update` |
| POST | `/users/{id}/deactivate` | Nonaktifkan | `user.update` |
| POST | `/users/{id}/reset-password` | Reset oleh admin | `user.update` |
| GET | `/roles` | Daftar role | `role.read` |
| GET | `/permissions` | Daftar permission | `role.read` |
| PATCH | `/roles/{id}/permissions` | Ubah permission role | `role.update` |

---

## 3. Pengaturan Toko

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/settings` | Baca pengaturan toko | terautentikasi |
| PATCH | `/settings` | Ubah pengaturan toko | `settings.update` |
| GET | `/locations` | Daftar lokasi | terautentikasi |
| POST | `/locations` | Tambah lokasi | `settings.update` |

---

## 4. Produk, Varian, Satuan, Harga

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/categories` | Daftar kategori | `product.read` |
| POST | `/categories` | Tambah kategori | `product.update` |
| PATCH | `/categories/{id}` | Ubah kategori | `product.update` |
| GET | `/products` | Daftar produk (`q`, `category_id`, `is_active`, pagination) | `product.read` |
| POST | `/products` | Tambah produk | `product.update` |
| GET | `/products/{id}` | Detail produk + varian | `product.read` |
| PATCH | `/products/{id}` | Ubah produk | `product.update` |
| POST | `/products/{id}/deactivate` | Nonaktifkan produk | `product.update` |
| GET | `/variants` | Daftar varian (`q`, `product_id`, `barcode`) | `product.read` |
| POST | `/variants` | Tambah varian | `product.update` |
| GET | `/variants/{id}` | Detail varian (konversi + harga + stok) | `product.read` |
| PATCH | `/variants/{id}` | Ubah varian | `product.update` |
| POST | `/variants/{id}/deactivate` | Nonaktifkan varian | `product.update` |
| GET | `/units` | Daftar satuan | `product.read` |
| POST | `/units` | Tambah satuan | `product.update` |
| GET | `/variants/{id}/conversions` | Daftar konversi | `product.read` |
| PUT | `/variants/{id}/conversions` | Set konversi varian (batch) | `product.update` |
| GET | `/variants/{id}/prices` | Daftar harga | `product.read` |
| POST | `/variants/{id}/prices` | Tambah aturan harga | `price.update` |
| PATCH | `/prices/{id}` | Ubah harga | `price.update` |
| POST | `/prices/{id}/deactivate` | Nonaktifkan harga | `price.update` |
| GET | `/variants/{id}/price-history` | Riwayat perubahan harga | `price.read` |
| POST | `/products/import` | Impor CSV (multipart) | `product.update` |
| POST | `/products/import/preview` | Pratinjau impor | `product.update` |
| GET | `/products/export` | Ekspor CSV | `product.read` |

### Contoh `POST /variants`
```json
{
  "product_id": "uuid",
  "sku": "PLT-KRESEK-24x36-HITAM",
  "barcode": "8991234567890",
  "attributes": {
    "size": "24x36",
    "color": "Hitam",
    "thickness": "0.8mm",
    "type": "Kresek",
    "packaging": "Pak"
  },
  "base_unit_id": "uuid-lembar",
  "min_stock": "100.0000",
  "conversions": [
    { "unit_id": "uuid-lembar", "base_units_per_unit": "1.0000" },
    { "unit_id": "uuid-pak", "base_units_per_unit": "50.0000" },
    { "unit_id": "uuid-bal", "base_units_per_unit": "1000.0000" }
  ]
}
```

### Contoh `POST /variants/{id}/prices` (harga bertingkat)
```json
{
  "unit_id": "uuid-pak",
  "min_qty": "10",
  "max_qty": "49",
  "unit_price": "4700.00",
  "valid_from": "2026-10-01T00:00:00Z"
}
```
Validasi server: rentang tidak tumpang tindih dengan harga aktif lain untuk `(variant_id, unit_id)`, `unit_price >= 0`.

---

## 5. Pencarian Produk untuk Kasir

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/catalog/search` | Cari produk/varian cepat (`q`, `barcode`, `limit`) | `sale.create` |
| GET | `/catalog/barcode/{barcode}` | Cari varian via barcode | `sale.create` |
| GET | `/variants/{id}/available-units` | Satuan & harga yang berlaku | `sale.create` |

`GET /catalog/search?q=kresek&limit=20` respons ringkas:
```json
{
  "data": [
    {
      "variant_id": "uuid",
      "product_name": "Kantong Kresek",
      "sku": "PLT-KRESEK-24x36-HITAM",
      "attributes": { "size": "24x36", "color": "Hitam" },
      "barcode": "8991234567890",
      "base_unit": { "id": "uuid-lembar", "name": "Lembar" },
      "stock_base": "1850.0000",
      "price_from": "100.00"
    }
  ]
}
```

---

## 6. Persediaan

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/inventory/stock` | Saldo stok (`variant_id`, `location_id`, `low_stock`, pagination) | `inventory.read` |
| GET | `/inventory/stock/{variant_id}` | Saldo stok per varian | `inventory.read` |
| GET | `/inventory/movements` | Riwayat pergerakan (`variant_id`, `type`, `from`, `to`) | `inventory.read` |
| GET | `/inventory/low-stock` | Daftar stok menipis | `inventory.read` |
| POST | `/inventory/adjustments` | Penyesuaian stok (naik/turun) | `inventory.adjust` |
| GET | `/inventory/adjustments` | Daftar penyesuaian | `inventory.read` |
| POST | `/stock-counts` | Mulai stok opname (snapshot) | `stockcount.create` |
| GET | `/stock-counts` | Daftar opname | `stockcount.read` |
| GET | `/stock-counts/{id}` | Detail opname + item | `stockcount.read` |
| PATCH | `/stock-counts/{id}/items` | Isi hitungan fisik | `stockcount.count` |
| POST | `/stock-counts/{id}/confirm` | Konfirmasi → buat penyesuaian | `stockcount.confirm` [izin khusus] |
| POST | `/stock-counts/{id}/cancel` | Batalkan opname | `stockcount.confirm` |

### Contoh `POST /inventory/adjustments`
Header: `Idempotency-Key` opsional.
```json
{
  "location_id": "uuid",
  "variant_id": "uuid",
  "adjustment_type": "decrease",
  "quantity": "5.0000",
  "reason": "Barang rusak terkena air"
}
```
Respons `201` memuat `number`, `balance_after`.

### Contoh `PATCH /stock-counts/{id}/items`
```json
{
  "items": [
    { "variant_id": "uuid", "counted_quantity": "18.0000", "notes": "Kurang 2 lembar" }
  ]
}
```
Persyaratan: `stock_counts.status = counting`.

---

## 7. Kasir & Penjualan

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| POST | `/cash-sessions/open` | Buka shift | `session.open` |
| GET | `/cash-sessions/current` | Shift aktif kasir | `session.read` |
| POST | `/cash-sessions/{id}/close` | Tutup shift | `session.close` |
| POST | `/cash-sessions/{id}/movements` | Kas masuk/keluar | `session.cashmove` |
| GET | `/cash-sessions/{id}` | Detail shift + ringkasan | `session.read` |
| GET | `/cash-sessions` | Daftar shift | `session.read` |
| POST | `/sales/quotes` | Hitung keranjang/harga sebelum checkout | `sale.create` |
| POST | `/sales` | Checkout (atomik) | `sale.create` |
| GET | `/sales` | Daftar penjualan (`from`, `to`, `cashier_id`, `status`) | `sale.read` |
| GET | `/sales/{id}` | Detail penjualan | `sale.read` |
| GET | `/sales/{id}/receipt` | Data struk | `sale.read` |
| POST | `/sales/{id}/void` | Void penjualan | `sale.void` [izin khusus] |

### 7.1 `POST /cash-sessions/open`
```json
{ "location_id": "uuid", "opening_cash": "200000.00" }
```
Respons `201`: `{ "id": "uuid", "status": "open", "opened_at": "..." }`
Error `409 CONFLICT` bila kasir/lokasi sudah punya shift `open`.

### 7.2 `POST /sales/quotes`
Menghitung harga server-side tanpa menyimpan.
Request:
```json
{
  "items": [
    { "variant_id": "uuid", "unit_id": "uuid-pak", "quantity": "10" }
  ]
}
```
Respons `200`:
```json
{
  "items": [
    {
      "variant_id": "uuid",
      "name": "Kantong Kresek",
      "sku": "PLT-KRESEK-24x36-HITAM",
      "unit_id": "uuid-pak",
      "unit_name": "Pak",
      "conversion_factor": "50.0000",
      "base_quantity": "500.0000",
      "unit_price": "4700.00",
      "pricing_tier": { "min_qty": "10", "max_qty": "49" },
      "discount_amount": "0.00",
      "line_total": "47000.00",
      "stock_base": "1850.0000",
      "stock_sufficient": true
    }
  ],
  "subtotal": "47000.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "47000.00"
}
```

### 7.3 `POST /sales` (checkout atomik)
Header: `Idempotency-Key: <uuid>` **wajib**.
Request:
```json
{
  "cash_session_id": "uuid",
  "customer_id": null,
  "items": [
    { "variant_id": "uuid", "unit_id": "uuid-pak", "quantity": "10", "discount_amount": "0.00" }
  ],
  "payments": [
    { "method": "cash", "amount": "40000.00" },
    { "method": "qris", "amount": "7000.00", "reference_no": "QR-123" }
  ],
  "notes": null
}
```
Aturan server:
- Menghitung ulang seluruh harga, diskon, konversi, stok, dan total. **Mengabaikan** `unit_price`, `total`, `change` dari klien.
- Memvalidasi produk aktif, stok mencukupi (`SELECT ... FOR UPDATE`), diskon ≤ batas.
- Menulis `sales`, `sale_items`, `payments`, `stock_movements`, `cash_movements` dalam satu transaksi DB.
- `sum(payments.amount) >= total`; `change_total` dihitung server.
- Retry dengan `Idempotency-Key` sama mengembalikan respons pertama.

Respons `201`:
```json
{
  "id": "uuid",
  "number": "SLS-202610-000123",
  "status": "completed",
  "sold_at": "2026-10-16T05:30:00Z",
  "subtotal": "47000.00",
  "discount_total": "0.00",
  "tax_total": "0.00",
  "total": "47000.00",
  "paid_total": "47000.00",
  "change_total": "0.00",
  "items": [ { "variant_id": "uuid", "quantity": "10", "unit_name": "Pak", "unit_price": "4700.00", "line_total": "47000.00" } ],
  "payments": [
    { "method": "cash", "amount": "40000.00", "status": "confirmed" },
    { "method": "qris", "amount": "7000.00", "status": "confirmed", "reference_no": "QR-123" }
  ]
}
```
Error penting:
- `409 INSUFFICIENT_STOCK` dengan detail varian dan sisa stok.
- `409 IDEMPOTENCY_CONFLICT`.
- `422 BUSINESS_RULE_VIOLATION` (diskon melebihi batas, harga tidak ditemukan).

### 7.4 `POST /sales/{id}/void`
Header: `Idempotency-Key` wajib.
```json
{ "reason": "Salah input, pelanggan batal" }
```
Server: mengubah status menjadi `voided`, menulis `stock_movements` bertipe `void`, `cash_movements` pembalik jika tunai, dan `audit_logs`. Tidak menghapus data.

### 7.5 `GET /sales/{id}/receipt`
```json
{
  "store": { "name": "Toko Plastik Jaya", "address": "...", "phone": "..." },
  "number": "SLS-202610-000123",
  "sold_at": "2026-10-16T05:30:00Z",
  "cashier": "Budi",
  "items": [ { "name": "...", "qty": "10", "unit": "Pak", "price": "4700.00", "total": "47000.00" } ],
  "total": "47000.00",
  "payments": [ { "method": "cash", "amount": "40000.00" } ],
  "change": "0.00",
  "footer": "Terima kasih"
}
```

---

## 8. Supplier & Pembelian [P1]

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/suppliers` | Daftar supplier | `supplier.read` |
| POST | `/suppliers` | Tambah supplier | `supplier.update` |
| PATCH | `/suppliers/{id}` | Ubah supplier | `supplier.update` |
| GET | `/purchases` | Daftar pembelian | `purchase.read` |
| POST | `/purchases` | Buat pembelian (draft/order) | `purchase.update` |
| GET | `/purchases/{id}` | Detail pembelian | `purchase.read` |
| PATCH | `/purchases/{id}` | Ubah pembelian (status `draft`) | `purchase.update` |
| POST | `/purchases/{id}/receive` | Konfirmasi penerimaan (atomik) | `purchase.receive` |
| POST | `/purchases/{id}/cancel` | Batalkan pembelian | `purchase.update` |
| GET | `/purchases/{id}/receipts` | Riwayat penerimaan | `purchase.read` |

### Contoh `POST /purchases/{id}/receive`
Header: `Idempotency-Key` wajib.
```json
{
  "received_at": "2026-10-16T05:00:00Z",
  "items": [
    { "purchase_item_id": "uuid", "received_quantity": "5", "unit_cost": "180000.00" }
  ],
  "notes": "Faktur 123"
}
```
Server memperbarui `stock_balances.avg_cost` (moving weighted average), `stock_movements` bertipe `purchase_receipt`, dan status pembelian (`partially_received`/`received`).

---

## 9. Retur [P1]

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| POST | `/returns` | Buat retur penjualan | `return.create` |
| GET | `/returns` | Daftar retur | `return.read` |
| GET | `/returns/{id}` | Detail retur | `return.read` |
| POST | `/returns/{id}/confirm` | Konfirmasi retur | `return.confirm` [izin khusus] |
| POST | `/returns/{id}/cancel` | Batalkan retur | `return.confirm` |
| GET | `/sales/{id}/returnable-items` | Item yang masih bisa diretur | `return.read` |

### Contoh `POST /returns`
```json
{
  "sale_id": "uuid",
  "reason": "Barang rusak",
  "refund_method": "cash",
  "items": [
    { "sale_item_id": "uuid", "quantity": "2", "condition": "damaged" }
  ]
}
```
Validasi: kuantitas ≤ sisa yang dapat diretur; `condition` menentukan apakah masuk stok layak jual, stok rusak, atau tidak menambah stok.

---

## 10. Pelanggan [P0 struktur]

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/customers` | Daftar pelanggan | `customer.read` |
| POST | `/customers` | Tambah pelanggan | `customer.update` |
| PATCH | `/customers/{id}` | Ubah pelanggan | `customer.update` |

> Tanpa endpoint piutang pada MVP.

---

## 11. Pengeluaran [P1]

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/expense-categories` | Kategori pengeluaran | `expense.read` |
| POST | `/expense-categories` | Tambah kategori | `expense.update` |
| GET | `/expenses` | Daftar pengeluaran | `expense.read` |
| POST | `/expenses` | Catat pengeluaran | `expense.update` |
| POST | `/expenses/{id}/cancel` | Batalkan | `expense.update` |

---

## 12. Laporan & Dashboard

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/reports/dashboard` | Ringkasan hari ini (omzet, transaksi, metode bayar) | `report.dashboard` |
| GET | `/reports/sales` | Laporan penjualan (`from`, `to`, `group_by`) | `report.sales` |
| GET | `/reports/sales/payments` | Rincian metode pembayaran | `report.sales` |
| GET | `/reports/products/top` | Produk terlaris (`by=quantity\|value`) | `report.sales` |
| GET | `/reports/stock` | Laporan stok saat ini | `report.stock` |
| GET | `/reports/stock/low` | Stok menipis | `report.stock` |
| GET | `/reports/gross-profit` | Estimasi laba kotor [izin khusus] | `report.profit` |
| GET | `/reports/cashiers` | Penjualan per kasir/shift | `report.sales` |
| GET | `/reports/purchases` [P1] | Laporan pembelian | `report.purchase` |
| GET | `/reports/expenses` [P1] | Laporan pengeluaran | `report.expense` |
| GET | `/reports/export` | Ekspor laporan CSV/XLSX/PDF (`type`, `params`) | sesuai tipe |

`GET /reports/dashboard` respons:
```json
{
  "date": "2026-10-16",
  "sales_count": 42,
  "gross_revenue": "3200000.00",
  "net_revenue": "3150000.00",
  "discount_total": "50000.00",
  "payment_breakdown": [
    { "method": "cash", "amount": "2000000.00" },
    { "method": "qris", "amount": "1150000.00" }
  ],
  "low_stock_count": 7
}
```

---

## 13. Barcode Label

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| POST | `/labels/preview` | Pratinjau label barcode | `product.read` |
| GET | `/labels/pdf` | Cetak label PDF (`variant_ids`, `qty`) | `product.read` |

### Contoh `POST /labels/preview`
```json
{
  "items": [ { "variant_id": "uuid", "copies": 10 } ],
  "template": "default-40x30"
}
```

---

## 14. Audit Log

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/audit-logs` | Riwayat audit (`actor_id`, `action`, `entity_type`, `from`, `to`, pagination) | `audit.read` |

---

## 15. Kesehatan Sistem

| Method | Endpoint | Tujuan | Izin |
|---|---|---|---|
| GET | `/health` | Status aplikasi | publik |
| GET | `/health/ready` | Kesiapan dependency (DB) | publik |

Respons `/health` tidak mengungkap detail internal atau rahasia.

---

## 16. Daftar Permission (Contoh)

| Grup | Kode |
|---|---|
| Produk | `product.read`, `product.update`, `price.read`, `price.update` |
| Persediaan | `inventory.read`, `inventory.adjust`, `stockcount.create`, `stockcount.read`, `stockcount.count`, `stockcount.confirm` |
| Penjualan | `sale.create`, `sale.read`, `sale.update_price`, `sale.discount`, `sale.void` |
| Shift | `session.open`, `session.read`, `session.close`, `session.cashmove` |
| Pembelian | `purchase.read`, `purchase.update`, `purchase.receive` |
| Retur | `return.create`, `return.read`, `return.confirm` |
| Supplier | `supplier.read`, `supplier.update` |
| Pelanggan | `customer.read`, `customer.update` |
| Pengeluaran | `expense.read`, `expense.update` |
| Laporan | `report.dashboard`, `report.sales`, `report.stock`, `report.profit`, `report.purchase`, `report.expense` |
| Pengguna | `user.read`, `user.create`, `user.update`, `role.read`, `role.update` |
| Pengaturan | `settings.update` |
| Audit | `audit.read` |

---

## 17. Catatan Implementasi

- Backend wajib memeriksa permission; menyembunyikan menu di frontend tidak cukup.
- Seluruh harga, diskon, konversi, total, dan kembalian dihitung server-side.
- Endpoint mutasi stok/penjualan/penerimaan menggunakan transaksi database dan penguncian baris.
- Rate limiting diterapkan pada `/auth/login`, `/auth/forgot-password`, dan endpoint sensitif.
- Jangan membocorkan detail internal pada pesan error; sertakan `request_id` untuk penelusuran.
