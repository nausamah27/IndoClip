import os
import json
import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, AsyncGenerator

from app.config import settings
from app.models import (
    ProcessRequest,
    JobState,
    ClipResultItem,
    WordTiming,
    AudioPeak,
    CuratedClip,
    ReRenderSubtitleRequest
)
from app.audio_analyzer import analyze_audio_stage
from app.transcriber import transcribe_audio
from app.curator import curate_viral_clips, fallback_heuristic_curation
from app.downloader import download_partial_video
from app.reframer import reframer
from app.renderer import render_final_clip, rerender_clip_subtitles_only

logger = logging.getLogger("indoclip.pipeline")

# In-memory storage for jobs and active SSE queues
active_jobs: Dict[str, JobState] = {}
job_event_queues: Dict[str, asyncio.Queue] = {}

async def broadcast_event(job_id: str, stage: str, stage_number: int, progress: int, message: str, data: Any = None):
    """Kirim update status via SSE ke client yang terhubung."""
    payload = {
        "job_id": job_id,
        "stage": stage,
        "stage_number": stage_number,
        "progress": progress,
        "message": message,
        "data": data
    }
    
    if job_id in active_jobs:
        job = active_jobs[job_id]
        job.current_stage = stage
        job.progress = progress
        job.message = message
        
    if job_id in job_event_queues:
        await job_event_queues[job_id].put(payload)

async def run_pipeline_orchestrator(job_id: str, request: ProcessRequest):
    """
    Eksekutor pipeline 6 tahap IndoClip Pro:
    Hemat Resource & Kualitas Tinggi untuk kreator Indonesia.
    """
    job_temp_dir = settings.TEMP_DIR / job_id
    job_output_dir = settings.OUTPUT_DIR / job_id
    job_temp_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # ==========================================
        # TAHAP 1: Audio-First & Peak Detection
        # ==========================================
        await broadcast_event(
            job_id,
            stage="AUDIO_EXTRACTION",
            stage_number=1,
            progress=5,
            message="Tahap 1/6: Mengunduh trek audio terbaik dari YouTube..."
        )
        
        loop = asyncio.get_running_loop()
        audio_path, peaks, video_title, duration = await loop.run_in_executor(
            None,
            analyze_audio_stage,
            request.youtube_url,
            job_temp_dir,
            job_id
        )
        
        if job_id in active_jobs:
            active_jobs[job_id].video_title = video_title
            active_jobs[job_id].duration = duration
            active_jobs[job_id].audio_peaks_count = len(peaks)
            
        await broadcast_event(
            job_id,
            stage="AUDIO_PEAKS_DONE",
            stage_number=1,
            progress=20,
            message=f"Tahap 1/6 Selesai: {len(peaks)} titik Audio Peaks (teriakan/tawa/klimaks) terdeteksi!",
            data={"peaks_count": len(peaks), "title": video_title, "duration": duration}
        )

        # ==========================================
        # TAHAP 2: Transkripsi Akurat Bahasa Indo
        # ==========================================
        await broadcast_event(
            job_id,
            stage="TRANSCRIPTION_START",
            stage_number=2,
            progress=25,
            message="Tahap 2/6: Menjalankan faster-whisper dengan deteksi kata presisi (word timestamps)..."
        )
        
        # Gunakan WAV 16kHz yang sudah dikonversi di Tahap 1 jika ada
        wav_audio_path = job_temp_dir / "audio_16k.wav"
        transcribe_target = wav_audio_path if wav_audio_path.exists() else audio_path
        
        # Callback progres transkripsi live (menit ke menit)
        def on_transcribe_progress(current_sec, total_sec, text_snippet):
            fraction = min(1.0, current_sec / max(1.0, total_sec))
            current_pct = 25 + int(fraction * 15)  # Range 25% - 40%
            mins_curr = int(current_sec // 60)
            secs_curr = int(current_sec % 60)
            mins_tot = int(total_sec // 60)
            secs_tot = int(total_sec % 60)
            progress_msg = f"Tahap 2/6: Mentranskrip percakapan menit {mins_curr:02d}:{secs_curr:02d} / {mins_tot:02d}:{secs_tot:02d} ({int(fraction * 100)}%)..."
            
            if job_id in active_jobs:
                active_jobs[job_id].progress = current_pct
                active_jobs[job_id].message = progress_msg
                
            asyncio.run_coroutine_threadsafe(
                broadcast_event(job_id, "TRANSCRIPTION_PROGRESS", 2, current_pct, progress_msg),
                loop
            )
            
        transcript_data = await loop.run_in_executor(
            None,
            transcribe_audio,
            transcribe_target,
            request.language,
            "Transkripsi percakapan santai YouTuber Indonesia, podcast, gaming, bahasa gaul sehari-hari, dan istilah Inggris.",
            on_transcribe_progress
        )
        
        await broadcast_event(
            job_id,
            stage="TRANSCRIPTION_DONE",
            stage_number=2,
            progress=40,
            message=f"Tahap 2/6 Selesai: {len(transcript_data['all_words'])} kata berhasil ditranskrip!",
            data={"word_count": len(transcript_data['all_words']), "language": transcript_data['language']}
        )

        # ==========================================
        # TAHAP 3: Kurasi Viral & Copywriting Indo
        # ==========================================
        await broadcast_event(
            job_id,
            stage="CURATION_START",
            stage_number=3,
            progress=45,
            message="Tahap 3/6: AI mengurasi momen viral & hook judul (Auto-Fallback: Gemini / Mistral / Groq)..."
        )
        
        try:
            curation_result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    curate_viral_clips,
                    transcript_data,
                    peaks,
                    request.gemini_api_key,
                    request.mistral_api_key,
                    request.groq_api_key,
                    request.min_clip_duration,
                    request.max_clip_duration
                ),
                timeout=75.0  # Timeout fleksibel untuk multi-provider fallback
            )
        except asyncio.TimeoutError:
            logger.warning("Kurasi AI timeout (>75s). Mengaktifkan fallback heuristik audio peaks instan...")
            curation_result = fallback_heuristic_curation(
                transcript_data,
                peaks,
                request.min_clip_duration,
                request.max_clip_duration
            )
        
        curated_clips = curation_result.clips
        if not curated_clips:
            raise ValueError("Tidak ada klip viral yang memenuhi kriteria durasi.")
            
        await broadcast_event(
            job_id,
            stage="CURATION_DONE",
            stage_number=3,
            progress=55,
            message=f"Tahap 3/6 Selesai: {len(curated_clips)} klip viral kualitas tinggi (skor >= 75) berhasil dikurasi!",
            data={"clips_found": len(curated_clips)}
        )

        # ==========================================
        # TAHAP 4-6: Pemrosesan Per Klip
        # ==========================================
        processed_clip_items: List[ClipResultItem] = []
        total_clips = len(curated_clips)
        
        for idx, clip in enumerate(curated_clips, start=1):
            clip_id = f"clip_{idx}_{uuid.uuid4().hex[:6]}"
            base_progress = 55 + int((idx - 1) / total_clips * 40)
            
            # --- Tahap 4: Partial Video Download ---
            await broadcast_event(
                job_id,
                stage="PARTIAL_DOWNLOAD",
                stage_number=4,
                progress=base_progress + 3,
                message=f"Tahap 4/6 [Klip {idx}/{total_clips}]: Mengunduh potongan 1080p ({clip.start_time:.1f}s - {clip.end_time:.1f}s)..."
            )
            
            raw_video_path, rel_start, rel_end = await loop.run_in_executor(
                None,
                download_partial_video,
                request.youtube_url,
                clip,
                idx,
                job_temp_dir
            )
            
            # --- Tahap 5: Smart Multi-Mode Reframing (MediaPipe) ---
            await broadcast_event(
                job_id,
                stage="REFRAMING",
                stage_number=5,
                progress=base_progress + 7,
                message=f"Tahap 5/6 [Klip {idx}/{total_clips}]: Reframing 9:16 MediaPipe (Mode: {request.layout_mode})..."
            )
            
            reframed_path = job_temp_dir / f"{clip_id}_reframed.mp4"
            await loop.run_in_executor(
                None,
                reframer.reframe_video,
                raw_video_path,
                reframed_path,
                request.layout_mode,
                rel_start,
                clip.end_time - clip.start_time,
                clip.start_time
            )
            
            # --- Tahap 6: Editing Anti-Reused & Animated Subtitle ---
            await broadcast_event(
                job_id,
                stage="RENDERING",
                stage_number=6,
                progress=base_progress + 12,
                message=f"Tahap 6/6 [Klip {idx}/{total_clips}]: Merender subtitle animasi Opus, punch-in zoom, & hook banner..."
            )
            
            final_video_path = job_output_dir / f"{clip_id}.mp4"
            thumb_path = job_output_dir / f"{clip_id}_thumb.jpg"
            
            # Cari audio peaks di dalam durasi klip
            peaks_in_clip = [
                round(p.timestamp - clip.start_time, 2)
                for p in peaks
                if clip.start_time <= p.timestamp <= clip.end_time
            ]
            
            await loop.run_in_executor(
                None,
                render_final_clip,
                reframed_path,
                final_video_path,
                thumb_path,
                clip.corrected_words,
                clip.hook_banner,
                request.subtitle_color,
                clip.start_time,
                peaks_in_clip
            )
            
            # URL relatif untuk static mount
            video_url = f"/outputs/{job_id}/{clip_id}.mp4"
            thumb_url = f"/outputs/{job_id}/{clip_id}_thumb.jpg"
            
            clip_item = ClipResultItem(
                clip_id=clip_id,
                index=idx,
                title=clip.title,
                hook_banner=clip.hook_banner,
                virality_score=clip.virality_score,
                score_breakdown=clip.score_breakdown,
                category=clip.category,
                start_time=clip.start_time,
                end_time=clip.end_time,
                duration=round(clip.end_time - clip.start_time, 2),
                corrected_words=clip.corrected_words,
                social_caption=clip.social_caption,
                video_url=video_url,
                thumbnail_url=thumb_url,
                reframed_video_path=str(reframed_path),
                peaks_in_clip=peaks_in_clip
            )
            processed_clip_items.append(clip_item)
            
        # Selesai seluruh pipeline
        if job_id in active_jobs:
            active_jobs[job_id].status = "COMPLETED"
            active_jobs[job_id].progress = 100
            active_jobs[job_id].clips = processed_clip_items
            active_jobs[job_id].message = "Semua klip IndoClip Pro berhasil diproses dan siap didownload!"
            
        # Simpan hasil ke JSON permanen
        results_file = job_output_dir / "results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            f.write(active_jobs[job_id].model_dump_json(indent=2))
            
        await broadcast_event(
            job_id,
            stage="COMPLETED",
            stage_number=6,
            progress=100,
            message="Selesai! Seluruh klip telah siap.",
            data={"clips": [c.model_dump() for c in processed_clip_items]}
        )
        
    except Exception as e:
        logger.error(f"Pipeline error for job {job_id}: {e}", exc_info=True)
        if job_id in active_jobs:
            active_jobs[job_id].status = "FAILED"
            active_jobs[job_id].error = str(e)
            active_jobs[job_id].message = f"Terjadi kesalahan: {e}"
        await broadcast_event(
            job_id,
            stage="ERROR",
            stage_number=0,
            progress=0,
            message=f"Error: {e}",
            data={"error": str(e)}
        )

async def handle_rerender_subtitle(req: ReRenderSubtitleRequest) -> ClipResultItem:
    """
    Memproses permintaan re-render subtitle inline dari frontend tanpa download ulang.
    """
    job_id = req.job_id
    clip_id = req.clip_id
    
    if job_id not in active_jobs:
        raise ValueError(f"Job {job_id} tidak ditemukan.")
        
    job = active_jobs[job_id]
    target_clip = next((c for c in job.clips if c.clip_id == clip_id), None)
    if not target_clip:
        raise ValueError(f"Klip {clip_id} tidak ditemukan di job {job_id}.")
        
    reframed_path = Path(target_clip.reframed_video_path)
    if not reframed_path.exists():
        raise FileNotFoundError(f"File video reframed tidak ditemukan: {reframed_path}")
        
    job_output_dir = settings.OUTPUT_DIR / job_id
    final_video_path = job_output_dir / f"{clip_id}.mp4"
    
    words_to_use = req.edited_words if req.edited_words is not None else target_clip.corrected_words
    hook_banner = req.hook_banner if req.hook_banner is not None else target_clip.hook_banner
    
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        rerender_clip_subtitles_only,
        reframed_path,
        final_video_path,
        words_to_use,
        hook_banner,
        req.subtitle_color,
        target_clip.start_time
    )
    
    # Update state
    target_clip.corrected_words = words_to_use
    target_clip.hook_banner = hook_banner
    
    return target_clip
