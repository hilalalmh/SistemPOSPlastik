# Production Specification — Sistem Point of Sale (POS) Toko Plastik

**Dokumen:** `production.md`  
**Status:** Draft spesifikasi produk untuk implementasi  
**Versi:** 1.0  
**Bahasa:** Indonesia  
**Tujuan:** Menjadi acuan kebutuhan produk, aturan bisnis, arsitektur, database, keamanan, pengujian, dan deployment untuk Sistem POS toko plastik.

> **Catatan keputusan:** Dokumen ini menggunakan asumsi awal: satu toko/cabang, aplikasi web responsif, React untuk frontend, FastAPI untuk backend, PostgreSQL untuk database, harga eceran dan grosir, dukungan konversi satuan, serta pembayaran tunai dan non-tunai. Kebutuhan yang belum dipastikan ditandai sebagai keputusan yang perlu dikonfirmasi sebelum implementasi final.

---

## 1. Ringkasan Produk

Sistem POS Toko Plastik adalah aplikasi untuk mengelola transaksi penjualan, produk dan variannya, persediaan, pembelian dari supplier, pembayaran, kasir, serta laporan operasional toko plastik.

Sistem harus menangani karakteristik barang toko plastik, seperti:

- Variasi ukuran, warna, ketebalan, tipe, merek, dan kemasan.
- Barang yang dibeli dalam satuan besar (bal/dus/karton) tetapi dijual dalam satuan lebih kecil (pak/ikat/lembar).
- Harga eceran dan grosir atau harga bertingkat berdasarkan kuantitas.
- Pengendalian stok yang akurat dan dapat ditelusuri.
- Produk rusak, retur, stok opname, serta koreksi stok.
- Laporan penjualan, pembayaran, persediaan, dan estimasi laba kotor.

### 1.1 Tujuan

1. Mempercepat dan mengurangi kesalahan transaksi kasir.
2. Menyediakan data stok yang akurat dan riwayat pergerakan stok.
3. Mengelola pembelian, supplier, dan harga modal.
4. Mendukung harga eceran/grosir serta konversi satuan.
5. Menyediakan laporan yang mudah dipahami pemilik toko.
6. Membatasi akses berdasarkan peran pengguna.
7. Menyediakan fondasi yang dapat dikembangkan untuk barcode, beberapa kasir, dan cabang.

### 1.2 Bukan tujuan MVP

Fitur berikut tidak wajib untuk rilis MVP kecuali disetujui secara khusus:

- Integrasi langsung dengan marketplace.
- Integrasi API bank atau payment gateway.
- Akuntansi penuh dan pelaporan pajak tingkat lanjut.
- Multi-cabang dan transfer stok antarcabang.
- Aplikasi native Android/iOS.
- Program loyalitas, poin, dan promosi kompleks.
- Sinkronisasi offline multi-perangkat.
- Prediksi permintaan berbasis AI.

---

## 2. Ruang Lingkup dan Asumsi

### 2.1 Asumsi awal

| Area | Asumsi awal |
|---|---|
| Tipe usaha | Satu toko plastik |
| Platform | Aplikasi web responsif |
| Frontend | React + TypeScript |
| Backend | Python + FastAPI |
| Database | PostgreSQL |
| Komunikasi | REST API, JSON, HTTPS pada deployment |
| Bahasa | Bahasa Indonesia |
| Mata uang | Rupiah (IDR) |
| Zona waktu | `Asia/Jakarta`, dapat dikonfigurasi |
| Pengguna | Owner, admin, kasir, petugas gudang |
| Pembayaran | Tunai dan non-tunai yang dicatat manual pada MVP |
| Harga | Harga eceran, grosir, dan/atau bertingkat |
| Persediaan | Satu lokasi stok pada MVP |
| Pelanggan | Pelanggan umum; data pelanggan opsional kecuali transaksi piutang digunakan |
| Supplier | Data supplier dan riwayat pembelian |

### 2.2 Keputusan yang perlu dikonfirmasi

Sebelum implementasi produksi, pemilik produk harus memastikan:

- Apakah toko melayani penjualan secara utang/piutang pelanggan.
- Apakah aplikasi wajib beroperasi tanpa internet.
- Apakah kasir hanya menggunakan komputer atau juga HP/tablet.
- Apakah setiap varian produk mempunyai barcode.
- Apakah retur penjualan diperbolehkan dan bagaimana kebijakannya.
- Apakah stok dicatat dalam satuan dasar berupa lembar, buah, gram, meter, atau satuan lain.
- Apakah ada lebih dari satu gudang atau cabang.
- Apakah printer struk, laci kas, dan barcode scanner akan digunakan.
- Apakah transaksi non-tunai hanya dicatat manual atau harus diverifikasi melalui penyedia pembayaran.

---

## 3. Peran dan Hak Akses

Aplikasi harus menerapkan Role-Based Access Control (RBAC). Backend wajib memeriksa hak akses; menyembunyikan tombol di frontend saja tidak cukup.

| Fitur | Owner | Admin | Kasir | Gudang |
|---|---:|---:|---:|---:|
| Dashboard | Semua | Sesuai izin | Ringkasan kasir | Ringkasan stok |
| Kelola pengguna | Ya | Terbatas/opsional | Tidak | Tidak |
| Kelola produk dan varian | Ya | Ya | Lihat/cari | Lihat |
| Ubah harga jual | Ya | Dengan izin | Tidak, kecuali izin khusus | Tidak |
| Penjualan | Ya | Ya | Ya | Tidak |
| Diskon manual | Ya | Dengan izin | Batas yang ditetapkan | Tidak |
| Pembelian dan penerimaan | Ya | Ya | Tidak | Dengan izin |
| Penyesuaian stok | Ya | Dengan izin | Tidak | Dengan izin |
| Stok opname | Ya | Ya | Tidak | Ya |
| Retur | Ya | Dengan izin | Ajukan/proses sesuai izin | Sesuai izin |
| Laporan laba | Ya | Dengan izin | Tidak | Tidak |
| Laporan penjualan | Ya | Ya | Transaksi sendiri/shift | Tidak |
| Penutupan kasir | Ya | Ya | Shift sendiri | Tidak |
| Audit log | Ya | Dengan izin | Tidak | Tidak |
| Pengaturan toko | Ya | Terbatas | Tidak | Tidak |

Seluruh akses sensitif harus dapat dikonfigurasi melalui permission jika diperlukan. Tindakan yang memerlukan izin tambahan antara lain perubahan harga, diskon di atas batas, pembatalan transaksi, retur, penyesuaian stok, dan pembukaan kembali shift.

---

## 4. Modul dan Kebutuhan Fungsional

Prioritas:
- **P0:** Wajib untuk MVP.
- **P1:** Tahap operasional berikutnya.
- **P2:** Pengembangan lanjutan.

### 4.1 Autentikasi dan pengguna — P0

- Login dan logout.
- Password disimpan menggunakan algoritma hash yang sesuai, bukan teks biasa.
- Pengelolaan pengguna dan status aktif/nonaktif.
- Penerapan role dan permission pada backend.
- Pembatasan percobaan login dan penanganan sesi.
- Reset password dengan alur yang aman.
- Audit untuk aktivitas penting.

### 4.2 Data toko dan pengaturan — P0

- Nama, alamat, kontak, logo, dan informasi struk toko.
- Zona waktu dan format mata uang.
- Awalan nomor transaksi yang dapat dikonfigurasi.
- Pengaturan batas diskon dan izin tindakan sensitif.
- Pengaturan printer/format struk jika didukung perangkat.

### 4.3 Kategori dan produk — P0

Setiap produk atau varian setidaknya memiliki:

- ID internal.
- SKU/kode produk unik.
- Nama produk.
- Kategori.
- Merek (opsional).
- Deskripsi (opsional).
- Varian seperti ukuran, warna, ketebalan, tipe, dan kemasan.
- Satuan dasar stok.
- Status aktif/nonaktif.
- Barcode (opsional).
- Harga modal atau metode perhitungan biaya.
- Harga jual dan aturan harga.
- Batas stok minimum (opsional).
- Catatan produk (opsional).

SKU harus unik. Varian yang secara operasional memiliki stok atau harga berbeda harus dapat diidentifikasi sebagai item tersendiri. Produk yang sudah memiliki riwayat transaksi tidak boleh dihapus permanen; gunakan status nonaktif.

Fitur produk:
- Tambah, lihat, ubah, nonaktifkan.
- Cari berdasarkan nama, SKU, barcode, kategori, dan atribut varian.
- Filter dan pagination.
- Impor/ekspor CSV dengan validasi dan pratinjau sebelum perubahan diterapkan.
- Riwayat perubahan harga.

### 4.4 Satuan dan konversi — P0

Sistem harus mendukung satuan yang berbeda untuk pembelian dan penjualan.

Contoh konfigurasi:
- 1 bal = 20 pak.
- 1 pak = 50 lembar.
- Maka 1 bal = 1.000 lembar.

Aturan:
1. Setiap item stok mempunyai satu satuan dasar yang konsisten.
2. Kuantitas transaksi dikonversi ke satuan dasar sebelum stok diperbarui.
3. Faktor konversi harus positif dan tidak boleh nol.
4. Perubahan faktor konversi tidak boleh mengubah transaksi historis.
5. Setiap baris transaksi menyimpan satuan dan faktor konversi yang digunakan pada saat transaksi.
6. Kuantitas pecahan hanya diperbolehkan untuk produk/satuan yang mengizinkannya.
7. Sistem harus menampilkan satuan yang dipilih dan ekuivalen satuan dasar dengan jelas.
8. Konversi antarunit hanya diizinkan jika hubungan konversinya terdefinisi.

**Contoh:** stok awal 2 bal, dengan 1 bal = 1.000 lembar, berarti stok dasar 2.000 lembar. Penjualan 3 pak, dengan 1 pak = 50 lembar, mengurangi stok sebanyak 150 lembar. Stok akhir adalah 1.850 lembar atau ekuivalen 1 bal + 17 pak + 0 lembar, sesuai aturan tampilan yang dipilih.

### 4.5 Harga jual dan grosir — P0

Sistem harus mendukung satu atau lebih skema harga per varian:

- Harga eceran.
- Harga grosir berdasarkan kuantitas minimum.
- Rentang kuantitas bertingkat.
- Periode berlaku harga jika diperlukan.
- Diskon per baris atau transaksi berdasarkan izin.
- Harga khusus pelanggan pada tahap P1.

Contoh aturan:
- 1–9 pak: Rp5.000 per pak.
- 10–49 pak: Rp4.700 per pak.
- 50 pak ke atas: Rp4.400 per pak.

Aturan:
- Harga harus dihitung oleh backend dan divalidasi ulang saat checkout.
- Rentang kuantitas tidak boleh tumpang tindih atau memiliki celah yang tidak disengaja.
- Perhitungan harga grosir harus konsisten dan dapat dijelaskan kepada kasir.
- Sistem menyimpan harga aktual per item pada saat transaksi agar histori tidak berubah ketika harga master diubah.
- Harga nol atau negatif ditolak kecuali fitur khusus secara eksplisit mendukungnya.
- Diskon di atas batas memerlukan izin.
- Pembulatan mengikuti aturan Rupiah yang ditetapkan aplikasi dan harus konsisten.

### 4.6 Kasir dan penjualan — P0

Alur dasar:
1. Kasir membuka shift.
2. Kasir mencari produk atau memindai barcode.
3. Kasir memilih satuan dan kuantitas.
4. Sistem menampilkan harga yang sesuai dan subtotal.
5. Kasir dapat mengubah kuantitas atau menghapus item sebelum checkout.
6. Sistem menghitung diskon, pajak jika kelak diterapkan, dan total.
7. Kasir memilih metode pembayaran.
8. Backend memvalidasi harga, izin, status produk, dan ketersediaan stok.
9. Backend menyimpan transaksi, item, pembayaran, dan pergerakan stok dalam satu transaksi database.
10. Sistem menampilkan nomor transaksi dan menyediakan struk.

Persyaratan:
- Satu transaksi dapat berisi banyak item.
- Mendukung pencarian cepat.
- Mendukung input kuantitas.
- Mendukung pembayaran tunai dan metode non-tunai yang dicatat manual.
- Menghitung uang diterima dan kembalian untuk pembayaran tunai.
- Menolak checkout jika stok tidak mencukupi, kecuali kebijakan backorder disetujui dan diimplementasikan.
- Mencegah transaksi ganda akibat klik berulang atau retry jaringan melalui idempotency key.
- Transaksi yang sudah selesai tidak boleh diedit langsung; gunakan void/retur dengan izin dan jejak audit.
- Jika printer gagal, transaksi tetap tersimpan dan struk dapat dicetak ulang.
- Nomor transaksi unik dan tidak boleh digunakan ulang.
- Menangani konflik stok jika dua kasir membeli item terakhir secara bersamaan.

### 4.7 Pembayaran — P0

Metode pembayaran pada MVP:
- Tunai.
- Transfer bank.
- QRIS.
- E-wallet.
- Metode lain yang dikonfigurasi.

Untuk pembayaran non-tunai yang belum terintegrasi, status hanya berarti dicatat oleh kasir, bukan otomatis terverifikasi oleh bank atau penyedia pembayaran. Jika diperlukan, tambahkan status seperti `pending`, `confirmed`, `failed`, dan `refunded`.

Untuk MVP, pilih salah satu kebijakan berikut sebelum coding:
- **Kebijakan A:** satu metode pembayaran per transaksi.
- **Kebijakan B:** pembayaran campuran, misalnya sebagian tunai dan sebagian QRIS.

Struktur database sebaiknya memungkinkan beberapa baris pembayaran agar kebijakan B dapat didukung tanpa migrasi besar.

### 4.8 Manajemen shift dan kas — P0/P1

- Buka shift dengan nominal kas awal.
- Catat kas masuk/keluar selain transaksi penjualan.
- Tutup shift dengan jumlah kas fisik.
- Hitung kas yang seharusnya ada berdasarkan transaksi dan pergerakan kas.
- Catat selisih dan alasan.
- Laporan penjualan per kasir dan shift.
- Shift yang sudah ditutup tidak dapat diubah tanpa izin khusus dan audit log.

### 4.9 Pembelian dan supplier — P1

- CRUD supplier.
- Pembuatan pesanan/pencatatan pembelian.
- Penerimaan barang aktual.
- Pencatatan harga beli, diskon pembelian, dan biaya tambahan.
- Update stok hanya pada saat penerimaan barang dikonfirmasi.
- Riwayat pembelian per supplier dan produk.
- Retur pembelian.
- Status pembelian: draft, ordered, partially received, received, cancelled.
- Lampiran nomor faktur dan catatan (opsional).

### 4.10 Persediaan dan pergerakan stok — P0

Jenis pergerakan stok minimal:
- Stok awal.
- Barang masuk dari penerimaan pembelian.
- Barang keluar dari penjualan.
- Retur penjualan yang layak masuk stok.
- Retur ke supplier.
- Penyesuaian positif/negatif.
- Barang rusak atau hilang.
- Pembatalan/void yang sah.

Persyaratan:
- Pergerakan stok bersifat append-only; koreksi dilakukan dengan transaksi pembalik atau penyesuaian baru, bukan menghapus sejarah.
- Setiap pergerakan mencatat item, jumlah satuan dasar, waktu, sumber transaksi, pengguna, dan alasan jika relevan.
- Saldo stok tidak boleh berubah tanpa sumber pergerakan yang tercatat.
- Sistem memiliki stok minimum dan laporan stok menipis.
- Produk yang tidak aktif tidak dapat dijual, tetapi riwayatnya tetap tersedia.
- Penyesuaian stok memerlukan alasan dan izin.
- Stok opname menyimpan stok sistem, hitungan fisik, selisih, pelaku, waktu, dan persetujuan bila diperlukan.
- Operasi penjualan/penerimaan harus memperbarui saldo stok dan catatan pergerakan secara atomik.

### 4.11 Retur dan pembatalan — P1

- Retur selalu merujuk pada transaksi asli jika transaksi asli tersedia.
- Jumlah retur tidak boleh melebihi jumlah yang dapat diretur dari transaksi asli.
- Kasir harus memilih alasan retur.
- Kondisi barang menentukan apakah barang kembali ke stok layak jual, masuk stok rusak, atau tidak menambah stok.
- Pengembalian dana dicatat terpisah dari penjualan awal.
- Void transaksi memerlukan izin dan alasan.
- Semua retur/void dicatat dalam audit log.
- Laporan penjualan harus membedakan penjualan kotor, retur, dan penjualan bersih.

### 4.12 Pelanggan dan piutang — P1, jika penjualan utang diperlukan

- Data pelanggan minimal: nama dan kontak opsional.
- Catatan transaksi pelanggan.
- Limit kredit opsional.
- Pencatatan pembayaran sebagian/pelunasan.
- Saldo piutang dan umur piutang.
- Riwayat perubahan saldo.
- Penjualan kredit hanya untuk pengguna yang diberi izin.
- Pembayaran piutang harus tercatat sebagai transaksi tersendiri dan tidak boleh mengubah transaksi penjualan asli.

### 4.13 Pengeluaran — P1

- Kategori pengeluaran.
- Nominal, tanggal, metode pembayaran, deskripsi, dan pencatat.
- Lampiran bukti (opsional).
- Laporan pengeluaran per periode dan kategori.
- Koreksi/pembatalan dengan izin dan jejak audit.

### 4.14 Laporan dan dashboard — P0/P1

MVP:
- Ringkasan transaksi hari ini.
- Omzet dan jumlah transaksi.
- Rincian metode pembayaran.
- Daftar transaksi dan detail struk.
- Produk terlaris berdasarkan kuantitas dan nilai.
- Stok saat ini dan stok menipis.

Tahap berikutnya:
- Penjualan harian/mingguan/bulanan.
- Penjualan bersih setelah retur.
- Estimasi laba kotor.
- Laporan pembelian.
- Nilai persediaan.
- Pengeluaran.
- Piutang dan utang supplier jika digunakan.
- Laporan per kasir, shift, kategori, produk, dan periode.
- Ekspor CSV/XLSX/PDF.

**Definisi metrik harus jelas:**
- Omzet kotor: total nilai item sebelum retur, sesuai kebijakan diskon.
- Penjualan bersih: penjualan setelah diskon dan retur yang diakui.
- Laba kotor: penjualan bersih dikurangi harga pokok barang terjual (HPP/COGS).
- Arus kas bukan hal yang sama dengan laba.
- Nilai stok dihitung berdasarkan metode valuasi yang dipilih.

Metode valuasi stok/HPP—misalnya moving weighted average atau FIFO—harus ditentukan sebelum laporan laba dianggap resmi. Untuk MVP, metode yang dipilih harus konsisten dan didokumentasikan.

### 4.15 Audit log — P0

Catat setidaknya:
- Login gagal/berhasil bila sesuai kebijakan keamanan.
- Perubahan pengguna/role.
- Perubahan produk, satuan, konversi, dan harga.
- Diskon khusus.
- Void, retur, dan refund.
- Penyesuaian stok dan stok opname.
- Pembukaan kembali shift.
- Perubahan konfigurasi penting.

Audit log berisi pelaku, aksi, entitas, ID entitas, waktu, dan metadata yang relevan. Jangan menyimpan password, token, atau data rahasia di log.

---

## 5. Aturan Bisnis Kritis

1. **Harga historis tidak berubah.** Transaksi menyimpan nama/SKU, satuan, faktor konversi, harga satuan, diskon, dan biaya pada waktu transaksi.
2. **Stok mempunyai satuan dasar.** Semua mutasi dikonversi ke satuan dasar produk.
3. **Stok dan transaksi atomik.** Penjualan tidak boleh tersimpan tanpa mutasi stok yang sesuai, atau sebaliknya.
4. **Tidak ada penghapusan transaksi final.** Gunakan void/retur dengan otorisasi dan audit.
5. **Harga checkout dihitung server-side.** Frontend tidak dipercaya sebagai sumber nilai final.
6. **Pencegahan stok negatif.** Ditolak secara default; pengecualian memerlukan keputusan eksplisit.
7. **Idempotensi checkout.** Request yang dikirim ulang tidak boleh membuat transaksi kedua.
8. **Pembulatan terstandar.** Semua nilai uang menggunakan tipe numerik fixed precision/integer Rupiah, bukan floating point biner.
9. **Waktu tersimpan dengan benar.** Timestamp disimpan dengan zona waktu yang sesuai; tampilan mengikuti `Asia/Jakarta`.
10. **Perubahan konversi tidak mengubah histori.** Snapshot konversi disimpan di transaksi.
11. **Produk historis dinonaktifkan, bukan dihapus.**
12. **Pembayaran dan penjualan dipisahkan.** Mendukung rekonsiliasi dan pembayaran campuran jika diperlukan.
13. **Hak akses diperiksa di backend.**
14. **Retur tidak otomatis membuat stok layak jual.** Kondisi barang harus dinilai.
15. **Nomor dokumen unik.** Penjualan, pembelian, retur, dan pergerakan stok memiliki identifier unik.

---

## 6. Rancangan Arsitektur

### 6.1 Teknologi yang direkomendasikan

| Lapisan | Teknologi | Catatan |
|---|---|---|
| Frontend | React + TypeScript + Vite | UI web responsif |
| UI | Tailwind CSS atau design system sejenis | Pilih satu pendekatan konsisten |
| Backend | Python + FastAPI | REST API, validasi Pydantic |
| ORM/migrasi | SQLAlchemy 2.x + Alembic | Skema database terkelola |
| Database | PostgreSQL | Transaksi ACID dan konsistensi stok |
| Auth | Session aman atau access/refresh token | Pilih berdasarkan deployment; jangan simpan token sensitif sembarangan |
| Testing | Pytest, HTTPX, Vitest/React Testing Library | Backend dan frontend |
| Deployment | Docker Compose untuk deployment sederhana | Reverse proxy HTTPS |
| Observability | Logging terstruktur dan health checks | Hindari data sensitif pada log |
| Backup | PostgreSQL backup terjadwal | Uji pemulihan secara berkala |

Versi library harus dipatok dan diperbarui melalui proses review. Jangan memakai dependensi yang tidak dipelihara atau mengandalkan versi floating di produksi.

### 6.2 Gambaran komponen

```text
Browser Kasir / Browser Admin
            |
       HTTPS / REST
            |
       React Frontend
            |
       FastAPI Backend
       /      |       \
 Auth/RBAC  Domain     Reporting
            Services
       /       |       \
 PostgreSQL  File Storage (opsional)  Logs/Monitoring
```

### 6.3 Prinsip backend

- Pisahkan router/API, schema, model, service/domain logic, dan repository jika digunakan.
- Jangan menaruh aturan harga atau stok hanya di frontend.
- Gunakan transaction database untuk checkout, penerimaan barang, retur, dan penyesuaian stok.
- Validasi input dengan schema.
- Gunakan pagination/filter pada daftar besar.
- Kembalikan pesan error yang konsisten tanpa membocorkan detail internal.
- Sediakan endpoint health check tanpa mengungkap informasi rahasia.
- Gunakan migration untuk semua perubahan skema.
- Gunakan background job hanya jika diperlukan, misalnya laporan berat atau backup terkoordinasi.

### 6.4 Prinsip frontend

- Antarmuka kasir memprioritaskan kecepatan dan penggunaan keyboard.
- Layout responsif untuk desktop, tablet, dan HP.
- Loading, empty state, error state, dan konfirmasi tindakan tersedia.
- Cegah klik ganda checkout.
- Tampilkan satuan, jumlah, harga per satuan, diskon, dan total secara jelas.
- Tangani kegagalan cetak tanpa menghilangkan transaksi yang telah berhasil.
- Jangan menyimpan data sensitif secara tidak aman pada browser.
- Aksi sensitif memerlukan konfirmasi yang sesuai.

---

## 7. Rancangan Database Awal

Rancangan berikut merupakan baseline. Nama kolom dan normalisasi final harus dipastikan ketika ERD dan migration dibuat.

### 7.1 Tabel inti

| Tabel | Kolom penting/tujuan |
|---|---|
| `users` | `id`, `name`, `username/email`, `password_hash`, `role_id`, `is_active`, timestamps |
| `roles` | `id`, `name` |
| `permissions` | `id`, `code`, `description` |
| `role_permissions` | `role_id`, `permission_id` |
| `store_settings` | identitas toko, timezone, konfigurasi struk |
| `categories` | `id`, `name`, `parent_id` opsional, `is_active` |
| `products` | `id`, `name`, `category_id`, `brand`, `description`, `is_active` |
| `product_variants` | `id`, `product_id`, `sku`, `barcode`, atribut varian, `base_unit_id`, `min_stock`, `is_active` |
| `units` | `id`, `name`, `symbol`, `allows_fraction` |
| `product_unit_conversions` | `variant_id`, `unit_id`, `base_units_per_unit`, `is_active` |
| `product_prices` | `variant_id`, `unit_id`, `min_qty`, `max_qty` nullable, `unit_price`, `valid_from`, `valid_to` |
| `suppliers` | nama, kontak, alamat, status |
| `customers` | nama, kontak, alamat opsional, status |
| `sales` | nomor, waktu, kasir, shift, status, subtotal, diskon, total, catatan |
| `sale_items` | penjualan, varian, snapshot nama/SKU, kuantitas input, satuan, faktor konversi, harga, diskon, total, HPP snapshot |
| `payments` | sale/payment reference, metode, nominal, status, waktu, reference eksternal opsional |
| `cash_sessions` | kasir, waktu buka/tutup, kas awal, kas hitungan, expected cash, selisih, status |
| `cash_movements` | shift, jenis, nominal, alasan, pengguna, waktu |
| `stock_balances` | varian, lokasi, kuantitas satuan dasar; unique per varian/lokasi |
| `stock_movements` | varian, lokasi, jenis, kuantitas bertanda, sumber, referensi, pengguna, waktu, alasan |
| `purchases` | nomor, supplier, status, tanggal, total, pembuat |
| `purchase_items` | pembelian, varian, kuantitas, unit, konversi, biaya satuan, diskon, total |
| `stock_counts` | nomor, lokasi, status, pembuat, waktu |
| `stock_count_items` | varian, stok sistem snapshot, hitungan fisik, selisih, satuan |
| `returns` | nomor, transaksi asal, jenis, alasan, status, pengguna |
| `return_items` | item penjualan asal, kuantitas retur, kondisi barang, nilai pengembalian |
| `expenses` | kategori, tanggal, nominal, metode pembayaran, deskripsi, pembuat |
| `audit_logs` | actor, action, entity type/id, metadata, timestamp |
| `idempotency_keys` | key unik, pengguna/konteks, hasil request, expiry jika diterapkan |

### 7.2 Constraint dan indeks

- Unique: `users.username/email` sesuai kebijakan, `product_variants.sku`, barcode jika ada, nomor dokumen.
- Foreign key untuk relasi inti.
- Check constraint untuk nominal dan faktor konversi positif.
- Index pada waktu transaksi, SKU, barcode, kategori, status, supplier, dan foreign key yang sering difilter.
- `stock_balances` memiliki unique constraint pada kombinasi varian dan lokasi.
- `product_prices` divalidasi agar rentang kuantitas dan periode harga tidak bertabrakan.
- Gunakan `NUMERIC` fixed precision atau integer untuk nilai uang dan kuantitas sesuai kebutuhan; jangan gunakan `FLOAT` untuk uang.
- Soft-delete/nonaktif untuk data master yang sudah direferensikan.
- Semua timestamp transaksi mencatat waktu yang konsisten.

### 7.3 Prinsip persediaan

`stock_balances` adalah saldo saat ini untuk performa. `stock_movements` adalah buku besar pergerakan yang dapat diaudit. Keduanya harus diperbarui dalam transaksi database yang sama.

Jangan mengubah saldo stok langsung dari endpoint umum tanpa membuat movement terkait. Sediakan service/domain khusus untuk penerimaan, penjualan, retur, dan penyesuaian.

### 7.4 Harga pokok dan nilai persediaan

Metode valuasi HPP belum ditentukan. Pilih dan dokumentasikan salah satu, misalnya:
- Moving weighted average.
- FIFO.

Pilihan metode memengaruhi laporan laba kotor, retur, dan nilai persediaan. Jangan menyebut laporan laba sebagai angka final sebelum metode HPP diterapkan dan diuji.

---

## 8. Rancangan REST API

Prefix API: `/api/v1`

Contoh endpoint baseline:

| Method | Endpoint | Tujuan |
|---|---|---|
| POST | `/auth/login` | Login |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Pengguna aktif |
| GET/POST | `/products` | Daftar/tambah produk |
| GET/PATCH | `/products/{id}` | Detail/ubah produk |
| GET/POST | `/variants` | Daftar/tambah varian |
| GET/POST | `/variants/{id}/prices` | Aturan harga varian |
| GET/POST | `/categories` | Daftar/tambah kategori |
| GET | `/inventory/stock` | Saldo stok |
| GET | `/inventory/movements` | Riwayat pergerakan stok |
| POST | `/inventory/adjustments` | Penyesuaian stok |
| POST | `/sales/quotes` | Menghitung keranjang/harga sebelum checkout |
| POST | `/sales` | Checkout/menyelesaikan penjualan |
| GET | `/sales` | Daftar penjualan |
| GET | `/sales/{id}` | Detail penjualan |
| POST | `/sales/{id}/void` | Void dengan izin |
| GET/POST | `/suppliers` | Data supplier |
| GET/POST | `/purchases` | Daftar/buat pembelian |
| POST | `/purchases/{id}/receive` | Konfirmasi penerimaan |
| POST | `/cash-sessions/open` | Buka shift |
| POST | `/cash-sessions/{id}/close` | Tutup shift |
| GET | `/reports/sales` | Laporan penjualan |
| GET | `/reports/stock` | Laporan stok |
| GET | `/audit-logs` | Audit log dengan izin |

API final harus mendefinisikan request/response schema, status code, validasi, pagination, filter, error code, permission, dan aturan idempotensi. Endpoint di atas adalah rancangan awal, bukan kontrak API final.

### 8.1 Contoh request checkout

Contoh konseptual:

```json
{
  "idempotency_key": "unique-client-generated-key",
  "cash_session_id": "session-id",
  "items": [
    {
      "variant_id": "variant-id",
      "unit_id": "unit-id",
      "quantity": "10"
    }
  ],
  "payments": [
    {
      "method": "cash",
      "amount": "50000"
    }
  ]
}
```

Backend wajib menghitung ulang harga, diskon, konversi, stok, dan total. Jangan mempercayai `unit_price`, `discount`, `total`, atau `change` yang dikirim frontend sebagai nilai otoritatif.

---

## 9. Kebutuhan UI/UX

### 9.1 Menu utama

1. Dashboard.
2. Kasir/Penjualan.
3. Riwayat transaksi.
4. Produk dan varian.
5. Kategori dan satuan.
6. Persediaan.
7. Pembelian.
8. Supplier.
9. Pelanggan (jika diperlukan).
10. Pengeluaran.
11. Laporan.
12. Pengguna dan hak akses.
13. Pengaturan toko.
14. Audit log.

Menu harus disesuaikan dengan role pengguna.

### 9.2 Halaman kasir

Wajib menampilkan:
- Pencarian produk/barcode.
- Daftar item keranjang.
- Varian dan satuan.
- Kuantitas.
- Harga per satuan.
- Diskon yang diizinkan.
- Subtotal dan total.
- Metode pembayaran.
- Nominal dibayar dan kembalian.
- Tombol checkout yang jelas.
- Status stok dan pesan validasi.
- Nomor transaksi setelah berhasil.

### 9.3 Prinsip usability

- Navigasi ringkas.
- Pencarian produk responsif.
- Dukungan keyboard dan scanner barcode yang berperilaku seperti input keyboard.
- Konfirmasi untuk tindakan destruktif.
- Pesan kesalahan dalam bahasa Indonesia yang menjelaskan langkah perbaikan.
- Format nominal konsisten, contoh `Rp50.000`.
- Tidak mengandalkan warna saja untuk menyampaikan status.
- Mendukung tampilan desktop dan ukuran layar lebih kecil.

---

## 10. Keamanan dan Privasi

- Wajib HTTPS pada akses jaringan publik.
- Hash password menggunakan algoritma modern yang sesuai.
- Validasi input dan query parameter.
- ORM/parameterized query untuk mencegah SQL injection.
- Proteksi XSS, CSRF sesuai mekanisme autentikasi, dan pembatasan CORS.
- Rate limiting pada login dan endpoint sensitif.
- Cookie sesi jika digunakan harus `HttpOnly`, `Secure`, dan `SameSite` yang tepat.
- Secret dan kredensial hanya melalui environment/secret manager, tidak disimpan di Git.
- Prinsip least privilege untuk akun database dan pengguna aplikasi.
- Audit tindakan penting.
- Jangan memasukkan password, token, atau data sensitif ke log.
- Backup dienkripsi dan aksesnya dibatasi.
- Sediakan prosedur pembuatan, rotasi, dan pencabutan kredensial.
- Dependency scan dan pembaruan keamanan secara berkala.
- Data pelanggan dikumpulkan seperlunya dan hanya dapat diakses oleh pengguna berwenang.

---

## 11. Non-Functional Requirements

Target awal yang harus diverifikasi lewat pengujian, bukan diasumsikan otomatis tercapai:

| Area | Target awal |
|---|---|
| Respons pencarian produk | P95 ≤ 500 ms pada beban yang disepakati |
| Respons API umum | P95 ≤ 800 ms, tidak termasuk proses eksternal |
| Checkout | P95 ≤ 1,5 detik pada beban yang disepakati |
| Ketersediaan | Target awal 99,5% per bulan untuk deployment online |
| Integritas transaksi | Tidak ada transaksi penjualan parsial yang menyebabkan stok tidak konsisten |
| Backup | Backup harian minimum; interval disesuaikan toleransi kehilangan data |
| Pemulihan | Prosedur restore diuji sebelum go-live |
| Skalabilitas | Pagination dan indeks untuk data yang terus bertambah |
| Auditabilitas | Perubahan stok, harga, void, dan retur dapat ditelusuri |
| Usability | Alur checkout dapat diselesaikan tanpa navigasi berlebihan |
| Aksesibilitas | Label form, fokus keyboard, dan kontras yang memadai |

RPO (toleransi kehilangan data) dan RTO (target waktu pemulihan) harus disetujui pemilik sebelum produksi. Target ketersediaan tidak menjamin hasil tanpa infrastruktur dan monitoring yang sesuai.

---

## 12. Pengujian dan Kriteria Penerimaan

### 12.1 Pengujian wajib

- Unit test untuk harga bertingkat dan konversi satuan.
- Integration test untuk checkout, pembelian, retur, dan stok opname.
- Test role/permission.
- Test validasi input dan error handling.
- Test konkurensi untuk dua checkout atas stok terakhir.
- Test idempotensi ketika request checkout diulang.
- Test transaksi rollback jika salah satu langkah gagal.
- Test laporan terhadap data transaksi yang diketahui.
- Test backup dan restore.
- Test printer struk pada perangkat target jika digunakan.
- Test usability dengan alur kerja kasir sebenarnya.

### 12.2 Skenario penerimaan inti

1. **Konversi satuan:** stok 2 bal × 1.000 lembar/bal = 2.000 lembar. Penjualan 3 pak × 50 lembar/pak menyisakan 1.850 lembar.
2. **Harga grosir:** penjualan 10 pak menggunakan harga untuk rentang 10–49 pak, sesuai konfigurasi.
3. **Stok tidak cukup:** checkout ditolak dan tidak membuat penjualan final.
4. **Request ganda:** request checkout dengan idempotency key sama menghasilkan satu transaksi saja.
5. **Kegagalan database:** jika update stok gagal, penjualan tidak menjadi final.
6. **Harga historis:** perubahan harga master tidak mengubah detail transaksi lama.
7. **Hak akses:** kasir tanpa permission tidak dapat mengubah harga master atau menyesuaikan stok melalui API.
8. **Void/retur:** tindakan mencatat alasan, pengguna, dan mutasi stok/pembayaran yang benar.
9. **Pembayaran tunai:** kembalian sesuai nominal dibayar dikurangi total.
10. **Pembayaran non-tunai:** status transaksi sesuai kebijakan konfirmasi yang dipilih.
11. **Stok opname:** selisih tidak mengubah stok sampai penyesuaian disetujui/dikonfirmasi.
12. **Restore:** backup dapat dipulihkan ke lingkungan uji dan data utama dapat diverifikasi.

### 12.3 Definition of Done

Fitur dianggap selesai jika:
- Kebutuhan dan aturan bisnis terdokumentasi.
- Validasi dilakukan di backend.
- Permission diperiksa di backend.
- Migration tersedia.
- Unit/integration test relevan lulus.
- Error/loading/empty state tersedia di UI.
- Audit log tersedia untuk tindakan sensitif.
- Dokumentasi API diperbarui.
- Tidak ada secret dalam source control.
- Code review dilakukan.
- Pengujian regresi inti lulus.

---

## 13. Deployment dan Operasional

### 13.1 Lingkungan

Pisahkan:
- Development lokal.
- Staging untuk uji penerimaan.
- Production untuk penggunaan toko.

Jangan memakai data produksi nyata dalam development tanpa proses anonimisasi dan izin yang sesuai.

### 13.2 Konfigurasi environment

Contoh nama variabel, bukan nilai rahasia:

```env
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/pos_db
SECRET_KEY=SET_VIA_SECRET_MANAGER
CORS_ORIGINS=https://pos.example.com
TIMEZONE=Asia/Jakarta
```

Jangan commit file `.env` produksi. Sertakan `.env.example` tanpa rahasia.

### 13.3 Deployment minimum

- Reverse proxy dengan HTTPS.
- Backend FastAPI dijalankan oleh process manager/container.
- PostgreSQL tidak diekspos langsung ke internet.
- Firewall hanya membuka port yang diperlukan.
- Migrasi database dilakukan terencana sebelum aplikasi baru menerima trafik.
- Health check dan log aplikasi aktif.
- Backup otomatis serta notifikasi jika gagal.
- Penyimpanan backup terpisah dari server utama.
- Uji pemulihan backup secara berkala.
- Prosedur rollback versi aplikasi dan database terdokumentasi.
- Waktu server tersinkronisasi.

### 13.4 Backup

Minimum:
- Backup database harian.
- Retensi backup yang ditentukan.
- Enkripsi saat disimpan/ditransfer.
- Akses backup dibatasi.
- Uji restore berkala.
- Backup sebelum migrasi berisiko tinggi.

Frekuensi backup harus ditingkatkan jika kehilangan transaksi selama satu hari tidak dapat diterima.

### 13.5 Operasional toko saat gangguan

Tentukan prosedur tertulis untuk:
- Internet mati.
- Listrik mati.
- Printer struk rusak.
- Server/database tidak dapat diakses.
- Pembayaran non-tunai belum terkonfirmasi.
- Stok fisik berbeda dengan sistem.

Jika operasi offline diwajibkan, desain offline-first dan sinkronisasi harus dirancang sebagai kebutuhan khusus; jangan menganggap aplikasi web online otomatis mendukung transaksi offline yang aman.

---

## 14. Struktur Repository yang Disarankan

```text
plastic-store-pos/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── dashboard/
│   │   │   ├── products/
│   │   │   ├── inventory/
│   │   │   ├── sales/
│   │   │   ├── purchases/
│   │   │   ├── suppliers/
│   │   │   ├── reports/
│   │   │   └── settings/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── permissions/
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── infra/
│   ├── docker/
│   └── reverse-proxy/
├── docs/
│   ├── erd.md
│   ├── api.md
│   ├── deployment.md
│   └── operations.md
├── .env.example
├── .gitignore
├── docker-compose.yml
└── production.md
```

Struktur dapat disederhanakan pada MVP, tetapi batas tanggung jawab frontend, backend, konfigurasi, migration, dan testing harus tetap jelas.

---

## 15. Tahapan Implementasi

### Tahap 0 — Validasi kebutuhan dan desain

- Konfirmasi skenario toko, perangkat, internet, piutang, dan pembayaran.
- Finalisasi aturan satuan dan harga grosir.
- Finalisasi metode HPP.
- Buat user flow dan wireframe kasir.
- Buat ERD, API contract, dan threat model ringkas.

**Output:** spesifikasi final, ERD, wireframe, dan backlog.

### Tahap 1 — Fondasi aplikasi

- Repository, konfigurasi, lint/format, dan test runner.
- Database PostgreSQL dan migration awal.
- Login, pengguna, role, permission.
- Pengaturan toko dan audit log dasar.

**Output:** aplikasi bisa dijalankan di lingkungan development/staging dengan autentikasi.

### Tahap 2 — Master data dan inventori dasar

- Kategori, produk, varian, SKU/barcode.
- Satuan dan konversi.
- Harga eceran/grosir.
- Stok awal dan stock movement.
- Pencarian produk.

**Output:** master data dan saldo stok dapat dikelola serta diaudit.

### Tahap 3 — Transaksi kasir

- Keranjang.
- Harga server-side.
- Checkout atomik.
- Pembayaran dan kembalian.
- Nomor transaksi dan struk.
- Idempotensi dan penanganan konflik stok.

**Output:** transaksi penjualan inti siap diuji dengan data realistis.

### Tahap 4 — Laporan dan operasional

- Riwayat transaksi.
- Laporan penjualan dan metode pembayaran.
- Stok menipis.
- Shift dan kas.
- Pembelian/supplier jika termasuk cakupan rilis.

**Output:** pemilik dapat memantau penjualan dan persediaan.

### Tahap 5 — Hardening dan go-live

- Uji keamanan dan permission.
- Uji beban sesuai perkiraan transaksi.
- Uji backup/restore dan rollback.
- Uji printer/barcode pada perangkat nyata.
- Migrasi data awal dan pelatihan pengguna.
- Go-live terbatas, pemantauan, dan perbaikan.

**Output:** rilis produksi yang sudah melewati acceptance test dan memiliki prosedur operasional.

### Tahap 6 — Pengembangan lanjutan

Berdasarkan kebutuhan nyata:
- Piutang pelanggan.
- Retur dan refund yang lebih lengkap.
- Multi-gudang/cabang.
- Integrasi payment gateway.
- Barcode label.
- PWA/offline dengan sinkronisasi jika benar-benar dibutuhkan.
- Analitik lanjutan.

---

## 16. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Konversi satuan salah | Stok tidak akurat | Satuan dasar, snapshot faktor konversi, test kasus |
| Harga grosir salah | Kerugian/komplain | Aturan harga server-side dan test batas kuantitas |
| Checkout ganda | Penjualan ganda | Idempotency key dan unique constraint |
| Dua kasir menjual stok terakhir | Stok negatif | Transaksi DB, locking/atomic update, validasi stok |
| Histori transaksi berubah | Laporan tidak konsisten | Snapshot harga, SKU, nama, dan konversi |
| Penghapusan transaksi | Sulit audit | Void/retur, permission, audit log |
| Backup tidak bisa dipulihkan | Kehilangan data | Uji restore berkala |
| Non-tunai belum terkonfirmasi | Rekonsiliasi salah | Status pembayaran dan prosedur konfirmasi |
| Listrik/internet mati | Operasi berhenti | Prosedur darurat; desain offline khusus bila wajib |
| Kebocoran kredensial | Akses ilegal | Secret management, least privilege, rotasi |
| HPP tidak jelas | Laba salah | Tentukan metode valuasi sebelum laporan laba resmi |

---

## 17. Checklist Go-Live

### Produk dan stok
- [ ] Semua produk memiliki SKU unik.
- [ ] Varian, satuan dasar, dan konversi sudah diverifikasi.
- [ ] Harga eceran dan grosir sudah diuji.
- [ ] Stok awal sudah direkonsiliasi dengan stok fisik.
- [ ] Stok rusak dipisahkan sesuai prosedur.

### Kasir
- [ ] Login dan hak akses diuji.
- [ ] Checkout tunai dan non-tunai diuji.
- [ ] Kembalian diuji.
- [ ] Request ganda tidak membuat transaksi ganda.
- [ ] Struk dapat dicetak ulang.
- [ ] Pembatalan dan retur mengikuti izin yang benar.

### Keamanan dan infrastruktur
- [ ] HTTPS aktif untuk akses jaringan publik.
- [ ] Kredensial produksi tidak ada di repository.
- [ ] Backup otomatis aktif.
- [ ] Restore backup sudah diuji.
- [ ] Log dan health check aktif.
- [ ] Firewall dan akses database dibatasi.
- [ ] Prosedur gangguan tersedia.

### Pengguna dan operasional
- [ ] Akun setiap pengguna dibuat sesuai role.
- [ ] Kasir/admin mendapat pelatihan.
- [ ] Prosedur buka/tutup kasir tersedia.
- [ ] Prosedur stok opname tersedia.
- [ ] Prosedur internet/listrik mati disepakati.
- [ ] Pemilik menyetujui definisi laporan dan HPP.

---

## 18. Definisi Selesai untuk MVP

MVP dapat dianggap siap dipakai untuk uji operasional ketika:

1. Pengguna dapat login sesuai perannya.
2. Produk, varian, satuan, konversi, dan harga dapat dikelola.
3. Kasir dapat membuat transaksi multi-item.
4. Harga eceran/grosir diterapkan sesuai aturan.
5. Stok diperbarui secara atomik dan riwayatnya tercatat.
6. Pembayaran tunai/non-tunai dicatat sesuai kebijakan.
7. Struk dan riwayat transaksi tersedia.
8. Laporan penjualan dasar dan stok dapat diperiksa.
9. Tindakan sensitif dibatasi dan diaudit.
10. Test inti, backup, dan restore berhasil.
11. Pemilik toko menyetujui alur kerja, data awal, serta prosedur saat gangguan.

---

## 19. Keputusan Produk yang Belum Final

Jangan menebak keputusan berikut saat coding. Catat persetujuan pemilik produk:

| Keputusan | Pilihan yang perlu ditentukan |
|---|---|
| Offline | Online saja, LAN lokal, atau offline-first |
| Perangkat | PC kasir, tablet, HP, atau kombinasi |
| Pembayaran | Satu metode atau split payment |
| Piutang pelanggan | Tidak ada / ada |
| Satuan | Daftar satuan dan konversi tiap produk |
| Harga | Eceran, grosir, bertingkat, harga pelanggan |
| HPP | Moving average / FIFO / kebijakan lain |
| Retur | Kebijakan, jangka waktu, kondisi barang |
| Printer | Tidak ada / thermal 58 mm / thermal 80 mm |
| Barcode | Scanner saja / cetak label / belum diperlukan |
| Cabang | Satu lokasi / multi-gudang / multi-cabang |
| Backup | Retensi, RPO, RTO, dan lokasi penyimpanan |
| Pembayaran non-tunai | Pencatatan manual / integrasi penyedia |

---

## 20. Instruksi Implementasi untuk Tim/AI Coding Agent

Gunakan dokumen ini sebagai sumber kebutuhan utama dan implementasikan secara bertahap.

1. Mulai dengan merangkum asumsi dan mengidentifikasi keputusan yang belum final. Jangan menambahkan fitur besar di luar scope tanpa persetujuan.
2. Buat ERD, migration, API contract, dan user flow sebelum membangun semua halaman.
3. Bangun fondasi backend dan test lebih dahulu untuk aturan kritis: harga bertingkat, konversi satuan, checkout atomik, idempotensi, dan stok.
4. Gunakan PostgreSQL transaction untuk proses yang mengubah transaksi dan persediaan.
5. Implementasikan validasi dan permission di backend; frontend hanya menyajikan antarmuka.
6. Buat UI kasir yang cepat, jelas, dan mudah digunakan dengan keyboard.
7. Sediakan seed/demo data yang realistis tetapi tidak mengandung data pribadi nyata.
8. Buat `.env.example`, dokumentasi setup Windows/development, migration, testing, backup, restore, dan deployment.
9. Jalankan lint, type-check, unit test, integration test, serta acceptance test sebelum menyatakan fitur selesai.
10. Jangan mengklaim sistem production-ready hanya karena aplikasi dapat dijalankan. Production-ready mensyaratkan pengujian, kontrol akses, backup/restore, logging, dan prosedur operasional.
11. Implementasikan MVP terlebih dahulu; fitur P1/P2 dibuat setelah alur inti stabil.
12. Jika ada konflik antara implementasi dan dokumen ini, jelaskan konflik dan minta keputusan sebelum mengubah aturan bisnis kritis.

**Prioritas teknis tertinggi:** konsistensi stok, ketepatan harga bertingkat dan konversi satuan, transaksi checkout yang atomik, pencegahan transaksi ganda, serta audit untuk tindakan sensitif.
