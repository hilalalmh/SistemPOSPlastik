# Ringkasan Asumsi & Keputusan — Sistem POS Toko Plastik

**Dokumen:** `decisions.md`
**Status:** Disetujui untuk desain MVP
**Sumber:** `production.md` (v1.0), Bagian 2, 19, dan 20
**Versi:** 1.0

Dokumen ini merangkum asumsi dan keputusan produk yang sebelumnya belum final pada `production.md` Bagian 19. Dokumen ini menjadi acuan desain ERD, API, dan user flow. Perubahan pada tabel di bawah mengubah rancangan teknis.

---

## 1. Keputusan yang sudah final untuk desain MVP

| # | Area | Keputusan | Dampak teknis |
|---|---|---|---|
| 1 | Output tahap ini | Dokumen desain (ERD, API contract, user flow, keputusan) | Belum ada scaffolding kode |
| 2 | Kebijakan pembayaran | **Split payment** (Kebijakan B) | Tabel `payments` multi-baris per penjualan; checkout menerima array pembayaran |
| 3 | Metode valuasi HPP | **Moving weighted average** | Kolom `avg_cost` pada `stock_balances`; snapshot `cost_unit`/`cost_total` pada `sale_items`; pembelian memperbarui rata-rata |
| 4 | Offline & perangkat | **Online saja, PC kasir** | Tanpa antrean sinkronisasi; layout dioptimalkan desktop + keyboard |
| 5 | Piutang pelanggan | **Tidak ada untuk MVP** | Tidak ada tabel piutang/pelunasan; `customers` tetap ada sebagai arsip pelanggan |
| 6 | Retur penjualan | **Dirancang (P1), belum diimplementasi MVP** | Tabel `returns`/`return_items` masuk ERD dengan tanda P1; void tetap P0 |
| 7 | Barcode | **Scanner + cetak label** | Kolom `barcode` unik pada varian; generator label; input scanner = input keyboard |
| 8 | Printer struk | **Belum ada printer pada MVP** | Struk ditampilkan di layar + endpoint data struk; integrasi thermal menyusul (P1) |
| 9 | Jumlah lokasi | **Satu lokasi** | Tabel `locations` ada dengan satu baris default; `location_id` tetap dipakai di stok/transaksi untuk kesiapan masa depan |

## 2. Asumsi dasar (dari production.md Bagian 2.1)

- Satu toko plastik, aplikasi web responsif.
- Frontend React + TypeScript + Vite; backend Python + FastAPI; database PostgreSQL.
- REST API, JSON, HTTPS pada deployment.
- Bahasa Indonesia, mata uang Rupiah (IDR), zona waktu `Asia/Jakarta` (dapat dikonfigurasi).
- Pengguna: Owner, Admin, Kasir, Gudang dengan RBAC diperiksa di backend.
- Harga: eceran, grosir, dan bertingkat berdasarkan kuantitas.
- Persediaan: satu lokasi stok.
- Retur: rancangan P1.

## 3. Keputusan teknis yang ditetapkan untuk desain

| Area | Keputusan desain |
|---|---|
| Tipe ID | UUID untuk seluruh primary key transaksional agar aman untuk API dan sinkronisasi masa depan |
| Tipe uang | `NUMERIC(18,2)` untuk uang; `NUMERIC(18,4)` untuk kuantitas/faktor konversi. Tidak memakai floating point |
| Waktu | `TIMESTAMPTZ` (UTC) di database; tampilan dikonversi ke `Asia/Jakarta` |
| Penomoran dokumen | Berformat `{PREFIX}-{YYYYMM}-{URUT}`, contoh `SLS-202610-000123`. Counter unik per periode |
| Soft delete | Data master memakai `is_active`; transaksi final tidak dihapus (void/retur) |
| Idempotensi | Header `Idempotency-Key` pada endpoint checkout dan penerimaan barang |
| Konkurensi stok | `SELECT ... FOR UPDATE` pada `stock_balances` dalam transaksi DB |
| Snapshot harga | Setiap `sale_items` menyimpan nama, SKU, satuan, faktor konversi, harga, diskon, dan HPP saat transaksi |

## 4. Keputusan yang MASIH perlu konfirmasi sebelum go-live

Item berikut belum dipakai menghambat desain tetapi harus diputuskan sebelum produksi:

| # | Keputusan | Pilihan | Default desain saat ini |
|---|---|---|---|
| 1 | Daftar satuan & konversi tiap produk | Diisi pemilik via data master | Struktur `units` + `product_unit_conversions` siap |
| 2 | Kebijakan harga pelanggan khusus | Ada / tidak | Belum di desain detail (P1) |
| 3 | RPO/RTO & retensi backup | Angka pasti | Backup harian, retensi 30 hari (usulan) |
| 4 | Nama dan prefix nomor dokumen toko | String prefix | Usulan `SLS`, `PUR`, `RTR`, `ADJ`, `OPN`, `LBL` |
| 5 | Batas diskon kasir | Persentase/nominal | Usulan 10% (dapat diubah di `store_settings`) |
| 6 | Pengaturan pajak/PPN | Ada / tidak | Belum diaktifkan (kolom `tax_total` disiapkan) |
| 7 | Format & rata teks struk | Template | Template default disiapkan |
| 8 | Integrasi penyedia pembayaran non-tunai | Manual / otomatis | Manual dicatat kasir (status `pending`/`confirmed`) |

## 5. Catatan kepatuhan terhadap production.md

- Aturan bisnis kritis Bagian 5 diterapkan pada ERD dan API.
- Prioritas modul: P0 untuk MVP, P1 dirancang (retur, pembelian, pengeluaran, laporan lanjutan), P2 di luar cakupan.
- Retur/pembelian dicantumkan di ERD dengan penanda **P1** agar desain tidak perlu migrasi besar saat diimplementasikan.
