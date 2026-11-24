import os
import sys
import shutil
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger("indoclip.utils")

def ensure_ffmpeg() -> Tuple[str, str]:
    """
    Memastikan binary ffmpeg dan ffprobe tersedia.
    Jika belum ada di PATH Windows, lakukan auto-detect pada direktori WinGet Gyan.FFmpeg
    dan tambahkan ke PATH runtime.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    
    if ffmpeg_bin and ffprobe_bin:
        return ffmpeg_bin, ffprobe_bin

    # Cari di direktori WinGet Gyan.FFmpeg umum di Windows
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    user_profile = os.environ.get("USERPROFILE", "")
    
    search_dirs = [
        Path(local_app_data) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ProgramData/chocolatey/bin"),
        Path("C:/ffmpeg/bin"),
        Path(user_profile) / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links",
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for ffmpeg_candidate in search_dir.glob("**/ffmpeg.exe"):
                bin_dir = ffmpeg_candidate.parent
                ffprobe_candidate = bin_dir / "ffprobe.exe"
                if ffprobe_candidate.exists():
                    os.environ["PATH"] = f"{bin_dir};{os.environ['PATH']}"
                    logger.info(f"Auto-configured FFmpeg PATH: {bin_dir}")
                    return str(ffmpeg_candidate), str(ffprobe_candidate)

    # Fallback to names in PATH
    return "ffmpeg", "ffprobe"

FFMPEG_CMD, FFPROBE_CMD = ensure_ffmpeg()

def run_subprocess(cmd: list, check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Jalankan command subprocess dengan logging yang aman di Windows."""
    logger.debug(f"Running subprocess: {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(
        cmd,
        check=check,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result

def get_video_duration(video_path: str) -> float:
    """Mengambil durasi video via ffprobe."""
    try:
        cmd = [
            FFPROBE_CMD,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = run_subprocess(cmd)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Failed to get video duration: {e}")
        return 0.0

def get_video_dimensions(video_path: str) -> Tuple[int, int]:
    """Mengambil resolusi (width, height) video via ffprobe."""
    try:
        cmd = [
            FFPROBE_CMD,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            video_path
        ]
        result = run_subprocess(cmd)
        parts = result.stdout.strip().split("x")
        return int(parts[0]), int(parts[1])
    except Exception as e:
        logger.warning(f"Failed to get video dimensions: {e}")
        return 1920, 1080

def clean_directory(dir_path: Path):
    """Menghapus isi direktori tanpa menghapus foldernya."""
    if not dir_path.exists():
        return
    for item in dir_path.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        except Exception as e:
            logger.warning(f"Could not delete {item}: {e}")
