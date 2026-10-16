# Wireframe Halaman Kasir — Sistem POS Toko Plastik

**Dokumen:** `wireframe-cashier.md`
**Status:** Draft desain UI/UX (Tahap 0)
**Sumber:** `production.md` Bagian 9, `user-flow.md`
**Versi:** 1.0

Wireframe ini menggunakan ASCII dan hanya menggambarkan tata letak serta interaksi utama. Halaman kasir dioptimalkan untuk **desktop + keyboard** (keputusan: online, PC kasir).

---

## 1. Tata Letak Utama (Desktop)

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│  Toko Plastik Jaya        Kasir: Budi (Shift #102)        [Riwayat] [Keluar]   │
├───────────────────────────────────────────────────────────────────────────────┤
│  ┌── Pencarian / Scan ─────────────────────┐  ┌── Keranjang ─────────────────┐ │
│  │ [ F2 ]  Scan barcode atau cari produk... │  │ No  Item            Qty  Hrg │ │
│  │                                          │  │ ──────────────────────────── │ │
│  │ Hasil:                                   │  │ 1   Kresek 24x36     10 Pak  │ │
│  │  • Kantong Kresek 24x36 Hitam            │  │      @4.700        47.000    │ │
│  │      SKU PLT-... | stok 1.850 lbr        │  │ 2   Plastik Bening    5 Pak  │ │
│  │  • Kantong Kresek 30x40 Bening           │  │      @6.000        30.000    │ │
│  │      SKU PLT-... | stok 920 lbr          │  │                              │ │
│  │  • ...                                    │  │ [F3] Ubah  [F4] Hapus        │ │
│  │                                          │  └──────────────────────────────┘ │
│  └──────────────────────────────────────────┘                                   │
│                                                                                 │
│  ┌── Satuan & Harga (item terpilih) ───────┐  ┌── Ringkasan ──────────────────┐ │
│  │ Varian: Kresek 24x36 Hitam              │  │ Subtotal          77.000       │ │
│  │ Satuan: ( ) Lembar ( ) Pak (*) Bal      │  │ Diskon [F6]        0           │ │
│  │ Kuantitas: [ 10 ]                       │  │ Pajak              0           │ │
│  │ Harga/pak: 4.700 (tier 10-49)           │  │ ─────────────────────────────  │ │
│  │ Ekuivalen stok: 500 lembar              │  │ TOTAL             77.000       │ │
│  │                                          │  │                                │ │
│  │ [F5] Tambah ke Keranjang                │  │ [F9] BAYAR                     │ │
│  └──────────────────────────────────────────┘  └──────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────────────────┤
│  F1 Bantuan   F2 Cari   F5 Tambah   F9 Bayar   F10 Tutup Kasir                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Prinsip:**
- Panel kiri: pencarian/scan dan pemilihan satuan—input utama.
- Panel kanan: ringkasan dan tombol bayar—selalu terlihat.
- Format nominal: `Rp77.000` pada tampilan akhir (di wireframe ditulis tanpa prefix agar ringkas).
- Status stok selalu tampil pada hasil pencarian.

---

## 2. Dialog Pembayaran (Split Payment)

```text
┌──────────────────────── Pembayaran ────────────────────────┐
│  Total: Rp77.000                                            │
│                                                             │
│  Metode pembayaran (boleh lebih dari satu):                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ [Tunai ▾]   Nominal: [ 50000 ]              [Hapus]    │ │
│  │ [QRIS  ▾]   Nominal: [ 27000 ] Ref: [      ] [Hapus]   │ │
│  │ [+ Tambah metode]                                      │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Total dibayar : Rp77.000                                   │
│  Kembalian     : Rp0                                        │
│                                                             │
│  ( ) Konfirmasi transaksi      [ Batal ]   [ BAYAR ]        │
└─────────────────────────────────────────────────────────────┘
```

**Aturan UI:**
- Tombol `BAYAR` aktif hanya jika total dibayar ≥ total.
- Kembalian dihitung dari komponen tunai.
- `BAYAR` dinonaktifkan selama request; mencegah klik ganda.
- Metode non-tunai menampilkan opsi referensi opsional.
- Selesai → tampil nomor transaksi dan struk.

---

## 3. Dialog Struk Setelah Berhasil

```text
┌──────────────── Transaksi Berhasil ─────────────────┐
│  Nomor: SLS-202610-000123                            │
│  Toko Plastik Jaya                                   │
│  ─────────────────────────────────────────────────   │
│  Kresek 24x36   10 Pak @4.700        47.000          │
│  Plastik Bening  5 Pak @6.000        30.000          │
│  ─────────────────────────────────────────────────   │
│  TOTAL                               77.000          │
│  Tunai 50.000 | QRIS 27.000                          │
│  Kembali                              0              │
│  ─────────────────────────────────────────────────   │
│  [ Lihat Struk ]  [ Transaksi Baru ]  [ Tutup ]      │
└──────────────────────────────────────────────────────┘
```

- `Transaksi Baru` mengosongkan keranjang dan kembali ke pencarian (fokus otomatis ke input scan).
- `Lihat Struk` membuka `GET /sales/{id}/receipt`.
- Jika pencetakan gagal, transaksi tetap tersimpan dan struk dapat dibuka ulang.

---

## 4. State UI Halaman Kasir

| State | Tampilan |
|---|---|
| Loading | Skeleton pada daftar hasil pencarian |
| Empty (keranjang) | Pesan "Keranjang kosong. Scan barcode atau cari produk." |
| Empty (pencarian) | "Produk tidak ditemukan" + saran periksa ejaan/kategori |
| Error | Banner merah "Gagal memuat produk. Coba lagi." + tombol ulangi |
| Validasi stok | Baris item ditandai; pesan "Stok tidak cukup, tersedia X dst." |
| Sedang checkout | Tombol disable + spinner; keranjang tidak dapat diubah |
| Konflik idempotensi | Transaksi tidak digandakan; tampilkan transaksi yang sudah ada |

---

## 5. Aksesibilitas & Keyboard

- Semua aksi utama memiliki pintasan: F2 cari, F5 tambah, F9 bayar, F10 tutup kasir.
- Fokus otomatis ke input scan saat membuka halaman dan setelah transaksi selesai.
- Label form eksplisit; navigasi Tab berurutan.
- Status tidak hanya dibedakan warna, tetapi juga ikon/teks.
- Pesan kesalahan dalam bahasa Indonesia yang menjelaskan langkah perbaikan.

---

## 6. Catatan Responsif

Meskipun target utama PC kasir, tata letak menyesuaikan untuk tablet:
- Pada layar lebih kecil, panel ringkasan menjadi bagian bawah tetap (sticky).
- Dialog pembayaran menjadi layar penuh.
- Tombol tetap dapat dijangkau tanpa scroll berlebihan.
