"""
IndoClip Pro - Ngrok Static Domain Runner
Menjalankan backend FastAPI Uvicorn dan menghubungkannya langsung ke domain statis Ngrok:
https://brunette-crimson-yen.ngrok-free.dev
"""

import os
import sys
import time
import signal
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("indoclip.ngrok")

# ==============================================================================
# KONFIGURASI NGROK
# ==============================================================================
# Masukkan NGROK_AUTHTOKEN Anda di sini atau lewat Environment Variable NGROK_AUTHTOKEN
NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "MASUKKAN_AUTHTOKEN_NGROK_ANDA_DI_SINI")

# Domain statis gratis Ngrok Anda
NGROK_DOMAIN = "brunette-crimson-yen.ngrok-free.dev"
PORT = int(os.environ.get("PORT", 8000))
HOST = "0.0.0.0"

def start_server_with_ngrok():
    # 1. Pastikan library pyngrok terpasang
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        logger.error("Library 'pyngrok' belum terinstall! Silakan jalankan: pip install pyngrok")
        sys.exit(1)

    # 2. Atur Authtoken Ngrok
    if NGROK_AUTHTOKEN and NGROK_AUTHTOKEN != "MASUKKAN_AUTHTOKEN_NGROK_ANDA_DI_SINI":
        ngrok.set_auth_token(NGROK_AUTHTOKEN)
        logger.info("Ngrok authtoken berhasil dikonfigurasi.")
    else:
        logger.warning(
            "⚠️ NGROK_AUTHTOKEN belum diisi! Jika Anda mendapatkan error autentikasi, "
            "silakan isi variabel NGROK_AUTHTOKEN di atas file ini atau via export NGROK_AUTHTOKEN='token_anda'."
        )

    # 3. Hentikan tunnel lama jika ada
    try:
        tunnels = ngrok.get_tunnels()
        for t in tunnels:
            logger.info(f"Menutup tunnel lama: {t.public_url}")
            ngrok.disconnect(t.public_url)
    except Exception:
        pass

    # 4. Hubungkan ke domain statis Ngrok
    logger.info(f"Menghubungkan tunnel ke domain statis: {NGROK_DOMAIN} (Port {PORT})...")
    try:
        tunnel = ngrok.connect(PORT, domain=NGROK_DOMAIN)
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://")
    except Exception as e:
        logger.warning(f"Gagal menghubungkan dengan opsi 'domain={NGROK_DOMAIN}': {e}")
        logger.info("Mencoba opsi fallback 'hostname'...")
        try:
            tunnel = ngrok.connect(PORT, hostname=NGROK_DOMAIN)
            public_url = tunnel.public_url
        except Exception as e2:
            logger.error(f"❌ Gagal menghubungkan ke domain statis Ngrok: {e2}")
            logger.info("Membuka tunnel dinamis acak sebagai alternatif...")
            tunnel = ngrok.connect(PORT)
            public_url = tunnel.public_url

    print("\n" + "=" * 65)
    print("🚀 INDOCLIP PRO BACKEND BERHASIL TERHUBUNG KE NGROK!")
    print(f"👉 Public URL  : {public_url}")
    print(f"👉 Local URL   : http://127.0.0.1:{PORT}")
    print(f"👉 Health Check: {public_url}/api/health")
    print("=" * 65)
    print("Frontend Vercel Anda sekarang otomatis terhubung ke URL ini tanpa perlu ubah setting!")
    print("Tekan CTRL+C untuk menghentikan server.\n")

    # 5. Jalankan server Uvicorn
    import uvicorn
    try:
        uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
    except KeyboardInterrupt:
        print("\nMenghentikan server dan menutup tunnel Ngrok...")
    finally:
        ngrok.disconnect(public_url)
        ngrok.kill()
        print("✅ Server dan tunnel Ngrok berhasil ditutup.")

if __name__ == "__main__":
    start_server_with_ngrok()
