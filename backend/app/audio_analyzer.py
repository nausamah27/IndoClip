import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Any
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks
import yt_dlp

from app.utils import FFMPEG_CMD, run_subprocess
from app.models import AudioPeak

logger = logging.getLogger("indoclip.audio")

def download_audio_track(youtube_url: str, output_dir: Path, job_id: str) -> Tuple[Path, str, float]:
    """
    Tahap 1.1: Unduh hanya trek audio terbaik menggunakan yt-dlp ke temp/{job_id}/audio.m4a.
    Mengembalikan: (path_audio_m4a, video_title, video_duration)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_template = str(output_dir / "audio.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': audio_template,
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }] if not audio_template.endswith(".m4a") else []
    }
    
    logger.info(f"Downloading best audio track for {youtube_url}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        video_title = info.get('title', 'Video YouTube')
        duration = float(info.get('duration', 0.0))
        
    # Lokasi audio yang dihasilkan
    possible_files = list(output_dir.glob("audio.*"))
    if not possible_files:
        raise FileNotFoundError(f"Gagal mengunduh audio untuk job {job_id}")
    
    audio_path = possible_files[0]
    return audio_path, video_title, duration

def convert_to_wav_pcm(audio_path: Path, wav_path: Path) -> Path:
    """Mengonversi file audio ke format WAV 16kHz mono PCM untuk analisis cepat."""
    cmd = [
        FFMPEG_CMD,
        "-y",
        "-i", str(audio_path),
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        str(wav_path)
    ]
    run_subprocess(cmd)
    return wav_path

def detect_audio_peaks(wav_path: Path, min_distance_sec: float = 3.0) -> List[AudioPeak]:
    """
    Tahap 1.2: Analisis file audio menggunakan numpy/scipy untuk mendeteksi
    titik-titik lonjakan volume/tawa/teriakan (Audio Peaks).
    """
    sample_rate, data = wavfile.read(str(wav_path))
    
    # Normalisasi data audio ke range -1.0 s/d 1.0
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        data = (data.astype(np.float32) - 128.0) / 128.0
        
    total_samples = len(data)
    total_duration = total_samples / sample_rate
    
    # Hitung RMS envelope dalam window 250ms (0.25s) dengan hop 100ms
    window_size = int(0.25 * sample_rate)
    hop_size = int(0.10 * sample_rate)
    
    num_frames = max(1, (total_samples - window_size) // hop_size)
    rms_values = np.zeros(num_frames, dtype=np.float32)
    timestamps = np.zeros(num_frames, dtype=np.float32)
    
    for i in range(num_frames):
        start = i * hop_size
        frame = data[start : start + window_size]
        rms_values[i] = np.sqrt(np.mean(frame**2) + 1e-9)
        timestamps[i] = (start + window_size / 2) / sample_rate
        
    # Baseline statistik
    mean_energy = float(np.mean(rms_values))
    std_energy = float(np.std(rms_values))
    
    # Ambang batas lonjakan volume (mean + 1.4 * std)
    threshold = mean_energy + 1.4 * std_energy
    min_dist_frames = int(min_distance_sec / 0.10)
    
    # Deteksi puncak (peaks)
    peak_indices, properties = find_peaks(
        rms_values,
        height=threshold,
        distance=min_dist_frames,
        prominence=0.5 * std_energy
    )
    
    peaks: List[AudioPeak] = []
    for idx in peak_indices:
        t = round(float(timestamps[idx]), 2)
        intensity = round(float(rms_values[idx] / (mean_energy + 1e-6)), 2)
        peaks.append(AudioPeak(timestamp=t, intensity=intensity))
        
    # Urutkan berdasarkan timestamp
    peaks.sort(key=lambda x: x.timestamp)
    logger.info(f"Detected {len(peaks)} audio peaks across {total_duration:.1f}s audio.")
    return peaks

def analyze_audio_stage(youtube_url: str, temp_dir: Path, job_id: str) -> Tuple[Path, List[AudioPeak], str, float]:
    """
    Fungsi pipeline lengkap Tahap 1:
    Mengunduh audio, konversi wav, analisis lonjakan suara, dan simpan peaks.json.
    """
    audio_path, video_title, duration = download_audio_track(youtube_url, temp_dir, job_id)
    wav_path = temp_dir / "audio_16k.wav"
    convert_to_wav_pcm(audio_path, wav_path)
    
    peaks = detect_audio_peaks(wav_path)
    
    # Simpan hasil ke peaks.json
    peaks_file = temp_dir / "peaks.json"
    with open(peaks_file, "w", encoding="utf-8") as f:
        json.dump([p.model_dump() for p in peaks], f, indent=2)
        
    return audio_path, peaks, video_title, duration
