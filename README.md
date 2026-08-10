# PyAnimeIndo v1.2.4

Nonton anime subtitle Indonesia tanpa iklan. Dengan GUI berbasis **PyQt5** dan **Material UI**, serta **MPV Player** untuk streaming tanpa hambatan.

> **Catatan Proyek & Pengembang**:
> Proyek ini merupakan kelanjutan dari proyek original **[PyAnimeIndo oleh Ayra Hikari](https://github.com/AyraHikari/PyAnimeIndo)** yang diperbarui dan dipelihara ke **Versi 1.2.4**.
> 
> **Pembaruan di v1.2.4**:
> - Pembaruan domain aktif host Otakudesu (`otakudesu.blog`).
> - Ekstraksi streaming universal (mendukung server Pixeldrain, Krakenfiles, VikingFile).
> - Deteksi otomatis lokasi installer MPV Player (WinGet / Path sistem).
> - Perbaikan penanganan metadata & pencegahan crash `SyntaxError`/`TypeError`.
> - Pengemasan executable mandiri (`pyanimeindo.exe`).

---

## Cara Pakai untuk Pengguna (Langsung Executable `.exe`)

Bagi Anda yang hanya ingin menggunakan aplikasi tanpa menginstall Python:

1. Buka folder `dist/` atau unduh file **`pyanimeindo.exe`**.
2. Klik 2x pada file **`pyanimeindo.exe`**.
3. Pastikan **MPV Player** sudah terinstal di komputer Anda (dapat diinstall mudah via Windows Terminal: `winget install mpv`).
4. Selamat menonton anime tanpa iklan!

---

## 🛠️ Panduan Pengembang (Developer Setup)

Bagi Anda pengembang yang ingin memodifikasi atau mengembangkan proyek ini:

### 1. Prasyarat
- Python 3.9 - 3.11 dipasang di sistem.
- MPV Player terpasang di sistem (`winget install mpv` atau dari website [mpv.io](https://mpv.io/)).

### 2. Instalasi Dependensi
Kloning repositori ini dan jalankan perintah berikut pada terminal:

```bash
pip install -r requirements.txt
```

### 3. Menjalankan Aplikasi dalam Mode Pengkodingan
Untuk menjalankan aplikasi secara langsung dari source code Python:

```bash
python pyanimeindo.py
```

### 4. Membangun File Executable (`.exe`)
Untuk mengompilasi kembali proyek Python ini menjadi file `pyanimeindo.exe` tunggal menggunakan **PyInstaller**:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --exclude-module tensorflow --exclude-module torch --exclude-module pandas --exclude-module scipy --exclude-module matplotlib pyanimeindo.py
```

File `.exe` hasil kompilasi akan otomatis dibuat di folder **`dist/pyanimeindo.exe`**.

---

## Fitur Utama
- **Material UI Modern**
- **Streaming Lancar sampai 1080p**
- **Upscaling Gambar hingga 4K UHD** (Menggunakan integrasi Anime4K)
- **Tersedia Download & Batch File**
- **Simpan Anime / Bookmark**
- **Riwayat Nonton & Penanda Episode Ditonton (`√`)**
- **Jadwal Rilis Anime Harian**
- **Bebas Iklan & Tanpa Berlangganan**

---

## Integrasi dengan Anime4K (Khusus MPV Player)
- Buka menu **Pengaturan**, klik tombol `Install (High-end VGA)` atau `Install (Low-end VGA)` sesuai spesifikasi GPU komputer Anda.
- Tutup Pengaturan. Saat streaming di MPV Player, ganti mode preset Anime4K secara *real-time* menggunakan tombol pintasan keyboard:
  - `CTRL + 1` (Mode A - HQ/Fast)
  - `CTRL + 2` (Mode B - HQ/Fast)
  - `CTRL + 3` (Mode C - HQ/Fast)
  - `CTRL + 4` (Mode A+A)
  - `CTRL + 5` (Mode B+B)
  - `CTRL + 6` (Mode C+A)
  - `CTRL + 0` (Matikan / Clear Shaders)

---

## Kredit & Pengembang
- **Programmer/Designer Original**: [Ayra Hikari](https://github.com/AyraHikari)
- **Pemelihara & Pembaru Versi 1.2.4**: [PyAnimeIndo Maintainers]
- **Ikon**: [Heroicons](https://heroicons.com)
- **Host Provider**: Otakudesu
- **Upscaler/Render**: [Anime4K](https://github.com/bloc97/Anime4K)
- **Video Player**: [MPV Player](https://mpv.io/)

