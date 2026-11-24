import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.models import WordTiming

logger = logging.getLogger("indoclip.subtitles")

# Definisi Warna Highlight Subtitle (Format BGR dalam sintaks ASS: &H00BBGGRR&)
SUBTITLE_COLORS = {
    "OPUS_GREEN": "&H0000FF66&",    # RGB #00FF66 -> BGR: 66, FF, 00 -> &H0066FF00&
    "SALMON_PINK": "&H007280FA&",   # RGB #FA8072 -> BGR: 72, 80, FA -> &H007280FA&
    "CYBER_YELLOW": "&H0000E6FF&",  # RGB #FFE600 -> BGR: 00, E6, FF -> &H0000E6FF&
}

def format_ass_time(seconds: float) -> str:
    """Format float seconds menjadi format timestamp ASS (H:MM:SS.cs)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hrs:d}:{mins:02d}:{secs:02d}.{cs:02d}"

def generate_ass_subtitle_file(
    words: List[WordTiming],
    output_path: Path,
    hook_banner: Optional[str] = None,
    color_scheme: str = "OPUS_GREEN",
    clip_start_offset: float = 0.0
) -> Path:
    """
    Menghasilkan file subtitle .ass dengan gaya OpusClip:
    - 2-4 kata per baris di area aman bawah (center-bottom).
    - Font tebal huruf kapital, outline hitam tebal + shadow.
    - Animasi kata aktif membesar 115% (\fscx115\fscy115) dan berubah warna.
    - 3-Second Hook Banner di bagian atas video pada detik 0.0 sampai 3.2.
    """
    highlight_color = SUBTITLE_COLORS.get(color_scheme.upper(), "&H0066FF00&")
    
    ass_header = f"""[Script Info]
Title: IndoClip Pro Animated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,6,3,2,40,40,240,1
Style: HookBanner,Montserrat ExtraBold,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H007280FA,-1,0,0,0,100,100,1,0,1,6,5,8,40,40,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogue_lines = []
    
    # 1. 3-Second Hook Overlay Banner
    if hook_banner and hook_banner.strip():
        clean_hook = hook_banner.strip().upper()
        # Banner muncul di detik 0.0 sampai 3.2
        start_hook = format_ass_time(0.0)
        end_hook = format_ass_time(3.2)
        # Efek kotak banner elegan dengan border salmon pink
        hook_text = f"{{\\fad(150,200)\\an8\\pos(540,160)\\bord5\\3c&H007280FA&\\1c&H00FFFFFF&\\shad3\\4c&H00000000&}}🔥 {clean_hook} 🔥"
        dialogue_lines.append(f"Dialogue: 1,{start_hook},{end_hook},HookBanner,,0,0,0,,{hook_text}")

    # 2. Opus-Style Animated Subtitles
    # Sesuaikan offset waktu kata ke awal klip (0.0 detik)
    normalized_words: List[Dict[str, Any]] = []
    for w in words:
        start_rel = max(0.0, w.start - clip_start_offset)
        end_rel = max(start_rel + 0.1, w.end - clip_start_offset)
        normalized_words.append({
            "word": w.word.strip().upper(),
            "start": start_rel,
            "end": end_rel
        })
        
    # Kelompokkan kata menjadi kelompok 2-4 kata per baris
    chunk_size = 3
    chunks = [normalized_words[i : i + chunk_size] for i in range(0, len(normalized_words), chunk_size)]
    
    for chunk in chunks:
        if not chunk:
            continue
            
        chunk_start = chunk[0]["start"]
        chunk_end = chunk[-1]["end"]
        
        # Untuk setiap kata aktif di dalam chunk, buat event animasi aktif
        for active_idx, active_word in enumerate(chunk):
            w_start = format_ass_time(active_word["start"])
            w_end = format_ass_time(active_word["end"])
            
            # Bentuk teks baris dengan kata aktif membesar 115% dan berwarna highlight
            formatted_words = []
            for idx, item in enumerate(chunk):
                w_str = item["word"]
                if idx == active_idx:
                    # Active Word: Warna highlight + skala 115%
                    formatted_words.append(
                        f"{{\\c{highlight_color}\\fscx115\\fscy115\\bord7\\3c&H00000000&}}{w_str}{{\\r}}"
                    )
                else:
                    # Inactive Word: Putih standar
                    formatted_words.append(
                        f"{{\\c&H00FFFFFF&\\fscx100\\fscy100\\bord6\\3c&H00000000&}}{w_str}{{\\r}}"
                    )
                    
            line_content = " ".join(formatted_words)
            dialogue_lines.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{line_content}")
            
    full_content = ass_header + "\n".join(dialogue_lines) + "\n"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)
        
    logger.info(f"Generated ASS subtitle file: {output_path.name} with {len(dialogue_lines)} events.")
    return output_path
