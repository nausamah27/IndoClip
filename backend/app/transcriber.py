import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Fix PyAV 19+ compatibility with faster-whisper (metadata_errors argument removed in PyAV 19)
try:
    import av
    _original_av_open = av.open
    def _safe_av_open(*args, **kwargs):
        kwargs.pop("metadata_errors", None)
        return _original_av_open(*args, **kwargs)
    av.open = _safe_av_open
except Exception:
    pass

import os, sys, site
# Auto-link nvidia cublas / cudnn libraries for CTranslate2 GPU execution
try:
    for p in site.getsitepackages():
        for sub in ["cublas", "cudnn"]:
            target = os.path.join(p, "nvidia", sub, "lib")
            if os.path.isdir(target):
                current_ld = os.environ.get("LD_LIBRARY_PATH", "")
                if target not in current_ld:
                    os.environ["LD_LIBRARY_PATH"] = f"{target}:{current_ld}"
                import ctypes
                for fname in os.listdir(target):
                    if fname.startswith("libcublas.so") or fname.startswith("libcudnn.so"):
                        try:
                            ctypes.CDLL(os.path.join(target, fname))
                        except Exception:
                            pass
except Exception:
    pass

from app.config import settings

logger = logging.getLogger("indoclip.transcriber")

def detect_device_and_compute_type() -> Tuple[str, str, str]:
    """
    Cek konfigurasi perangkat & tipe komputasi.
    Dioptimalkan khusus untuk CPU Intel Core i7-8665U:
    default model="small", device="cpu", compute_type="int8".
    Jika GPU CUDA terdeteksi, otomatis switch ke GPU.
    """
    cuda_available = False
    
    try:
        import torch
        if torch.cuda.is_available():
            cuda_available = True
            device_name = torch.cuda.get_device_name(0)
            logger.info(f"CUDA detected via torch: {device_name}")
    except ImportError:
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                cuda_available = True
                logger.info("CUDA detected via ctranslate2")
        except Exception as e:
            logger.warning(f"CUDA detection failed: {e}")
            cuda_available = False
    except Exception as e:
        logger.warning(f"CUDA torch check error: {e}")
        cuda_available = False
        
    if cuda_available:
        return "cuda", "float16", "medium"
    else:
        return settings.WHISPER_DEVICE, settings.WHISPER_COMPUTE_TYPE, settings.WHISPER_MODEL

def transcribe_audio(
    audio_path: Path,
    language: str = "id",
    initial_prompt: str = "Transkripsi percakapan santai YouTuber Indonesia, podcast, gaming, bahasa gaul sehari-hari, dan istilah Inggris.",
    progress_callback = None
) -> Dict[str, Any]:
    """
    Tahap 2: Transkripsi Akurat Bahasa Indonesia menggunakan faster-whisper.
    Menggunakan word_timestamps=True, vad_filter=True, dan beam_size=1 (greedy)
    dengan 6 cpu_threads pada Intel Core i7-8665U (4C/8T).
    """
    from faster_whisper import WhisperModel

    device, compute_type, default_model = detect_device_and_compute_type()
    cpu_threads = settings.WHISPER_CPU_THREADS  # 6 threads (sisa 2 thread untuk OS/Browser agar lancar)
    logger.info(f"Initializing faster-whisper with model='{default_model}', device='{device}', compute_type='{compute_type}', threads={cpu_threads}")
    
    try:
        model = WhisperModel(default_model, device=device, compute_type=compute_type, cpu_threads=cpu_threads)
    except Exception as init_err:
        if device == "cuda":
            logger.warning(f"CUDA faster-whisper init failed ({init_err}), falling back to CPU (small, int8)...")
            device = "cpu"
            compute_type = "int8"
            default_model = "small"
            model = WhisperModel(default_model, device=device, compute_type=compute_type, cpu_threads=cpu_threads)
        else:
            raise init_err
    
    logger.info(f"Transcribing audio {audio_path.name} (language={language}, beam_size={settings.WHISPER_BEAM_SIZE}, vad_filter=True)...")
    segments_generator, info = model.transcribe(
        str(audio_path),
        language=language if language != "auto" else None,
        initial_prompt=initial_prompt,
        word_timestamps=True,
        beam_size=settings.WHISPER_BEAM_SIZE,  # beam_size=1 (3x-4x lebih cepat pada audio panjang)
        vad_filter=True,                       # Voice Activity Detection aktif untuk melewati keheningan
        vad_parameters=dict(min_silence_duration_ms=500)
    )
    
    total_duration = max(1.0, info.duration if info.duration else 1.0)
    formatted_segments = []
    all_words = []
    last_report_sec = 0.0
    
    for segment in segments_generator:
        segment_words = []
        if segment.words:
            for w in segment.words:
                cleaned_word = w.word.strip()
                if cleaned_word:
                    word_obj = {
                        "word": cleaned_word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2)
                    }
                    segment_words.append(word_obj)
                    all_words.append(word_obj)
                    
        formatted_segments.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip(),
            "words": segment_words
        })
        
        # Kirim update progres transkripsi secara bertahap
        if progress_callback and (segment.end - last_report_sec >= 10.0 or len(formatted_segments) % 15 == 0):
            last_report_sec = segment.end
            progress_callback(segment.end, total_duration, segment.text.strip())
        
    full_transcript_text = " ".join(s["text"] for s in formatted_segments)
    logger.info(f"Transcription completed: {len(formatted_segments)} segments, {len(all_words)} words.")
    
    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 2),
        "duration": round(info.duration, 2),
        "text": full_transcript_text,
        "segments": formatted_segments,
        "all_words": all_words
    }
