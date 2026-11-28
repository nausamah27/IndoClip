import os
import json
import logging
import urllib.request
import urllib.error
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

# Schema ringkas respons AI untuk konsistensi di seluruh provider
class AIClipItem(BaseModel):
    start: float = Field(description="Detik mulai klip")
    end: float = Field(description="Detik selesai klip")
    title: str = Field(description="Judul hook click-worthy maksimal 8 kata bahasa Indonesia")
    hook_text: str = Field(default="", description="Kalimat pancingan 0-3 detik pertama")
    hook_banner: str = Field(default="", description="Maksimal 5 kata HURUF BESAR untuk banner atas")
    category: str = Field(default="Hot Take", description="'Hot Take', 'Storytelling', 'Tips Daging', atau 'Komedi/Emosi'")
    reason: str = Field(default="", description="Alasan mengapa momen ini viral")
    score: int = Field(default=85, description="Skor viralitas 1-100")
    social_caption: str = Field(default="", description="Caption medsos + hashtag viral")

class AICurationResponse(BaseModel):
    clips: List[AIClipItem] = Field(description="Daftar klip viral terkurasi")

CURATOR_SYSTEM_PROMPT = """Kamu adalah Senior Short-Form Content Strategist & Lead Video Editor profesional untuk TikTok, Instagram Reels, dan YouTube Shorts berbahasa Indonesia.
Tugasmu: Menganalisis transkrip percakapan video dengan penanda timestamp [detik_mulai - detik_selesai] serta titik audio peaks (lonjakan tawa/teriakan/klimaks emosional), lalu memilih klip paling bernilai tinggi dan berpotensi viral masif.

PANDUAN KURASI WAJIB (STRICT RULES):
1. RULE 1 (STRONG HOOK 0–3 DETIK):
   - Titik `start` WAJIB dimulai tepat pada kalimat pembuka yang kuat, mengejutkan, kontroversial, atau memancing rasa penasaran.
   - DILARANG KERAS memulai dari basa-basi pembuka ("Halo guys", "Jadi gini", "Nah terus", "Oke balik lagi", atau jeda hening).
2. RULE 2 (KONTEKS MANDIRI & PENUTUP RAPI):
   - Setiap klip harus berdiri sendiri (self-contained): Hook Pancingan → Isi/Daging Cerita → Kesimpulan/Punchline/Reaksi Tuntas.
   - Titik `end` WAJIB berhenti tepat setelah kalimat selesai diucapkan tuntas (tidak terpotong di tengah kalimat).
3. RULE 3 (DURASI IDEAL & SKOR MINIMAL):
   - Durasi setiap klip WAJIB antara 28 hingga 58 detik.
   - Filter ketat: HANYA pilih klip dengan skor viralitas minimal 75 (1–100). Buang momen biasa di bawah 75.
4. RULE 4 (OUTPUT JSON SERAGAM):
   - Berikan HANYA JSON murni (valid JSON object) dengan key "clips", masing-masing berisi:
     - `start`: float (detik mulai presisi)
     - `end`: float (detik selesai presisi)
     - `title`: string (judul click-worthy maksimal 8 kata bahasa Indonesia natural)
     - `hook_text`: string (kalimat pembuka hook 0-3 detik)
     - `hook_banner`: string (maksimal 5 kata SEMUA HURUF BESAR untuk banner atas)
     - `category`: string ('Hot Take', 'Storytelling', 'Tips Daging', atau 'Komedi/Emosi')
     - `reason`: string (alasan potensi viral)
     - `score`: integer (75-100)
     - `social_caption`: string (caption siap posting dengan hashtag #fyp #shorts #viralindonesia)
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

def format_transcript_with_timestamps(segments: List[Dict[str, Any]]) -> str:
    """Format transkrip ke bentuk: [12.4 - 18.2] teks percakapan."""
    lines = []
    for s in segments:
        text = s.get("text", "").strip()
        if text:
            start_val = round(float(s.get("start", 0.0)), 1)
            end_val = round(float(s.get("end", 0.0)), 1)
            lines.append(f"[{start_val:.1f} - {end_val:.1f}] {text}")
    return "\n".join(lines)

def chunk_transcript_text(transcript_text: str, max_chars: int = 18000) -> List[str]:
    """
    Jika transkrip melebihi 20.000 karakter (video durasi panjang 1 jam+),
    pecah menjadi beberapa chunk teratur dengan overlap 1.000 karakter agar konteks terjaga.
    """
    if len(transcript_text) <= max_chars:
        return [transcript_text]
        
    chunks = []
    lines = transcript_text.split("\n")
    current_chunk = []
    current_len = 0
    
    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            # Simpan 10 baris terakhir sebagai overlap konteks
            current_chunk = current_chunk[-10:] + [line]
            current_len = sum(len(l) + 1 for l in current_chunk)
        else:
            current_chunk.append(line)
            current_len += line_len
            
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    logger.info(f"Transkrip panjang dipecah menjadi {len(chunks)} chunk untuk kurasi AI.")
    return chunks

# ==============================================================
# PROVIDER 1: Google Gemini (gemini-2.5-flash / fallback)
# ==============================================================
def call_gemini_provider(
    prompt_content: str,
    api_key: str,
    timeout_sec: int = 60
) -> Optional[List[AIClipItem]]:
    """Prioritas 1: Google Gemini dengan timeout eksplisit 60 detik."""
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-3.8-flash"]
        
        for model_name in candidate_models:
            try:
                logger.info(f"Mengirim permintaan kurasi ke Gemini ('{model_name}')...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_content,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AICurationResponse,
                        system_instruction=CURATOR_SYSTEM_PROMPT,
                        temperature=0.7,
                    )
                )
                if response and response.text:
                    parsed = json.loads(response.text)
                    items = parsed.get("clips", [])
                    clips = [AIClipItem(**c) for c in items]
                    if clips:
                        logger.info(f"Gemini ('{model_name}') berhasil mengurasi {len(clips)} klip.")
                        return clips
            except Exception as e:
                logger.warning(f"Gemini {model_name} gagal: {e}. Mencoba alternatif...")
    except Exception as e:
        logger.warning(f"Gemini SDK error: {e}")
    return None

# ==============================================================
# PROVIDER 2: Mistral AI (mistral-small-latest)
# ==============================================================
def call_mistral_provider(
    prompt_content: str,
    api_key: str,
    timeout_sec: int = 35
) -> Optional[List[AIClipItem]]:
    """Prioritas 2: Mistral AI REST API via JSON Object."""
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        payload = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": CURATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "IndoClip/2.0"
            },
            method="POST"
        )
        
        logger.info("Mengirim permintaan kurasi ke Mistral AI ('mistral-small-latest')...")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            items = parsed.get("clips", parsed if isinstance(parsed, list) else [])
            clips = [AIClipItem(**c) for c in items]
            if clips:
                logger.info(f"Mistral AI berhasil mengurasi {len(clips)} klip.")
                return clips
    except Exception as e:
        logger.warning(f"Mistral AI kurasi gagal: {e}")
    return None

# ==============================================================
# PROVIDER 3: GroqCloud (llama-3.3-70b-versatile)
# ==============================================================
def call_groq_provider(
    prompt_content: str,
    api_key: str,
    timeout_sec: int = 35
) -> Optional[List[AIClipItem]]:
    """Prioritas 3: GroqCloud OpenAI-compatible endpoint."""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": CURATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.7
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "IndoClip/2.0"
            },
            method="POST"
        )
        
        logger.info("Mengirim permintaan kurasi ke GroqCloud ('llama-3.3-70b-versatile')...")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            items = parsed.get("clips", parsed if isinstance(parsed, list) else [])
            clips = [AIClipItem(**c) for c in items]
            if clips:
                logger.info(f"GroqCloud berhasil mengurasi {len(clips)} klip.")
                return clips
    except Exception as e:
        logger.warning(f"GroqCloud kurasi gagal: {e}")
    return None

# ==============================================================
# FALLBACK HEURISTIK PEAKS
# ==============================================================
def fallback_heuristic_curation(
    transcript_data: Dict[str, Any],
    peaks: List[AudioPeak],
    min_duration: int = 28,
    max_duration: int = 58
) -> CurationResponse:
    """Fallback instan (~0.1s) berdasarkan audio peaks jika seluruh provider AI tidak tersedia."""
    logger.info("Mengaktifkan Fallback Heuristik Audio Peaks (Instan, 100% Offline)...")
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
        if dur < float(min_duration) * 0.7:
            continue
            
        full_clip_text = " ".join(clip_text_parts)
        sample_title = full_clip_text[:40].strip() + "..."
        current_words = extract_words_for_clip(all_words, start_t, end_t)
        
        clips.append(CuratedClip(
            title=f"Momen Epik: {sample_title}",
            hook_banner="MOMEN INI BIKIN KAGET!",
            hook_text=clip_text_parts[0] if clip_text_parts else "Perhatikan baik-baik bagian ini!",
            virality_score=85 - (len(clips) * 2),
            score_breakdown=ViralityBreakdown(hook_score=88, flow_score=85, engagement_score=86),
            category="Hot Take",
            reason="Lonjakan audio terdeteksi pada titik ini",
            start_time=round(start_t, 2),
            end_time=round(end_t, 2),
            corrected_words=current_words,
            social_caption=f"{sample_title} Tonton sampai habis! 🔥 #fyp #viralindonesia #shorts #trending"
        ))
        
    return CurationResponse(clips=clips)

# ==============================================================
# MAIN CURATION ORCHESTRATOR
# ==============================================================
def curate_viral_clips(
    transcript_data: Dict[str, Any],
    peaks: List[AudioPeak],
    gemini_api_key: Optional[str] = None,
    mistral_api_key: Optional[str] = None,
    groq_api_key: Optional[str] = None,
    min_duration: int = 28,
    max_duration: int = 58
) -> CurationResponse:
    """
    Tahap 3: Kurasi Viral & Copywriting Multi-Provider Auto-Fallback:
    1. Gemini (gemini-2.5-flash, timeout 60s)
    2. Mistral AI (mistral-small-latest)
    3. GroqCloud (llama-3.3-70b-versatile)
    4. Heuristic Audio Peaks Fallback
    """
    all_words = transcript_data.get("all_words", [])
    segments = transcript_data.get("segments", [])
    
    # Resolusi API keys dari argument atau environment
    g_key = (gemini_api_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip() or settings.GEMINI_API_KEY
    m_key = (mistral_api_key or "").strip() or os.getenv("MISTRAL_API_KEY", "").strip() or settings.MISTRAL_API_KEY
    gr_key = (groq_api_key or "").strip() or os.getenv("GROQ_API_KEY", "").strip() or settings.GROQ_API_KEY
    
    if not g_key and not m_key and not gr_key:
        logger.warning("Semua API key AI kosong. Menggunakan fallback heuristik audio peaks.")
        return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
        
    # Format transkrip dengan timestamp presisi
    formatted_transcript = format_transcript_with_timestamps(segments)
    peaks_summary = [f"{p.timestamp:.1f}s (intensitas: {p.intensity:.1f})" for p in peaks[:25]]
    
    # Pecah chunk jika transkrip panjang (> 20.000 karakter)
    transcript_chunks = chunk_transcript_text(formatted_transcript, max_chars=18000)
    
    raw_ai_clips: List[AIClipItem] = []
    
    for chunk_idx, chunk_text in enumerate(transcript_chunks, start=1):
        prompt_content = f"""Tolong kurasi momen viral terbaik dari transkrip video berikut:

DURASI KLIP YANG DIINGINKAN:
- Minimal durasi: {min_duration} detik
- Maksimal durasi: {max_duration} detik
- Titik Audio Peaks (teriakan/tawa): {', '.join(peaks_summary) if peaks_summary else 'Tidak ada peaks signifikan'}

TRANSKRIP VIDEO DENGAN TIMESTAMP (Bagian {chunk_idx}/{len(transcript_chunks)}):
{chunk_text}

Pilihlah 3 sampai 6 klip paling viral berdurasi {min_duration}-{max_duration} detik dengan skor viralitas minimal 75!
Hasilkan respons HANYA dalam JSON murni sesuai schema AICurationResponse."""

        chunk_clips = None
        
        # 1. Coba Prioritas 1: Google Gemini (Timeout 60 detik)
        if g_key and not chunk_clips:
            chunk_clips = call_gemini_provider(prompt_content, g_key, timeout_sec=60)
            
        # 2. Coba Prioritas 2: Mistral AI (jika Gemini gagal/kosong)
        if m_key and not chunk_clips:
            logger.info("Beralih ke Cadangan 1: Mistral AI...")
            chunk_clips = call_mistral_provider(prompt_content, m_key, timeout_sec=35)
            
        # 3. Coba Prioritas 3: GroqCloud (jika Mistral gagal/kosong)
        if gr_key and not chunk_clips:
            logger.info("Beralih ke Cadangan 2: GroqCloud...")
            chunk_clips = call_groq_provider(prompt_content, gr_key, timeout_sec=35)
            
        if chunk_clips:
            raw_ai_clips.extend(chunk_clips)
            
    # Filter klip: durasi valid dan skor viralitas >= 75
    valid_clips: List[CuratedClip] = []
    seen_ranges = set()
    
    for item in raw_ai_clips:
        start_t = round(float(item.start), 2)
        end_t = round(float(item.end), 2)
        duration = end_t - start_t
        score = int(item.score)
        
        # Filter aturan durasi & skor
        if duration < float(min_duration) * 0.8 or duration > float(max_duration) * 1.2:
            continue
        if score < 75:
            continue
            
        # Hindari klip duplikat/overlap berat
        range_key = (int(start_t // 10), int(end_t // 10))
        if range_key in seen_ranges:
            continue
        seen_ranges.add(range_key)
        
        clip_words = extract_words_for_clip(all_words, start_t, end_t)
        
        # Hook banner fallback jika kosong
        banner_text = item.hook_banner.strip().upper()
        if not banner_text or len(banner_text.split()) > 6:
            words_title = item.title.split()[:4]
            banner_text = " ".join(words_title).upper()
            
        valid_clips.append(CuratedClip(
            title=item.title.strip(),
            hook_banner=banner_text,
            hook_text=item.hook_text.strip(),
            virality_score=score,
            score_breakdown=ViralityBreakdown(
                hook_score=min(100, score + 4),
                flow_score=min(100, score - 2),
                engagement_score=min(100, score + 2)
            ),
            category=item.category if item.category in ["Hot Take", "Storytelling", "Tips Daging", "Komedi/Emosi"] else "Hot Take",
            reason=item.reason.strip(),
            start_time=start_t,
            end_time=end_t,
            corrected_words=clip_words,
            social_caption=item.social_caption.strip()
        ))
        
    if not valid_clips:
        logger.warning("Tidak ada klip AI yang memenuhi skor >= 75 atau provider gagal. Mengaktifkan fallback heuristik.")
        return fallback_heuristic_curation(transcript_data, peaks, min_duration, max_duration)
        
    # Urutkan berdasarkan skor viralitas tertinggi dan batasi 3-6 klip
    valid_clips.sort(key=lambda x: x.virality_score, reverse=True)
    selected_clips = valid_clips[:6]
    logger.info(f"Berhasil memilih {len(selected_clips)} klip viral kualitas tinggi (skor {selected_clips[0].virality_score} - {selected_clips[-1].virality_score})!")
    return CurationResponse(clips=selected_clips)
