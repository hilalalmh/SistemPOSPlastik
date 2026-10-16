# User Flow — Sistem POS Toko Plastik

**Dokumen:** `user-flow.md`
**Status:** Baseline desain MVP
**Sumber:** `production.md` Bagian 4, 5, 9, `erd.md`, `api.md`
**Versi:** 1.0

Dokumen ini menjelaskan alur pengguna utama per peran. Setiap alur memuat aktor, prasyarat, langkah, aturan yang berlaku, dan kondisi gagal.

---

## 1. Peran

| Peran | Tanggung jawab utama |
|---|---|
| Owner | Semua fitur, pengaturan, laporan laba, audit |
| Admin | Operasional harian, master data, pembelian, laporan (sesuai izin) |
| Kasir | Transaksi penjualan, shift, pembayaran, void terbatas |
| Gudang | Penerimaan, stok opname, penyesuaian stok, label barcode |

---

## 2. Alur Autentikasi

### 2.1 Login
1. Pengguna membuka aplikasi.
2. Mengisi `username` dan `password`.
3. Frontend memanggil `POST /auth/login`.
4. Berhasil: token disimpan aman, redirect ke dashboard sesuai role.
5. Gagal: pesan "Username atau password salah"; percobaan gagal dihitung.
6. Terlalu banyak percobaan: akun dikunci sementara; pesan "Akun terkunci sementara, coba lagi nanti".
7. Aktivitas login dicatat di audit log.

### 2.2 Logout
1. Pengguna menekan logout.
2. `POST /auth/logout`, token dihapus.
3. Redirect ke halaman login.

### 2.3 Reset password
1. Pengguna memilih "Lupa password", memasukkan identitas.
2. Sistem mengirim token reset (kanal sesuai konfigurasi).
3. Pengguna menetapkan password baru.
4. Password baru disimpan sebagai hash; sesi lama dicabut.

---

## 3. Alur Kasir

### 3.1 Buka shift
**Prasyarat:** kasir login, belum ada shift `open`.
1. Kasir membuka menu Kasir.
2. Jika belum ada shift, muncul dialog "Buka Kasir".
3. Kasir memasukkan nominal kas awal.
4. `POST /cash-sessions/open`.
5. Shift aktif; antarmuka kasir terbuka. `cash_movements` tipe `opening` tercatat.

**Gagal:** sudah ada shift `open` → tampil shift aktif yang ada.

### 3.2 Transaksi penjualan (alur inti)
**Prasyarat:** shift aktif.

```text
Mulai
  │
  ▼
Cari produk / scan barcode ──► GET /catalog/search atau /catalog/barcode/{barcode}
  │
  ▼
Pilih varian & satuan ──────► GET /variants/{id}/available-units
  │
  ▼
Input kuantitas
  │
  ▼
Sistem hitung harga server-side ──► POST /sales/quotes (opsional, bertahap)
  │
  ▼
Item masuk keranjang ───────► tampil satuan, harga/satuan, subtotal, stok
  │
  ├─ Tambah item lain? ──► ulangi
  │
  ├─ Ubah kuantitas / hapus item ──► perbarui keranjang
  │
  ├─ Diskon (jika diizinkan) ──► validasi batas diskon
  │
  ▼
Checkout ──────────────────► tampil total akhir
  │
  ▼
Pilih metode pembayaran (split payment boleh)
  │
  ▼
Input nominal per metode
  │
  ├─ Tunai: hitung kembalian otomatis
  │
  ▼
Konfirmasi checkout ───────► POST /sales (Idempotency-Key)
  │
  ▼
Server validasi & simpan atomik
  │
  ├─ Gagal (stok kurang) ──► tampil pesan, keranjang tetap
  │
  ▼
Berhasil ──────────────────► tampil nomor transaksi + struk
  │
  ▼
Cetak/lihat struk ────────► GET /sales/{id}/receipt
  │
  ▼
Selesai / transaksi berikutnya
```

**Aturan yang berlaku:**
- Nomor transaksi unik `SLS-YYYYMM-NNNNNN`.
- Harga, diskon, total, kembalian dihitung server; frontend hanya menampilkan.
- Checkout memakai `Idempotency-Key` untuk mencegah transaksi ganda.
- Tombol checkout dinonaktifkan selama request berjalan (cegah klik ganda).
- Jika stok tidak cukup, checkout ditolak dan tidak membuat penjualan final.
- Jika printer/struk gagal, transaksi tetap tersimpan dan struk dapat dibuka ulang.

### 3.3 Pembayaran split
1. Kasir memilih lebih dari satu metode (contoh tunai + QRIS).
2. Mengisi nominal tiap baris.
3. Sistem memastikan `jumlah pembayaran ≥ total`.
4. Kembalian hanya dihitung dari komponen tunai.
5. Semua baris pembayaran tersimpan pada `payments`.

### 3.4 Void penjualan
**Prasyarat:** permission `sale.void`.
1. Kasir membuka riwayat transaksi, memilih transaksi.
2. Menekan "Void" dan memasukkan alasan.
3. Sistem menampilkan konfirmasi (tindakan destruktif).
4. `POST /sales/{id}/void`.
5. Server: status → `voided`, stok dikembalikan lewat `stock_movements` tipe `void`, kas disesuaikan, audit dicatat.
6. Transaksi asli tidak dihapus.

### 3.5 Tutup shift
**Prasyarat:** shift aktif.
1. Kasir menekan "Tutup Kasir".
2. Sistem menghitung kas seharusnya: kas awal + penjualan tunai ± kas masuk/keluar.
3. Kasir memasukkan jumlah kas fisik.
4. Sistem menghitung selisih dan meminta alasan bila ada selisih.
5. `POST /cash-sessions/{id}/close`.
6. Shift → `closed`; laporan shift tersedia.

**Catatan:** shift tertutup tidak dapat diubah tanpa izin khusus dan audit.

---

## 4. Alur Gudang

### 4.1 Stok awal
1. Gudang/admin memilih varian.
2. Memasukkan kuantitas awal (satuan dasar atau satuan konversi).
3. Sistem menulis `stock_movements` tipe `opening` dan memperbarui `stock_balances`.
4. Nominal modal awal (jika ada) mengisi `avg_cost`.

### 4.2 Stok opname
**Prasyarat:** permission `stockcount.create`.
1. Gudang membuat sesi opname → `POST /stock-counts` (snapshot `system_quantity`).
2. Status `counting`.
3. Gudang mengisi hitungan fisik per item → `PATCH /stock-counts/{id}/items`.
4. Sistem menghitung `difference` (fisik − sistem) per item.
5. Gudang menekan "Konfirmasi" → `POST /stock-counts/{id}/confirm` (izin khusus).
6. Server, dalam satu transaksi DB, membuat `stock_adjustments`/`stock_movements` untuk tiap selisih.
7. Stok hanya berubah setelah konfirmasi; audit dicatat.

### 4.3 Penyesuaian stok
**Prasyarat:** permission `inventory.adjust`.
1. Gudang memilih varian, tipe (naik/turun), kuantitas, dan **alasan wajib**.
2. `POST /inventory/adjustments`.
3. Server menulis nomor penyesuaian, `stock_movements`, memperbarui saldo, dan audit.
4. Alasan tersimpan untuk audit.

### 4.4 Penerimaan pembelian [P1]
1. Gudang membuka pembelian berstatus `ordered`.
2. Memilih penerimaan, memasukkan kuantitas diterima per item dan harga beli aktual.
3. `POST /purchases/{id}/receive` dengan `Idempotency-Key`.
4. Server memperbarui `avg_cost` (moving weighted average), menulis `stock_movements` `purchase_receipt`, memperbarui status (`partially_received`/`received`).
5. Stok berubah hanya saat penerimaan dikonfirmasi.

### 4.5 Cetak label barcode
1. Gudang memilih varian dan jumlah salinan.
2. `POST /labels/preview` untuk pratinjau.
3. `GET /labels/pdf` untuk unduh/cetak.
4. Barcode yang terdaftar dapat dipindai di kasir.

---

## 5. Alur Admin / Master Data

### 5.1 Kelola produk & varian
1. Admin membuka menu Produk.
2. Tambah produk (nama, kategori, merek).
3. Tambah varian (SKU unik, barcode opsional, atribut: ukuran/warna/ketebalan/tipe/kemasan, satuan dasar).
4. Menetapkan konversi satuan (mis. 1 pak = 50 lembar, 1 bal = 1000 lembar).
5. Menetapkan harga eceran dan bertingkat per satuan.
6. Simpan → validasi server (SKU unik, rentang harga tidak tumpang tindih).

**Mengubah harga:** memerlukan izin `price.update`; perubahan dicatat di `price_histories` dan audit. Harga transaksi lama tidak berubah (snapshot).

**Menonaktifkan produk:** produk dengan riwayat transaksi tidak dihapus; status menjadi nonaktif dan tidak dapat dijual.

### 5.2 Impor produk CSV
1. Admin mengunggah CSV → `POST /products/import/preview`.
2. Sistem menampilkan pratinjau, error baris per baris, dan ringkasan perubahan.
3. Admin menyetujui → `POST /products/import`.
4. Data diterapkan; kegagalan parsial dilaporkan.

### 5.3 Kelola pengguna & role
1. Admin membuka menu Pengguna.
2. Menambah pengguna (nama, username, role, password awal).
3. Mengatur status aktif/nonaktif.
4. Owner/admin mengatur permission per role bila diperlukan.
5. Semua perubahan dicatat di audit log.

### 5.4 Pengaturan toko
1. Owner/admin membuka Pengaturan.
2. Mengubah identitas toko, kontak, logo, teks struk, timezone, prefix nomor, batas diskon kasir.
3. Simpan; perubahan penting dicatat di audit.

---

## 6. Alur Owner / Laporan

### 6.1 Dashboard
1. Owner membuka dashboard.
2. `GET /reports/dashboard` menampilkan omzet hari ini, jumlah transaksi, rincian metode pembayaran, stok menipis.

### 6.2 Laporan
1. Owner memilih jenis laporan (penjualan, produk terlaris, stok, laba kotor).
2. Mengatur periode/filter.
3. Melihat hasil; mengekspor CSV/XLSX/PDF bila diperlukan.
4. Laporan laba kotor hanya tersedia dengan izin `report.profit`.

**Definisi metrik (dari production.md 4.14):**
- Omzet kotor: total nilai item sebelum retur.
- Penjualan bersih: setelah diskon dan retur.
- Laba kotor: penjualan bersih − HPP (moving weighted average).
- Arus kas ≠ laba.

### 6.3 Audit log
1. Owner membuka menu Audit Log.
2. Filter berdasarkan pelaku, aksi, entitas, dan periode.
3. Menelusuri perubahan penting (harga, void, retur, penyesuaian stok, perubahan pengguna).

---

## 7. Alur Retur [P1]

1. Kasir/admin membuka transaksi, memilih item yang diretur.
2. `GET /sales/{id}/returnable-items` menampilkan sisa yang dapat diretur.
3. Memilih kuantitas, alasan, dan kondisi barang (`resellable`/`damaged`/`writeoff`).
4. `POST /returns`.
5. Persetujuan (izin khusus) → `POST /returns/{id}/confirm`.
6. Server: mencatat pengembalian dana terpisah, menyesuaikan stok sesuai kondisi, dan menulis audit.
7. Laporan membedakan penjualan kotor, retur, dan penjualan bersih.

---

## 8. Alur Pengeluaran [P1]

1. Admin/owner membuka menu Pengeluaran.
2. Mengisi kategori, tanggal, nominal, metode pembayaran, deskripsi.
3. Simpan; tercatat atas nama pengguna.
4. Koreksi/pembatalan memerlukan izin dan tercatat audit.

---

## 9. Alur Penanganan Gangguan

| Situasi | Alur |
|---|---|
| Internet mati | Transaksi online terhenti; gunakan prosedur darurat tertulis; aplikasi tidak menjamin operasi offline pada MVP |
| Listrik mati | Gunakan prosedur darurat; catat transaksi manual untuk entri ulang |
| Printer struk rusak | Transaksi tetap tersimpan; struk dibuka ulang dari riwayat saat printer siap |
| Server/database tidak dapat diakses | Hentikan transaksi; escalation ke admin/IT |
| Pembayaran non-tunai belum terkonfirmasi | Status pembayaran `pending` sampai dikonfirmasi kasir/admin |
| Stok fisik berbeda | Ajukan penyesuaian/opname dengan alasan |

---

## 10. Matriks Ringkas: Peran × Alur

| Alur | Owner | Admin | Kasir | Gudang |
|---|---:|---:|---:|---:|
| Buka/tutup shift | ✓ | ✓ | ✓ (shift sendiri) | – |
| Transaksi penjualan | ✓ | ✓ | ✓ | – |
| Void | ✓ | ✓ (izin) | ✓ (izin) | – |
| Stok opname | ✓ | ✓ | – | ✓ |
| Penyesuaian stok | ✓ | ✓ (izin) | – | ✓ (izin) |
| Master produk/harga | ✓ | ✓ | lihat | lihat |
| Pembelian/penerimaan [P1] | ✓ | ✓ | – | ✓ (izin) |
| Laporan laba | ✓ | ✓ (izin) | – | – |
| Audit log | ✓ | ✓ (izin) | – | – |
| Pengaturan toko | ✓ | terbatas | – | – |
