from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class WordTiming(BaseModel):
    word: str = Field(description="Kata")
    start: float = Field(description="Waktu mulai dalam detik")
    end: float = Field(description="Waktu selesai dalam detik")
    probability: Optional[float] = Field(default=1.0, description="Confidence score")

class ViralityBreakdown(BaseModel):
    hook_score: int = Field(default=85, description="Skor daya pikat 3 detik pertama (1-100)")
    flow_score: int = Field(default=85, description="Skor kelancaran alur dan punchline (1-100)")
    engagement_score: int = Field(default=85, description="Skor potensi share, komentar, replay (1-100)")

class AudioPeak(BaseModel):
    timestamp: float
    intensity: float

class CuratedClip(BaseModel):
    title: str = Field(description="Judul deskriptif dan clickbait positif khas kreator Indonesia")
    hook_banner: str = Field(description="Teks pancingan maksimal 5 kata HURUF KAPITAL untuk 3 detik pertama")
    virality_score: int = Field(description="Skor total viralitas konten (1-100)")
    score_breakdown: ViralityBreakdown = Field(description="Rincian skor hook, alur cerita, dan potensi interaksi")
    category: str = Field(description="Kategori klip: 'PODCAST', 'GAMING', atau 'SOLO'")
    start_time: float = Field(description="Detik mulai klip (tepat pada jeda napas, jangan potong kata)")
    end_time: float = Field(description="Detik selesai klip (durasi ideal 30-65 detik)")
    corrected_words: List[WordTiming] = Field(description="Kata-kata dengan perbaikan ejaan slang/gaul Indonesia tanpa mengubah timestamp")
    social_caption: str = Field(description="Caption siap posting dan hashtag viral TikTok/Shorts")

class CurationResponse(BaseModel):
    clips: List[CuratedClip] = Field(description="Daftar 3-6 klip viral terbaik")

class ProcessRequest(BaseModel):
    youtube_url: str = Field(description="URL video YouTube yang ingin diproses")
    gemini_api_key: Optional[str] = Field(default=None, description="API Key Google Gemini")
    layout_mode: str = Field(default="AUTO", description="Mode layout: 'AUTO', 'PODCAST', 'GAMING', 'SOLO'")
    subtitle_color: str = Field(default="OPUS_GREEN", description="Warna highlight subtitle: 'OPUS_GREEN', 'SALMON_PINK', 'CYBER_YELLOW'")
    language: str = Field(default="id", description="Bahasa transkripsi ('id' atau 'auto')")
    min_clip_duration: int = Field(default=30, description="Durasi minimal klip dalam detik")
    max_clip_duration: int = Field(default=65, description="Durasi maksimal klip dalam detik")

class ReRenderSubtitleRequest(BaseModel):
    job_id: str
    clip_id: str
    subtitle_color: str = Field(default="OPUS_GREEN", description="Warna highlight subtitle")
    hook_banner: Optional[str] = Field(default=None, description="Teks hook banner jika ingin diperbarui")
    edited_words: Optional[List[WordTiming]] = Field(default=None, description="Daftar kata yang telah diedit")
    edited_text: Optional[str] = Field(default=None, description="Alternatif teks lengkap jika diedit per kalimat")

class ClipResultItem(BaseModel):
    clip_id: str
    index: int
    title: str
    hook_banner: str
    virality_score: int
    score_breakdown: ViralityBreakdown
    category: str
    start_time: float
    end_time: float
    duration: float
    corrected_words: List[WordTiming]
    social_caption: str
    video_url: str
    thumbnail_url: Optional[str] = None
    reframed_video_path: Optional[str] = None
    peaks_in_clip: List[float] = Field(default_factory=list)

class JobState(BaseModel):
    job_id: str
    status: str = "PENDING"  # PENDING, PROCESSING, COMPLETED, FAILED
    current_stage: str = "INIT"
    progress: int = 0
    message: str = "Inisialisasi antrean..."
    youtube_url: str = ""
    video_title: str = ""
    duration: float = 0.0
    clips: List[ClipResultItem] = Field(default_factory=list)
    audio_peaks_count: int = 0
    error: Optional[str] = None
