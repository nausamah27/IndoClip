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
        from pyngrok.installer import install_ngrok, get_ngrok_bin
    except ImportError:
        logger.error("Library 'pyngrok' belum terinstall! Silakan jalankan: pip install pyngrok")
        sys.exit(1)

    # 2. Atur Authtoken Ngrok (Aman dari error 'Authtoken already set')
    if NGROK_AUTHTOKEN and NGROK_AUTHTOKEN != "MASUKKAN_AUTHTOKEN_NGROK_ANDA_DI_SINI":
        try:
            ngrok.set_auth_token(NGROK_AUTHTOKEN)
            logger.info("Ngrok authtoken berhasil dikonfigurasi.")
        except Exception as auth_err:
            logger.info(f"Authtoken sudah terdaftar di sistem: {auth_err}")
    else:
        logger.warning(
            "⚠️ NGROK_AUTHTOKEN belum diisi! Jika Anda mendapatkan error autentikasi, "
            "silakan isi variabel NGROK_AUTHTOKEN."
        )

    # 3. Hentikan tunnel lokal lama jika ada
    try:
        tunnels = ngrok.get_tunnels()
        for t in tunnels:
            logger.info(f"Menutup tunnel lokal: {t.public_url}")
            ngrok.disconnect(t.public_url)
    except Exception:
        pass

    # 4. Hubungkan ke domain statis Ngrok
    logger.info(f"Menghubungkan tunnel ke domain statis: {NGROK_DOMAIN} (Port {PORT})...")
    public_url = f"https://{NGROK_DOMAIN}"
    tunnel_connected = False

    # Coba metode 1: pyngrok options url (ngrok v3)
    try:
        tunnel = ngrok.connect(PORT, "http", url=public_url)
        public_url = tunnel.public_url
        tunnel_connected = True
    except Exception as e1:
        if "ERR_NGROK_334" in str(e1):
            logger.error("\n" + "!" * 70)
            logger.error("🚨 PERINGATAN: ENDPOINT NGROK SEDANG DIGUNAKAN DI TEMPAT LAIN!")
            logger.error(f"Domain '{NGROK_DOMAIN}' masih aktif di sesi Google Colab Anda sebelumnya.")
            logger.error("Solusi: Hentikan runtime Google Colab lama Anda, atau tutup di https://dashboard.ngrok.com/endpoints")
            logger.error("!" * 70 + "\n")
            raise e1

        # Coba metode 2: domain / hostname fallback
        try:
            tunnel = ngrok.connect(PORT, "http", domain=NGROK_DOMAIN)
            public_url = tunnel.public_url
            tunnel_connected = True
        except Exception as e2:
            if "ERR_NGROK_334" in str(e2):
                logger.error("🚨 Sesi lama masih aktif di Colab. Tutup sesi Colab terlebih dahulu!")
                raise e2
            # Coba metode 3: subprocess CLI langsung
            logger.info("Mencoba menghubungkan via ngrok CLI langsung...")
            try:
                ngrok_bin = get_ngrok_bin()
                proc = subprocess.Popen(
                    [ngrok_bin, "http", str(PORT), f"--url={public_url}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                time.sleep(2)
                tunnel_connected = True
            except Exception as e3:
                logger.error(f"Koneksi tunnel gagal: {e3}")
                raise e3

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
        try:
            ngrok.disconnect(public_url)
            ngrok.kill()
        except Exception:
            pass
        print("✅ Server dan tunnel Ngrok berhasil ditutup.")

if __name__ == "__main__":
    start_server_with_ngrok()
