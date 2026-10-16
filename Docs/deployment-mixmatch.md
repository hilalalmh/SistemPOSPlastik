# Deploy ke Jagoan Hosting "Cloud Hosting MixMatch" (cPanel)

Panduan menaruh Sistem POS Toko Plastik di shared hosting cPanel: backend FastAPI
(dijalankan sebagai WSGI via Passenger) + frontend React (file statis).

## Arsitektur

```
pos.domain.com   -> file statis frontend (hasil `npm run build`)   [public_html]
api.domain.com   -> backend FastAPI (Passenger + passenger_wsgi.py)
```

- Backend memakai **MySQL/MariaDB** (bukan PostgreSQL) dan **WSGI** (bukan uvicorn).
  Keduanya sudah disiapkan di repo (`pymysql`, `a2wsgi`, `passenger_wsgi.py`).
- Frontend memanggil API lintas subdomain, jadi **CORS** harus diatur.

## Prasyarat

- Paket hosting cPanel yang menyediakan **Setup Python App** (Passenger) dan MySQL.
- Akses SSH (disarankan) atau minimal Terminal + File Manager + PHP/cron.
- Python 3.11/3.12 dipilih dari cPanel.
- Dua subdomain (gratis dari cPanel) atau 1 domain + 1 subdomain.

## 1. Subdomain & SSL

1. cPanel → **Domains / Subdomains**: buat `api.domain.com` (docroot kosong) dan
   `pos.domain.com` (docroot `public_html` atau folder khusus).
2. Aktifkan **AutoSSL/Let's Encrypt** untuk keduanya, tunggu sampai HTTPS aktif.

## 2. Database MySQL

1. cPanel → **MySQL Databases**:
   - Buat database, mis. `user_pos`.
   - Buat user, mis. `user_posuser` + password kuat.
   - **Add User to Database** → centang ALL PRIVILEGES.
2. Catat: host biasanya `localhost`, nama DB, user, password.
3. URL koneksi: `mysql+pymysql://USER:PASSWORD@localhost:DBNAME`.

> Catatan: karena hanya kredensial DB yang berbeda, jangan pakai password yang sama
> dengan yang ada di `.env.example`.

## 3. Ambil kode dari GitHub (Git Version Control)

Metode disarankan agar hosting selalu sinkron dengan GitHub:

1. cPanel → **Git Version Control** → **Create**.
2. **Clone URL**: `https://github.com/hilalalmh/SistemPOSPlastik.git`
   (repo publik, tidak perlu kredensial).
3. **Repository Path**: `repos/pos`
4. **Repository Name**: `pos` → klik **Create**.

Hasilnya backend ada di `~/repos/pos/backend` (berisi `passenger_wsgi.py`,
`alembic.ini`, `app/`, `migrations/`). Folder ini yang dipakai sebagai
*Application root* pada langkah berikutnya.

> Alternatif tanpa Git: upload ZIP lalu ekstrak via File Manager ke `~/repos/pos`.

### 3b. Auto-deploy dari Git (opsional, `.cpanel.yml`)

Agar tombol **Deploy HEAD Commit** otomatis memasang dependensi dan menjalankan
migrasi, buat file `.cpanel.yml` di root repo (sesuaikan nama app & versi Python):

```yaml
---
deployment:
  tasks:
    - export APPNAME=pos_backend
    - export PYVER=3.11
    - export VENV=$HOME/virtualenv/$APPNAME/$PYVER
    - export APPDIR=$HOME/repos/pos/backend
    - $VENV/bin/pip install -r $APPDIR/requirements.txt
    - cd $APPDIR && $VENV/bin/alembic upgrade head
    - touch $APPDIR/passenger_wsgi.py
```

> `alembic` membaca `.env` di application root, jadi buat `.env` (langkah 4b) dulu
> sebelum menekan **Deploy HEAD Commit**.

## 4. Setup Python App

cPanel → **Setup Python App** → **Create Application**:

| Field | Nilai |
| --- | --- |
| Python version | 3.11 atau 3.12 |
| Application root | `repos/pos/backend` |
| Application URL | `api.domain.com` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

`passenger_wsgi.py` sudah berisi adapter ASGI→WSGI, jadi tidak perlu diubah.

## 4b. Environment variables

Isi bagian **Environment Variables** pada Python App (atau buat file `.env` di
application root). Nilai produksi:

```
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:DBNAME
SECRET_KEY=<hasil generate>
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://pos.domain.com
TIMEZONE=Asia/Jakarta
```

- Buat `SECRET_KEY` acak: `python -c "import secrets; print(secrets.token_hex(32))"`.
- `CORS_ORIGINS` boleh diisi beberapa origin, dipisah koma.
- Jika memakai file `.env`, taruh di application root `~/repos/pos/backend/.env`.

## 4b. Install dependensi

Backend punya `requirements.txt` (khusus hosting, tanpa psycopg).

- cPanel **Setup Python App** → bagian **Configuration files** →
  isi `requirements.txt`, lalu klik **Run Pip Install**.
- Atau via SSH:

```bash
source ~/virtualenv/pos_backend/3.11/bin/activate   # sesuaikan nama/path
cd ~/repos/pos/backend
pip install -r requirements.txt
```

## 5. Migrasi & seed (sekali saja)

Jalankan dengan virtualenv yang sama:

```bash
source ~/virtualenv/pos_backend/3.11/bin/activate
cd ~/repos/pos/backend
alembic upgrade head        # buat semua tabel
python -m app.seed          # data awal (role, user, contoh produk)
```

Login awal: `admin / admin123` dan `kasir1 / kasir123` — **ganti segera** setelah
masuk pertama kali. Jika tidak ada SSH, gunakan fitur **Run Script** cPanel atau
cron job sementara untuk menjalankan perintah di atas.

## 6. Frontend

Build di komputer (bukan di hosting), arahkan ke API produksi:

```bash
cd frontend
# PowerShell
$env:VITE_API_BASE="https://api.domain.com/api/v1"; npm run build
# bash
VITE_API_BASE=https://api.domain.com/api/v1 npm run build
```

Upload **isi** `frontend/dist/` ke docroot frontend (`public_html` untuk
`pos.domain.com`). File `public/.htaccess` sudah ikut ter-build ke `dist/` dan
menangani SPA fallback (React Router).

> Frontend **tidak** di-deploy lewat Git karena folder `dist` hasil build tidak
> di-commit. Build ulang lokal setiap ada perubahan lalu upload ulang.

## 7. Verifikasi

1. `https://api.domain.com/api/health` → `{"status":"ok","version":"1.0.0"}`.
2. Buka `https://pos.domain.com`, login, cek dashboard menampilkan data.
3. Uji mutasi (buat produk, transaksi kasir) untuk memastikan tulis-baca MySQL OK.
4. Jika login gagal karena CORS: pastikan `CORS_ORIGINS` persis sama dengan origin
   frontend (`https://pos.domain.com`, tanpa trailing slash) lalu restart app
   (touch `passenger_wsgi.py` atau Restart di panel Python).

## 8. Operasional

- **Restart app** setelah ubah `.env`/kode: cPanel → Setup Python App → **Restart**,
  atau `touch ~/repos/pos/backend/passenger_wsgi.py`.
- **Update dari GitHub** (sinkron): cPanel → **Git Version Control** →
  **Update from Remote** (`git pull`), lalu **Deploy HEAD Commit**
  (pip install + migrasi otomatis bila `.cpanel.yml` dipakai), lalu **Restart**.
  Tanpa `.cpanel.yml`, setelah pull jalankan:

  ```bash
  source ~/virtualenv/pos_backend/3.11/bin/activate
  cd ~/repos/pos/backend
  pip install -r requirements.txt
  alembic upgrade head
  ```

- **Frontend**: build ulang lokal lalu upload `dist` (lihat langkah 6).
- **Backup**: cPanel → Backup Wizard / Backup, dan ekspor DB via phpMyAdmin.
- **Log**: cek `stderr.log` di application root atau menu Errors cPanel.
- **Jangan** commit file `.env`; simpan kredensial hanya di server.

## Troubleshooting

| Gejala | Penyebab umum | Solusi |
| --- | --- | --- |
| 500 di `api.domain.com` | dependensi belum terpasang / entry point salah | cek `stderr.log`, pastikan Startup file `passenger_wsgi.py` & entry point `application`, ulangi Run Pip Install |
| `Access denied for user` | kredensial DB salah / user belum di-Add ke DB | perbaiki `DATABASE_URL`, pastikan user punya ALL PRIVILEGES |
| `ModuleNotFoundError: No module named 'a2wsgi'` | pip install belum dijalankan di venv app | jalankan Run Pip Install / `pip install -r requirements.txt` di venv app |
| Halaman putih / 404 saat refresh di frontend | `.htaccess` SPA tidak terpasang | upload ulang `dist` termasuk `.htaccess` |
| Waktu/server tidak akurat | konfigurasi zona | `TIMEZONE=Asia/Jakarta`; server menyimpan UTC, tampilan dikonversi di aplikasi |
