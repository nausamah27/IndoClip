import os
import logging
from pathlib import Path
from typing import Tuple
import yt_dlp

from app.models import CuratedClip
from app.utils import FFMPEG_CMD, run_subprocess
from app.config import settings

logger = logging.getLogger("indoclip.downloader")

def download_partial_video(
    youtube_url: str,
    clip: CuratedClip,
    clip_index: int,
    output_dir: Path
) -> Tuple[Path, float, float]:
    """
    Tahap 4: Unduh hanya bagian video pada rentang (start_time - 1.5s) hingga (end_time + 1.5s)
    resolusi 1080p menggunakan yt-dlp --download-sections.
    
    Mengembalikan: (path_raw_video, relative_start_sec, relative_end_sec)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_video_path = output_dir / f"clip_{clip_index}_raw.mp4"
    
    # Tambahkan padding 1.5 detik sebelum dan sesudah agar tidak terpotong
    start_pad = max(0.0, clip.start_time - 1.5)
    end_pad = clip.end_time + 1.5
    
    # Hitung posisi relatif klip di dalam file yang sudah diunduh
    relative_start = clip.start_time - start_pad
    relative_end = relative_start + (clip.end_time - clip.start_time)
    
    section_arg = f"*{start_pad:.2f}-{end_pad:.2f}"
    logger.info(f"Downloading partial video section {section_arg} for clip #{clip_index}...")
    
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'outtmpl': str(raw_video_path),
        'download_ranges': yt_dlp.utils.download_range_func(None, [(start_pad, end_pad)]),
        'force_keyframes_at_cuts': True,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
        'overwrites': True,
        'concurrent_fragment_downloads': 5,
        'buffersize': 1024 * 1024
    }
    
    if settings.COOKIES_FILE.exists():
        ydl_opts['cookiefile'] = str(settings.COOKIES_FILE)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        if not raw_video_path.exists() or raw_video_path.stat().st_size == 0:
            raise FileNotFoundError("File hasil download_ranges kosong.")
    except Exception as e:
        logger.warning(f"Direct download_ranges failed ({e}). Trying CLI fallback...")
        cmd = [
            "yt-dlp",
            "--download-sections", section_arg,
            "--force-keyframes-at-cuts",
            "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format", "mp4",
            "-o", str(raw_video_path),
            "--no-playlist",
            "--force-overwrites"
        ]
        if settings.COOKIES_FILE.exists():
            cmd.extend(["--cookies", str(settings.COOKIES_FILE)])
        cmd.append(youtube_url)
        run_subprocess(cmd)
        
    if not raw_video_path.exists() or raw_video_path.stat().st_size == 0:
        raise FileNotFoundError(f"Gagal mengunduh bagian video untuk klip #{clip_index}")
        
    logger.info(f"Partial video downloaded: {raw_video_path.name} ({relative_end - relative_start:.1f}s effective)")
    return raw_video_path, relative_start, relative_end
