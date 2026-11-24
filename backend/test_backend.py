import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

def test_imports_and_components():
    print("=== Testing IndoClip Pro Backend Components ===")
    
    # 1. Config & Environment
    from app.config import settings
    print(f"[OK] Settings loaded. BASE_DIR={settings.BASE_DIR}, TEMP_DIR={settings.TEMP_DIR}")
    
    # 2. Utils & FFmpeg
    from app.utils import FFMPEG_CMD, FFPROBE_CMD
    print(f"[OK] FFmpeg binary resolved: {FFMPEG_CMD}")
    print(f"[OK] FFprobe binary resolved: {FFPROBE_CMD}")
    
    # 3. Models
    from app.models import ProcessRequest, CuratedClip, ViralityBreakdown, WordTiming, CurationResponse
    req = ProcessRequest(youtube_url="https://www.youtube.com/watch?v=sample")
    print(f"[OK] Models validated. Sample request URL={req.youtube_url}")
    
    # 4. Transcriber CUDA / CPU detection
    from app.transcriber import detect_device_and_compute_type
    device, compute, model = detect_device_and_compute_type()
    print(f"[OK] Transcriber hardware detected: device={device}, compute_type={compute}, model={model}")
    
    # 5. Curator & google-genai SDK
    from google import genai
    from app.curator import CURATOR_SYSTEM_PROMPT
    print(f"[OK] google-genai SDK imported successfully. System prompt ready ({len(CURATOR_SYSTEM_PROMPT)} chars)")
    
    # 6. MediaPipe Face Detection & Face Mesh
    import mediapipe as mp
    mp_face_detection = mp.solutions.face_detection
    mp_face_mesh = mp.solutions.face_mesh
    det = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    mesh = mp_face_mesh.FaceMesh(max_num_faces=2, min_detection_confidence=0.5)
    det.close()
    mesh.close()
    print("[OK] MediaPipe Face Detection & Face Mesh initialized and verified without errors")
    
    # 7. Subtitle Generator & ASS Syntax
    from app.subtitle_generator import generate_ass_subtitle_file
    sample_words = [
        WordTiming(word="HALO", start=0.0, end=0.4),
        WordTiming(word="SEMUANYA", start=0.5, end=0.9),
        WordTiming(word="WELCOME", start=1.0, end=1.4),
        WordTiming(word="BACK", start=1.5, end=1.8),
    ]
    test_ass_path = settings.TEMP_DIR / "test_sample.ass"
    generate_ass_subtitle_file(
        words=sample_words,
        output_path=test_ass_path,
        hook_banner="DETIK-DETIK KETAHUAN BOHONG!",
        color_scheme="OPUS_GREEN"
    )
    assert test_ass_path.exists(), "ASS subtitle file was not created"
    ass_content = test_ass_path.read_text(encoding="utf-8")
    assert "HookBanner" in ass_content
    assert "DETIK-DETIK KETAHUAN BOHONG!" in ass_content
    print(f"[OK] ASS Subtitle file generated successfully ({test_ass_path.stat().st_size} bytes)")
    
    # 8. Audio Peak Detection algorithm test with synthetic audio
    import numpy as np
    from scipy.io import wavfile
    from app.audio_analyzer import detect_audio_peaks
    
    sample_rate = 16000
    duration_sec = 10
    t = np.linspace(0, duration_sec, sample_rate * duration_sec, endpoint=False)
    # Background tone
    audio_signal = 0.1 * np.sin(2 * np.pi * 440 * t)
    # Add volume burst (peak) at t=3.0s and t=7.0s
    burst_idx1 = int(3.0 * sample_rate)
    burst_idx2 = int(7.0 * sample_rate)
    burst_len = int(0.5 * sample_rate)
    audio_signal[burst_idx1 : burst_idx1 + burst_len] += 0.8
    audio_signal[burst_idx2 : burst_idx2 + burst_len] += 0.9
    audio_int16 = (audio_signal * 32767).astype(np.int16)
    
    test_wav_path = settings.TEMP_DIR / "test_synthetic.wav"
    wavfile.write(str(test_wav_path), sample_rate, audio_int16)
    peaks = detect_audio_peaks(test_wav_path, min_distance_sec=2.0)
    print(f"[OK] Audio Peak Detection tested: found {len(peaks)} peaks at timestamps {[p.timestamp for p in peaks]}")
    assert len(peaks) >= 2, "Expected at least 2 synthetic peaks"
    
    print("\n>>> ALL BACKEND COMPONENTS PASSED VERIFICATION WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    test_imports_and_components()
