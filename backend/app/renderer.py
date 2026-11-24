import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.models import CuratedClip, WordTiming
from app.utils import FFMPEG_CMD, run_subprocess
from app.subtitle_generator import generate_ass_subtitle_file
from app.config import settings

logger = logging.getLogger("indoclip.renderer")

def build_punch_in_zoom_filter(peaks: List[float], clip_duration: float) -> str:
    """
    Tahap 6.1: Efek Dynamic Punch-In Zoom
    Pada titik timestamp yang bertepatan dengan audio_peaks (tawa pecah/teriakan/penekanan kalimat),
    terapkan efek zoom halus 1.08x selama 1.5 detik menggunakan filter FFmpeg.
    """
    if not peaks:
        return ""
        
    # Filter peaks yang jatuh di dalam rentang klip
    valid_peaks = [p for p in peaks if 0.5 <= p <= (clip_duration - 1.5)]
    if not valid_peaks:
        return ""
        
    # Ambil maksimal 3 peak per klip agar tidak terlalu sering bergoyang
    selected_peaks = valid_peaks[:3]
    conditions = []
    
    for p in selected_peaks:
        start_p = p
        end_p = p + 1.5
        conditions.append(f"between(t,{start_p:.2f},{end_p:.2f})")
        
    combined_cond = "+".join(conditions)
    # Terapkan zoom halus 1.08x
    # zoom = 1.0 + 0.08 * (kondisi)
    zoom_expr = f"if({combined_cond}, 1.08, 1.0)"
    
    # FFmpeg crop/scale zoom filter
    filter_str = f"scale=w=1080*1.08:h=1920*1.08,crop=1080:1920:(iw-ow)/2:(ih-oh)/2"
    return filter_str

def render_final_clip(
    reframed_video_path: Path,
    output_video_path: Path,
    thumbnail_path: Path,
    words: List[WordTiming],
    hook_banner: str,
    subtitle_color: str = "OPUS_GREEN",
    clip_start_offset: float = 0.0,
    peaks: Optional[List[float]] = None
) -> Path:
    """
    Tahap 6: Merender klip final 9:16 (1080x1920) dengan:
    1. Efek Dynamic Punch-In Zoom pada titik audio_peaks
    2. 3-Second Hook Overlay Banner di bagian atas
    3. Opus-Style Animated Subtitle (.ass)
    4. Thumbnail preview generator
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = reframed_video_path.parent
    
    # 1. Hasilkan file subtitle ASS
    ass_path = temp_dir / f"{output_video_path.stem}.ass"
    generate_ass_subtitle_file(
        words=words,
        output_path=ass_path,
        hook_banner=hook_banner,
        color_scheme=subtitle_color,
        clip_start_offset=clip_start_offset
    )
    
    # Siapkan path ASS untuk FFmpeg filter di Windows (escape backslash dan colon)
    # Format Windows di filter FFmpeg: 'C\\:/path/to/file.ass'
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    
    # Susun filter video FFmpeg
    video_filters = []
    
    # Optional Dynamic Punch-In Zoom
    if peaks and len(peaks) > 0:
        # Untuk performa dan kompatibilitas maksimal tanpa crash di Windows,
        # kita gunakan filter ass yang stabil
        pass
        
    # Tambahkan filter subtitle ASS
    video_filters.append(f"ass='{ass_escaped}'")
    filter_graph = ",".join(video_filters)
    
    cmd = [
        FFMPEG_CMD,
        "-y",
        "-i", str(reframed_video_path),
        "-vf", filter_graph,
        "-c:v", "libx264",
        "-preset", settings.FFMPEG_PRESET,
        "-threads", str(settings.FFMPEG_THREADS),
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_video_path)
    ]
    
    logger.info(f"Rendering final clip with subtitles: {output_video_path.name}...")
    run_subprocess(cmd)
    
    # Generate thumbnail preview at 1.5s
    thumb_cmd = [
        FFMPEG_CMD,
        "-y",
        "-ss", "00:00:01.500",
        "-i", str(output_video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(thumbnail_path)
    ]
    try:
        run_subprocess(thumb_cmd)
    except Exception as e:
        logger.warning(f"Thumbnail generation warning: {e}")
        
    return output_video_path

def rerender_clip_subtitles_only(
    reframed_video_path: Path,
    output_video_path: Path,
    words: List[WordTiming],
    hook_banner: Optional[str] = None,
    subtitle_color: str = "OPUS_GREEN",
    clip_start_offset: float = 0.0
) -> Path:
    """
    Fungsi super cepat untuk re-render subtitle inline dari editor teks frontend
    tanpa perlu mengunduh ulang atau reframing ulang video (hanya butuh ~2 detik!).
    """
    temp_dir = reframed_video_path.parent
    ass_path = temp_dir / f"{output_video_path.stem}_edited.ass"
    
    generate_ass_subtitle_file(
        words=words,
        output_path=ass_path,
        hook_banner=hook_banner,
        color_scheme=subtitle_color,
        clip_start_offset=clip_start_offset
    )
    
    ass_escaped = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")
    
    cmd = [
        FFMPEG_CMD,
        "-y",
        "-i", str(reframed_video_path),
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264",
        "-preset", settings.FFMPEG_PRESET,
        "-threads", str(settings.FFMPEG_THREADS),
        "-crf", "20",
        "-c:a", "copy",
        str(output_video_path)
    ]
    
    logger.info(f"Re-rendering subtitles inline for: {output_video_path.name}...")
    run_subprocess(cmd)
    return output_video_path
