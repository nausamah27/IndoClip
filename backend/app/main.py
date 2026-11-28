import os
import json
import uuid
import asyncio
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import settings
from app.models import ProcessRequest, JobState, ReRenderSubtitleRequest
from app.pipeline import (
    active_jobs,
    job_event_queues,
    run_pipeline_orchestrator,
    handle_rerender_subtitle
)
from app.utils import FFMPEG_CMD, FFPROBE_CMD, get_video_duration
from app.transcriber import detect_device_and_compute_type

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("indoclip.main")

app = FastAPI(
    title="IndoClip Pro API",
    description="Backend AI Video Clipper khusus Kreator & YouTuber Indonesia",
    version="1.0.0"
)

# CORS setup - Mengizinkan semua origin, method, dan header (termasuk ngrok-skip-browser-warning)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount outputs directory as static files for video streaming and preview
app.mount("/outputs", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="outputs")

@app.get("/api/health")
async def health_check():
    """Endpoint status sistem, verifikasi GPU CUDA, CPU i7-8665U & FFmpeg."""
    device, compute_type, default_model = detect_device_and_compute_type()
    
    return {
        "status": "online",
        "app_name": "IndoClip Pro",
        "cpu_optimization": "Intel Core i7-8665U (4C / 8T)",
        "ffmpeg_path": FFMPEG_CMD,
        "ffprobe_path": FFPROBE_CMD,
        "ffmpeg_threads": settings.FFMPEG_THREADS,
        "ffmpeg_preset": settings.FFMPEG_PRESET,
        "cuda_device": device,
        "compute_type": compute_type,
        "default_whisper_model": default_model,
        "whisper_cpu_threads": settings.WHISPER_CPU_THREADS,
        "whisper_beam_size": settings.WHISPER_BEAM_SIZE,
        "gemini_api_configured": bool(os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY),
        "mistral_api_configured": bool(os.getenv("MISTRAL_API_KEY") or settings.MISTRAL_API_KEY),
        "groq_api_configured": bool(os.getenv("GROQ_API_KEY") or settings.GROQ_API_KEY),
        "cookies_configured": settings.COOKIES_FILE.exists()
    }

@app.post("/api/process")
async def start_process_pipeline(request: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Memulai pipeline video clipping 6 tahap di background.
    API Key Gemini, Mistral, dan Groq otomatis di-resolve dari environment jika tidak dikirim frontend.
    """
    if not request.youtube_url or "http" not in request.youtube_url:
        raise HTTPException(status_code=400, detail="URL YouTube tidak valid.")
        
    # Auto-resolve API keys dari environment backend jika kosong di frontend
    gemini_key = (request.gemini_api_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip() or settings.GEMINI_API_KEY
    mistral_key = (request.mistral_api_key or "").strip() or os.getenv("MISTRAL_API_KEY", "").strip() or settings.MISTRAL_API_KEY
    groq_key = (request.groq_api_key or "").strip() or os.getenv("GROQ_API_KEY", "").strip() or settings.GROQ_API_KEY
    
    if not gemini_key and not mistral_key and not groq_key:
        raise HTTPException(
            status_code=400,
            detail="Semua API key (Gemini, Mistral, Groq) kosong. Harap isi salah satu API key di form pengaturan atau environment variable backend."
        )
        
    request.gemini_api_key = gemini_key or None
    request.mistral_api_key = mistral_key or None
    request.groq_api_key = groq_key or None
        
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    
    # Inisialisasi job state dan antrean SSE
    new_job = JobState(
        job_id=job_id,
        status="PROCESSING",
        current_stage="QUEUED",
        progress=1,
        message="Antrean job berhasil dibuat...",
        youtube_url=request.youtube_url
    )
    active_jobs[job_id] = new_job
    job_event_queues[job_id] = asyncio.Queue()
    
    # Jalankan pipeline di background
    background_tasks.add_task(run_pipeline_orchestrator, job_id, request)
    
    logger.info(f"Started job {job_id} for URL {request.youtube_url}")
    return {"job_id": job_id, "status": "QUEUED", "message": "Proses dimulai di latar belakang."}

@app.get("/api/progress/{job_id}")
async def stream_job_progress(job_id: str):
    """
    Server-Sent Events (SSE) stream untuk log progres real-time per tahap.
    """
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
        
    queue = job_event_queues.get(job_id)
    if not queue:
        queue = asyncio.Queue()
        job_event_queues[job_id] = queue
        
    async def event_generator() -> AsyncGenerator[str, None]:
        # Kirim status terkini terlebih dahulu
        current_job = active_jobs.get(job_id)
        if current_job:
            init_event = {
                "job_id": job_id,
                "stage": current_job.current_stage,
                "progress": current_job.progress,
                "message": current_job.message,
                "status": current_job.status
            }
            yield f"data: {json.dumps(init_event)}\n\n"
            
        while True:
            try:
                event_data = await asyncio.wait_for(queue.get(), timeout=20.0)
                yield f"data: {json.dumps(event_data)}\n\n"
                
                # Jika job selesai atau gagal, tutup stream
                if event_data.get("stage") in ["COMPLETED", "ERROR"]:
                    break
            except asyncio.TimeoutError:
                # Ping keep-alive
                yield f": keep-alive\n\n"
                current_job = active_jobs.get(job_id)
                if current_job and current_job.status in ["COMPLETED", "FAILED"]:
                    break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/jobs/{job_id}", response_model=JobState)
async def get_job_details(job_id: str):
    """Mengambil detail lengkap job dan hasil klip yang telah jadi."""
    if job_id not in active_jobs:
        # Coba cek apakah ada file results.json tersimpan
        saved_file = settings.OUTPUT_DIR / job_id / "results.json"
        if saved_file.exists():
            with open(saved_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return JobState(**data)
        raise HTTPException(status_code=404, detail="Job ID tidak ditemukan.")
        
    return active_jobs[job_id]

@app.post("/api/rerender-subtitle")
async def rerender_subtitle_endpoint(req: ReRenderSubtitleRequest):
    """
    Re-render subtitle inline dari editor teks tanpa download ulang video.
    """
    try:
        updated_clip = await handle_rerender_subtitle(req)
        return {"status": "SUCCESS", "clip": updated_clip}
    except Exception as e:
        logger.error(f"Failed to rerender subtitle: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
