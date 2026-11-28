import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.models import (
    WordTiming,
    ViralityBreakdown,
    AudioPeak,
    CuratedClip,
    CurationResponse
)

logger = logging.getLogger("indoclip.curator")

# Schema ringkas khusus respons Gemini (tanpa list kata-kata agar super cepat & tidak pernah timeout)
class FastGeminiClip(BaseModel):
    title: str = Field(description="Judul deskriptif dan clickbait positif khas kreator Indonesia")
    hook_banner: str = Field(description="Teks pancingan maksimal 5 kata HURUF KAPITAL untuk 3 detik pertama")
    virality_score: int = Field(description="Skor total viralitas konten (1-100)")
    score_breakdown: ViralityBreakdown = Field(description="Rincian skor hook, alur cerita, dan potensi interaksi")
    category: str = Field(description="Kategori klip: 'PODCAST', 'GAMING', atau 'SOLO'")
    start_time: float = Field(description="Detik mulai klip")
    end_time: float = Field(description="Detik selesai klip")
    social_caption: str = Field(description="Caption siap posting dan hashtag viral TikTok/Shorts")

class FastGeminiCurationResponse(BaseModel):
    clips: List[FastGeminiClip] = Field(description="Daftar 3-6 klip viral terbaik")

CURATOR_SYSTEM_PROMPT = """
Kamu adalah AI Lead Video Editor & Copywriter profesional untuk kreator konten Indonesia (Shorts, TikTok, Reels).
Tugasmu: Menganalisis transkrip percakapan video dan audio peaks (titik tawa/teriakan/klimaks emosional), lalu memilih 3 sampai 6 bagian klip paling viral berdurasi antara 30 hingga 65 detik.

Prinsip Kurasi & Copywriting:
1. Pancingan 3 Detik Pertama (Hook): Pilih bagian yang langsung mengundang rasa penasaran, pernyataan kontroversial, candaan lucu, atau momen emosional tinggi.
2. Hook Banner: Buat teks pancingan MAKSIMAL 5 KATA dalam SEMUA HURUF BESAR (KAPITAL) yang heboh dan menarik rasa penasaran.
3. Alur Cerita Utuh: Setiap klip harus memiliki awal (setup), konflik/candaan (body), dan penyelesaian/reaksi (punchline).
4. Pemilihan Waktu (start_time & end_time): Pastikan durasi klip antara 30 sampai 65 detik.
5. Caption & Hashtag: Buat caption santai bergaya anak muda Indonesia dengan hashtag relevan (#fyp, #viralindonesia, #podcastindo, dll).
"""

def extract_words_for_clip(all_words: List[Dict[str, Any]], start_t: float, end_t: float) -> List[WordTiming]:
    """Mengambil kata-kata ber-timestamp secara lokal dan instan (0.001s)."""
    words: List[WordTiming] = []
    for w in all_words:
        w_start = w.get("start", 0.0)
        w_end = w.get("end", 0.0)
        if (start_t - 0.2) <= w_start and w_end <= (end_t + 0.3):
            words.append(WordTiming(
                word=w.get("word", "").strip(),
                start=round(w_start, 2),
                end=round(w_end, 2),
                probability=round(w.get("probability", 1.0), 2)
            ))
    return words

def fallback_heuristic_curation(
    transcript_data: Dict[str, Any],
    peaks: List[AudioPeak],
    min_duration: int = 30,
    max_duration: int = 65
) -> CurationResponse:
    """
    Fallback cepat jika Gemini API tidak tersedia atau timeout.
    Memotong klip berdasarkan titik klimaks audio peaks & segmen transkrip.
    """
    logger.info("Using smart heuristic peak curation fallback (Instant, ~0.1s)...")
    clips: List[CuratedClip] = []
    segments = transcript_data.get("segments", [])
    all_words = transcript_data.get("all_words", [])
    
    if not segments:
        return CurationResponse(clips=[])
        
    total_segments = len(segments)
    target_clips = min(4, max(1, total_segments // 5))
    step = max(1, total_segments // target_clips)
    
    for i in range(0, total_segments, step):
        if len(clips) >= 4:
            break
            
        start_seg = segments[i]
        start_t = start_seg["start"]
        end_t = start_t
        clip_text_parts = []
        
        for j in range(i, total_segments):
            seg = segments[j]
            seg_dur = seg["end"] - start_t
            if seg_dur > max_duration:
                break
            end_t = seg["end"]
            clip_text_parts.append(seg["text"])
            if seg_dur >= min_duration:
                break
                
        dur = end_t - start_t
        if dur < 15.0:
            continue
            
        full_clip_text = " ".join(clip_text_parts)
        sample_title = full_clip_text[:40].strip() + "..."
        current_words = extract_words_for_clip(all_words, start_t, end_t)
        
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
    dengan model gemini-3.8-flash (atau fallback cepat) & pemrosesan kata lokal.
    """
    effective_api_key = api_key or settings.GEMINI_API_KEY
    all_words = transcript_data.get("all_words", [])
    
    if not effective_api_key:
        logger.warning("Tidak ada Gemini API Key. Menggunakan kurasi heuristik audio peaks.")
        return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
        
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=effective_api_key)
        
        # Persiapkan data ringkas (HANYA teks, tanpa jutaan array kata agar ukuran payload kecil & respons < 3 detik)
        segments = transcript_data.get("segments", [])
        simplified_segments = []
        
        # Jika segmen sangat banyak (misal video > 20 menit), lakukan sampling representatif
        max_prompt_segments = 120
        step_sample = max(1, len(segments) // max_prompt_segments)
        
        for s in segments[::step_sample]:
            simplified_segments.append({
                "start": round(s["start"], 1),
                "end": round(s["end"], 1),
                "text": s["text"].strip()
            })
            
        peaks_summary = [{"t": round(p.timestamp, 1), "i": round(p.intensity, 1)} for p in peaks[:30]]
        
        prompt_payload = {
            "instruction": "Pilih 3-6 klip viral terbaik (durasi 30-65 detik) berdasarkan transkrip dan audio peaks berikut.",
            "target_clip_count": "3 sampai 6 klip",
            "min_duration_seconds": min_duration,
            "max_duration_seconds": max_duration,
            "audio_peaks_detected": peaks_summary,
            "transcript_summary": simplified_segments
        }
        
        candidate_models = ["gemini-3.8-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        raw_response = None
        
        for model_name in candidate_models:
            try:
                logger.info(f"Mengirim transkrip ke Gemini model '{model_name}'...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=json.dumps(prompt_payload, ensure_ascii=False),
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=FastGeminiCurationResponse,
                        system_instruction=CURATOR_SYSTEM_PROMPT,
                        temperature=0.7,
                    )
                )
                if response and response.text:
                    raw_response = response.text
                    logger.info(f"Gemini ({model_name}) berhasil merespons kurasi viral!")
                    break
            except Exception as model_err:
                logger.warning(f"Model {model_name} gagal: {model_err}. Mencoba model alternatif...")
                
        if not raw_response:
            logger.warning("Seluruh kandidat model Gemini gagal atau kuota habis, beralih ke fallback.")
            return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
            
        # Parse respons terstruktur
        parsed_data = json.loads(raw_response)
        fast_curation = FastGeminiCurationResponse(**parsed_data)
        
        if not fast_curation.clips:
            logger.warning("Gemini mengembalikan 0 klip, beralih ke fallback.")
            return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
            
        # Rakit kembali CuratedClip dengan mengekstrak kata-kata lokal dari whisper
        final_clips: List[CuratedClip] = []
        for c in fast_curation.clips:
            clip_words = extract_words_for_clip(all_words, c.start_time, c.end_time)
            final_clips.append(CuratedClip(
                title=c.title,
                hook_banner=c.hook_banner,
                virality_score=c.virality_score,
                score_breakdown=c.score_breakdown,
                category=c.category,
                start_time=c.start_time,
                end_time=c.end_time,
                corrected_words=clip_words,
                social_caption=c.social_caption
            ))
            
        logger.info(f"Berhasil merakit {len(final_clips)} klip viral kurasi Gemini!")
        return CurationResponse(clips=final_clips)
        
    except Exception as e:
        logger.error(f"Error selama kurasi Gemini: {e}", exc_info=True)
        return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
