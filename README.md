# 🎬 IndoClip Pro — OpusClip Clone 100% Khusus Kreator Indonesia (0 Budget di Windows)

Aplikasi web full-stack lokal yang mengkloning seluruh fitur unggulan **OpusClip**, dioptimalkan khusus untuk konten kreator & YouTuber Indonesia (Podcast, Gaming, Reaction, Storytelling) dengan 0 budget di Windows (`localhost`).

---

## 🚀 Fitur Unggulan

1. **Audio-First & Audio Peak Detection**:
   - Hanya mengunduh trek audio terbaik di awal via `yt-dlp` untuk menghemat kuota & waktu.
   - Analisis lonjakan volume, tawa pecah, dan teriakan klimaks menggunakan `numpy` & `scipy.signal.find_peaks` yang disimpan ke `peaks.json`.
2. **Transkripsi Akurat Bahasa Indonesia (`faster-whisper`)**:
   - Mendukung aksen lokal, bahasa gaul sehari-hari, slang tongkrongan, dan istilah bahasa Inggris dengan `word_timestamps=True`.
   - Deteksi otomatis GPU CUDA (`float16`) atau fallback ke CPU (`int8`) tanpa error.
3. **Kurasi Viral & Copywriting (`google-genai` & `gemini-2.5-flash`)**:
   - Menggunakan SDK resmi terbaru `google-genai` dengan **Structured Outputs (Pydantic)**.
   - Memilih 3–6 klip viral terbaik berdurasi 30–65 detik dengan hook kuat di 3 detik pertama.
   - Menghasilkan: `title`, `hook_banner` (maks 5 kata kapital), `virality_score` + rincian (`hook_score`, `flow_score`, `engagement_score`), `category`, koreksi ejaan gaul, dan caption siap posting + hashtag TikTok/Shorts.
4. **Partial Video Download**:
   - Hanya mengunduh potongan video resolusi 1080p pada bagian klip terpilih menggunakan `yt-dlp --download-sections`.
5. **Smart Multi-Mode Reframing (`reframer.py`)**:
   - Deteksi wajah & ekspresi menggunakan **MediaPipe Face Detection & Face Mesh** (sampling tiap 3 frame untuk performa cepat di laptop).
   - **Mode PODCAST (2+ Wajah)**: Split-screen atas-bawah `1080x1920` (masing-masing `1080x960`) jika 2 orang; Active Speaker Switching berbasis *Mouth Aspect Ratio (MAR)* jika 3+ orang (tahan kamera minimal 1.5 detik agar stabil).
   - **Mode GAMING**: Facecam streamer di atas (`1080x620`) + gameplay di bawah (`1080x1300`).
   - **Mode SOLO**: *Dynamic Face Tracking* halus dengan *Exponential Moving Average (EMA)*.
6. **Editing Anti-Reused Content & Animated Subtitles (`renderer.py`)**:
   - **Dynamic Punch-In Zoom**: Zoom halus 1.08x pada timestamp lonjakan audio peaks.
   - **3-Second Hook Overlay**: Kotak banner modern di detik 0.0 sampai 3.2 berisi teks `hook_banner`.
   - **Opus-Style Animated Subtitle (.ass)**: Subtitle 2–4 kata per baris, font tebal kapital, outline hitam tebal, dan animasi kata aktif membesar 115% dengan warna pilihan (`Opus Green`, `Salmon Pink`, `Cyber Yellow`).
7. **Inline Subtitle Editor**:
   - Kemampuan mengedit kata/kalimat/hook banner langsung dari web dan tombol **"Re-render Subtitle"** yang selesai dalam ~2 detik tanpa download ulang video.

---

## 🛠️ Prasyarat di Windows

- **Python 3.10 - 3.12**
- **Node.js v18+ & npm**
- **FFmpeg dengan libass support** (Mudah diinstal via WinGet)

---

## 📦 Panduan Instalasi Cepat di Windows

### 1. Instal FFmpeg (Jika belum ada)
Jalankan perintah ini di PowerShell / Terminal Administrator:
```powershell
winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
```
*Catatan: IndoClip Pro juga memiliki auto-detect bawaan yang secara otomatis mencari binary FFmpeg dari direktori WinGet jika belum terdaftar di PATH.*

### 2. Setup Backend (FastAPI)
Buka terminal dan masuk ke folder `backend`:
```powershell
cd d:\SOFTWARE\XAMPP\htdocs\IndoClip\backend

# Install dependensi backend
pip install -r requirements.txt
```

Salin atau sesuaikan konfigurasi `.env`:
```powershell
# File .env sudah dibuat otomatis dari .env.example
# Anda bisa mengisi GEMINI_API_KEY di file backend/.env atau lewat UI browser!
```

Jalankan server backend:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Backend akan aktif di: `http://127.0.0.1:8000` (Dokumentasi Swagger API di `http://127.0.0.1:8000/docs`).

### 3. Setup Frontend (Next.js)
Buka terminal baru dan masuk ke folder `frontend`:
```powershell
cd d:\SOFTWARE\XAMPP\htdocs\IndoClip\frontend

# Install dependensi frontend
npm install

# Jalankan server frontend development
npm run dev
```
Frontend akan aktif di: `http://localhost:3000`.

---

## 💡 Cara Penggunaan

1. Buka browser ke `http://localhost:3000`.
2. Klik tombol **"Set Gemini API Key"** di kanan atas dan masukkan API Key Google Gemini Anda (dapatkan gratis di [Google AI Studio](https://aistudio.google.com)). Key tersimpan aman di browser Anda.
3. Masukkan link video YouTube (Podcast, Gaming, Reaction, atau Storytelling).
4. Pilih **Mode Reframing 9:16** (`Auto Detect`, `Podcast Multi-Speaker`, `Gaming Facecam`, atau `Solo Creator`).
5. Pilih **Warna Highlight Subtitle** (`Opus Green`, `Salmon Pink`, atau `Cyber Yellow`).
6. Klik **"Generate Klip Viral Vertikal 9:16 Sekarang"**.
7. Pantau log progres real-time per tahap via **Pipeline Tracker (SSE)**.
8. Setelah selesai:
   - Preview video vertikal 9:16 langsung di browser.
   - Klik **"Edit Subtitle & Hook"** jika ingin mengoreksi kata atau mengganti warna highlight, lalu klik **"Re-render Subtitle Sekarang"** (hanya butuh ~2 detik!).
   - Klik **"Copy Caption & Hashtag"** untuk menyalin caption TikTok/Shorts.
   - Klik **"Download MP4"** untuk mengunduh video final kualitas 1080p.

---

## 📁 Struktur Proyek

```
IndoClip/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI routes, CORS, static mount
│   │   ├── config.py              # Konfigurasi & path loader
│   │   ├── models.py              # Schema Pydantic terstruktur
│   │   ├── utils.py               # Auto-detect FFmpeg & subprocess helper
│   │   ├── audio_analyzer.py      # Tahap 1: yt-dlp audio & scipy peak detection
│   │   ├── transcriber.py         # Tahap 2: faster-whisper dengan CUDA/CPU fallback
│   │   ├── curator.py             # Tahap 3: google-genai gemini-2.5-flash viral curator
│   │   ├── downloader.py          # Tahap 4: yt-dlp partial video downloader
│   │   ├── reframer.py            # Tahap 5: MediaPipe multi-mode 9:16 reframer
│   │   ├── subtitle_generator.py  # Tahap 6: Generator file subtitle animasi .ass
│   │   ├── renderer.py            # Tahap 6: Punch-in zoom, hook banner, ass burn
│   │   └── pipeline.py            # Orchestrator & SSE live event streamer
│   ├── .env.example
│   ├── .env                       # Terbuat otomatis
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Main Dashboard
│   │   └── globals.css            # Dark mode ala OpusClip + Salmon Pink accents
│   ├── components/
│   │   ├── Navbar.tsx             # Brand, status hardware & modal API key
│   │   ├── ControlPanel.tsx       # Input URL, selector layout mode & warna subtitle
│   │   ├── PipelineTracker.tsx    # 6-Stage SSE tracker & live log console
│   │   ├── ClipCard.tsx           # 9:16 player preview, virality score & actions
│   │   └── SubtitleEditorModal.tsx# Inline subtitle editor & instant re-render
│   ├── types/
│   │   └── index.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── next.config.js
└── README.md
```

---

## ☁️ Panduan Hosting Online 0 Budget: Vercel (Frontend) + Google Colab (Backend GPU)

Arsitektur ini adalah solusi terbaik untuk menjalankan IndoClip Pro secara publik di internet dengan **biaya Rp 0**:
* **Frontend di Vercel:** Hosting Next.js gratis tercepat di dunia, CDN global edge, HTTPS otomatis, dan tampilan responsif di HP/Laptop.
* **Backend di Google Colab:** Menyediakan **NVIDIA T4 GPU (16GB VRAM)** gratis dan koneksi internet datacenter (500+ Mbps) untuk download video, transkripsi Whisper kilat, dan rendering FFmpeg berkecepatan tinggi.

### Langkah 1: Jalankan Backend di Google Colab (GPU)
1. Buka [Google Colab](https://colab.research.google.com).
2. Klik tab **Upload** lalu pilih file notebook **`IndoClip_Colab_Backend.ipynb`** yang sudah tersedia di folder utama proyek ini.
3. Di menu atas Colab, pastikan tipe akselerator GPU aktif:
   * Klik **Runtime** -> **Change runtime type** -> pilih **T4 GPU** -> **Save**.
4. Jalankan sel notebook dari atas ke bawah:
   * Sel akan otomatis menginstal FFmpeg, dependensi Python, dan mengunduh Cloudflare Tunnel.
   * Pada sel terakhir, script akan otomatis memunculkan URL publik HTTPS Anda, contoh:
     ```
     🚀 URL BACKEND ANDA:
     https://random-subdomain.trycloudflare.com
     ```
   * *Biarkan tab Google Colab tetap berjalan selama Anda menggunakan aplikasi.*

---

### Langkah 2: Deploy Frontend ke Vercel
1. Simpan proyek IndoClip Anda ke repository GitHub (publik atau privat):
   ```bash
   git init
   git add .
   git commit -m "Deploy IndoClip Pro"
   git branch -M main
   git remote add origin https://github.com/USERNAME/IndoClip.git
   git push -u origin main
   ```
2. Buka **[Vercel Dashboard](https://vercel.com)** lalu login dengan akun GitHub Anda.
3. Klik tombol **"Add New..."** -> **"Project"** -> pilih repository `IndoClip`.
4. Pada menu konfigurasi proyek:
   * **Framework Preset:** Next.js
   * **Root Directory:** Klik edit dan pilih folder **`frontend`**
   * **Environment Variables:** Tambahkan 1 variabel:
     * **Key:** `NEXT_PUBLIC_API_URL`
     * **Value:** Masukkan URL Cloudflare Tunnel dari Google Colab Anda (misal `https://random-subdomain.trycloudflare.com`)
5. Klik **Deploy**!

Dalam 1–2 menit, Vercel akan menghasilkan URL domain publik Anda (contoh: `https://indoclip-pro.vercel.app`). Anda sekarang bisa mengakses IndoClip Pro dari HP, tablet, maupun komputer manapun dengan kecepatan rendering GPU!

---

## ⚖️ Lisensi
Dilisensikan di bawah lisensi MIT untuk kreator konten dan developer Indonesia.
