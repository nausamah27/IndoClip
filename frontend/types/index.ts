export interface WordTiming {
  word: string;
  start: number;
  end: number;
  probability?: number;
}

export interface ViralityBreakdown {
  hook_score: number;
  flow_score: number;
  engagement_score: number;
}

export interface ClipResultItem {
  clip_id: string;
  index: number;
  title: string;
  hook_banner: string;
  virality_score: number;
  score_breakdown: ViralityBreakdown;
  category: 'PODCAST' | 'GAMING' | 'SOLO' | string;
  start_time: number;
  end_time: number;
  duration: number;
  corrected_words: WordTiming[];
  social_caption: string;
  video_url: string;
  thumbnail_url?: string;
  reframed_video_path?: string;
  peaks_in_clip?: number[];
}

export interface JobState {
  job_id: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  current_stage: string;
  progress: number;
  message: string;
  youtube_url: string;
  video_title?: string;
  duration?: number;
  clips: ClipResultItem[];
  audio_peaks_count?: number;
  error?: string;
}

export interface PipelineProgressEvent {
  job_id: string;
  stage: string;
  stage_number: number;
  progress: number;
  message: string;
  data?: any;
}

export type LayoutMode = 'AUTO' | 'PODCAST' | 'GAMING' | 'SOLO';
export type SubtitleColor = 'OPUS_GREEN' | 'SALMON_PINK' | 'CYBER_YELLOW';
