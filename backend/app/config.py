import os
import json
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
env_path = BASE_DIR / ".env"
if not env_path.exists():
    example_path = BASE_DIR / ".env.example"
    if example_path.exists():
        import shutil
        shutil.copy(example_path, env_path)

load_dotenv(dotenv_path=env_path)

class Settings:
    BASE_DIR: Path = BASE_DIR
    TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", str(BASE_DIR / "temp"))).resolve()
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs"))).resolve()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    COOKIES_FILE: Path = BASE_DIR / "cookies.txt"
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS
    cors_str = os.getenv("CORS_ORIGINS", '["http://localhost:3000","http://127.0.0.1:3000"]')
    try:
        CORS_ORIGINS = json.loads(cors_str)
    except Exception:
        CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Optimasi Kecepatan Eksekusi (GPU Kaggle & Multi-Core CPU)
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    WHISPER_CPU_THREADS: int = int(os.getenv("WHISPER_CPU_THREADS", "4"))
    WHISPER_BEAM_SIZE: int = int(os.getenv("WHISPER_BEAM_SIZE", "1"))
    FFMPEG_THREADS: int = int(os.getenv("FFMPEG_THREADS", "0"))  # 0 = gunakan semua thread CPU yang tersedia
    FFMPEG_PRESET: str = os.getenv("FFMPEG_PRESET", "ultrafast")  # ultrafast = render instan tanpa jeda

    def __init__(self):
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
