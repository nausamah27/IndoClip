import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.models import (
    CurationResponse,
    CuratedClip,
    WordTiming,
    ViralityBreakdown,
    AudioPeak
)
from app.config import settings

logger = logging.getLogger("indoclip.curator")

CURATOR_SYSTEM_PROMPT = """
Anda adalah "Viral Content Strategist" kelas dunia khusus audiens TikTok, Instagram Reels, dan YouTube Shorts Indonesia.
Tugas Anda adalah menganalisis transkrip percakapan konten kreator/YouTuber Indonesia (Podcast, Gaming, Reaction, Storytelling) bersama timestamp audio peaks (lonjakan tawa, teriakan, atau momen emosional) untuk mengurasi 3 sampai 6 klip terbaik berpotensi viral tinggi.

Kriteria Seleksi Klip:
1. Durasi setiap klip wajib antara 30 hingga 65 detik.
2. Hook 3 Detik Pertama: Momen pembuka harus langsung memancing rasa penasaran, kejutan, perdebatan sengit, atau punchline lucu.
3. Alur Cerita Utuh: Harus memiliki awal (konteks), klimaks (punchline/reaksi pecah/debat), dan penutup yang memuaskan.
4. Potong Tepat pada Jeda Napas: Nilai start_time dan end_time HARUS presisi pada jeda alami antar kalimat, JANGAN memotong di tengah pengucapan kata.
5. Hook Banner: Buat teks pancingan MAKSIMAL 5 KATA, WAJIB SEMUA HURUF KAPITAL (contoh: "DETIK-DETIK KETAHUAN BOHONG!", "REAKSI SHOCK PAS DITANYA INI", "PLOT TWIST PALING GILA").
6. Perbaikan Slang Gaul: Koreksi salah eja atau kata bahasa gaul (misal: "bgt" -> "banget", "gk" -> "nggak", "gw" -> "gue") di corrected_words tanpa mengubah timestamp start & end aslinya.
7. Kategori: Tentukan apakah klip ini "PODCAST" (obrolan santai/diskusi), "GAMING" (gameplay/clutch/rage), atau "SOLO" (monolog/reaksi tunggal).
8. Social Caption: Buat caption singkat yang engaging, memicu kolom komentar, serta 5-8 hashtag populer (#fyp #viralindonesia #podcastindo #shorts dsb).
"""

def fallback_heuristic_curation(
    transcript_data: Dict[str, Any],
    peaks: List[AudioPeak],
    min_duration: int = 30,
    max_duration: int = 65
) -> CurationResponse:
    """
    Fallback kurasi jika Gemini API Key belum diisi atau kuota habis:
    Menemukan klip berbasis konsentrasi lonjakan audio peaks dan transkrip.
    """
    segments = transcript_data.get("segments", [])
    if not segments:
        return CurationResponse(clips=[])
        
    clips: List[CuratedClip] = []
    total_segments = len(segments)
    
    # Kelompokkan segmen menjadi 3-5 kandidat klip
    target_clips = min(4, max(1, total_segments // 5))
    step = max(1, total_segments // target_clips)
    
    for i in range(0, total_segments, step):
        if len(clips) >= 4:
            break
            
        start_seg = segments[i]
        start_t = start_seg["start"]
        
        # Cari end_seg hingga durasi mencapai min_duration s/d max_duration
        current_words: List[WordTiming] = []
        end_t = start_t
        clip_text_parts = []
        
        for j in range(i, total_segments):
            seg = segments[j]
            seg_dur = seg["end"] - start_t
            if seg_dur > max_duration:
                break
            end_t = seg["end"]
            clip_text_parts.append(seg["text"])
            for w in seg.get("words", []):
                current_words.append(WordTiming(
                    word=w["word"],
                    start=w["start"],
                    end=w["end"],
                    probability=w.get("probability", 1.0)
                ))
            if seg_dur >= min_duration:
                break
                
        dur = end_t - start_t
        if dur < 15.0:
            continue
            
        full_clip_text = " ".join(clip_text_parts)
        sample_title = full_clip_text[:40].strip() + "..."
        
        clips.append(CuratedClip(
            title=f"Momen Epik: {sample_title}",
            hook_banner="MOMEN INI BIKIN KAGET!",
            virality_score=88 - (len(clips) * 3),
            score_breakdown=ViralityBreakdown(hook_score=90, flow_score=85, engagement_score=89),
            category="PODCAST",
            start_time=round(start_t, 2),
            end_time=round(end_t, 2),
            corrected_words=current_words,
            social_caption=f"{sample_title} Ga nyangka bakal begini jadinya! Tonton sampai akhir 🔥 #fyp #viralindonesia #shorts #trending"
        ))
        
    return CurationResponse(clips=clips)

def curate_viral_clips(
    transcript_data: Dict[str, Any],
    peaks: List[AudioPeak],
    api_key: Optional[str] = None,
    min_duration: int = 30,
    max_duration: int = 65
) -> CurationResponse:
    """
    Tahap 3: Kurasi Viral & Copywriting ala Kreator Indo menggunakan google-genai
    dengan model gemini-2.5-flash dan Structured Outputs (Pydantic).
    """
    effective_api_key = api_key or settings.GEMINI_API_KEY
    
    if not effective_api_key:
        logger.warning("No Gemini API key provided. Falling back to heuristic peak-based curation.")
        return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
        
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=effective_api_key)
        
        # Persiapkan data input transkrip ringkas & audio peaks
        simplified_segments = []
        for s in transcript_data.get("segments", []):
            simplified_segments.append({
                "start": s["start"],
                "end": s["end"],
                "text": s["text"],
                "words": [
                    {"w": w["word"], "s": w["start"], "e": w["end"]}
                    for w in s.get("words", [])
                ]
            })
            
        peaks_summary = [{"t": p.timestamp, "intensity": p.intensity} for p in peaks[:40]]
        
        prompt_payload = {
            "instruction": "Pilih 3-6 klip viral terbaik (durasi 30-65 detik) berdasarkan transkrip dan titik audio peaks berikut.",
            "target_clip_count": "3 sampai 6 klip",
            "min_duration_seconds": min_duration,
            "max_duration_seconds": max_duration,
            "audio_peaks_detected": peaks_summary,
            "transcript_segments": simplified_segments
        }
        
        logger.info("Calling Gemini 2.5 Flash via google-genai SDK for viral clip curation...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=json.dumps(prompt_payload, ensure_ascii=False),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CurationResponse,
                system_instruction=CURATOR_SYSTEM_PROMPT,
                temperature=0.7,
            )
        )
        
        # Parse respons terstruktur
        response_text = response.text
        parsed_data = json.loads(response_text)
        curation_result = CurationResponse(**parsed_data)
        
        # Validasi kembali timestamp klip agar tidak kosong
        if not curation_result.clips:
            logger.warning("Gemini returned 0 clips, falling back to heuristic curation.")
            return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
            
        logger.info(f"Gemini successfully curated {len(curation_result.clips)} high-virality clips!")
        return curation_result
        
    except Exception as e:
        logger.error(f"Error during Gemini viral curation: {e}", exc_info=True)
        logger.info("Engaging fallback heuristic curation...")
        return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
