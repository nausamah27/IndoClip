'use client';

import React, { useState, useRef } from 'react';
import {
  Flame,
  Download,
  Copy,
  Edit3,
  Check,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Share2,
  Sparkles
} from 'lucide-react';
import { ClipResultItem } from '../types';
import { SubtitleEditorModal } from './SubtitleEditorModal';
import { getFullMediaUrl } from '../utils/api';

interface ClipCardProps {
  clip: ClipResultItem;
  jobId: string;
  onClipUpdated: (updated: ClipResultItem) => void;
}

export const ClipCard: React.FC<ClipCardProps> = ({ clip, jobId, onClipUpdated }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [copiedCaption, setCopiedCaption] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleCopyCaption = () => {
    const textToCopy = `${clip.title}\n\n${clip.social_caption}`;
    navigator.clipboard.writeText(textToCopy);
    setCopiedCaption(true);
    setTimeout(() => setCopiedCaption(false), 2500);
  };

  const getViralityColor = (score: number) => {
    if (score >= 90) return 'text-salmon border-salmon bg-salmon/10';
    if (score >= 80) return 'text-green-400 border-green-500 bg-green-500/10';
    return 'text-yellow-400 border-yellow-500 bg-yellow-500/10';
  };

  return (
    <div className="glass-card rounded-3xl p-5 sm:p-6 transition-all duration-300 flex flex-col md:flex-row gap-6 hover:shadow-2xl hover:shadow-salmon/10">
      {/* 9:16 Vertical Video Preview Player */}
      <div className="w-full md:w-[280px] flex-shrink-0 flex flex-col items-center">
        <div className="relative aspect-[9/16] w-full max-w-[280px] bg-black rounded-2xl overflow-hidden shadow-2xl border border-dark-border group">
          <video
            ref={videoRef}
            src={getFullMediaUrl(clip.video_url)}
            poster={getFullMediaUrl(clip.thumbnail_url)}
            playsInline
            loop
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            className="w-full h-full object-cover cursor-pointer"
            onClick={togglePlay}
          />

          {/* Top Hook Banner Badge */}
          <div className="absolute top-3 inset-x-3 z-10 pointer-events-none">
            <div className="px-2.5 py-1.5 rounded-lg bg-black/75 backdrop-blur-md border border-salmon/40 text-center">
              <span className="text-[11px] font-black text-white tracking-wider uppercase">
                🔥 {clip.hook_banner} 🔥
              </span>
            </div>
          </div>

          {/* Floating Player Controls Overlay */}
          <div className="absolute bottom-3 inset-x-3 z-10 flex items-center justify-between pointer-events-auto opacity-0 group-hover:opacity-100 transition-opacity bg-black/60 backdrop-blur-md p-2 rounded-xl">
            <button
              onClick={togglePlay}
              className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white transition"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <span className="text-[11px] font-mono text-gray-300">
              {clip.duration.toFixed(0)}s
            </span>
            <button
              onClick={toggleMute}
              className="p-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white transition"
            >
              {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Clip Metadata & Actions */}
      <div className="flex-1 flex flex-col justify-between space-y-4">
        <div>
          {/* Header & Virality Score */}
          <div className="flex flex-wrap items-start justify-between gap-3 mb-2">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md bg-salmon/15 text-salmon border border-salmon/25 inline-block mb-2">
                Klip #{clip.index} • Mode {clip.category}
              </span>
              <h3 className="text-lg font-bold text-white leading-snug">
                {clip.title}
              </h3>
            </div>

            {/* Virality Score Badge */}
            <div
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border font-black text-sm shadow-md ${getViralityColor(
                clip.virality_score
              )}`}
            >
              <Flame className="w-4 h-4 fill-current" />
              <span>Score {clip.virality_score}/100</span>
            </div>
          </div>

          {/* Score Breakdown Pills */}
          <div className="flex flex-wrap gap-2 mt-3 text-xs">
            <span className="px-2.5 py-1 rounded-lg bg-dark-input border border-dark-border text-gray-300">
              Hook:{' '}
              <strong className="text-white">
                {clip.score_breakdown?.hook_score || 88}
              </strong>
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-dark-input border border-dark-border text-gray-300">
              Story Flow:{' '}
              <strong className="text-white">
                {clip.score_breakdown?.flow_score || 85}
              </strong>
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-dark-input border border-dark-border text-gray-300">
              Engagement:{' '}
              <strong className="text-white">
                {clip.score_breakdown?.engagement_score || 90}
              </strong>
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-dark-input border border-dark-border text-gray-400 font-mono">
              ⏱ {clip.start_time.toFixed(1)}s - {clip.end_time.toFixed(1)}s
            </span>
          </div>

          {/* Subtitle Words Snippet Preview */}
          <div className="mt-4 p-3.5 bg-dark-input/60 rounded-xl border border-dark-border text-xs text-gray-300 leading-relaxed font-sans line-clamp-3">
            <span className="text-salmon font-bold">Subtitle Transkrip: </span>
            {(clip.corrected_words || []).map((w) => w.word).join(' ')}
          </div>

          {/* Ready-to-Post Social Caption */}
          <div className="mt-3 p-3 bg-dark-bg/80 rounded-xl border border-dark-border/80 text-xs text-gray-400">
            <span className="text-gray-200 font-semibold block mb-1">
              📱 Caption & Hashtag TikTok/Shorts:
            </span>
            <p className="line-clamp-2 italic">{clip.social_caption}</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-dark-border">
          {/* Edit Subtitles Inline */}
          <button
            onClick={() => setShowEditor(true)}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-dark-input hover:bg-dark-hover border border-dark-border hover:border-salmon/40 text-xs font-semibold text-gray-200 hover:text-white transition shadow-sm"
          >
            <Edit3 className="w-3.5 h-3.5 text-salmon" />
            <span>Edit Subtitle & Hook</span>
          </button>

          {/* Copy Caption & Hashtags */}
          <button
            onClick={handleCopyCaption}
            className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-dark-input hover:bg-dark-hover border border-dark-border text-xs font-semibold text-gray-200 hover:text-white transition shadow-sm"
          >
            {copiedCaption ? (
              <Check className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <Copy className="w-3.5 h-3.5 text-gray-400" />
            )}
            <span>{copiedCaption ? 'Tersalin!' : 'Copy Caption & Hashtag'}</span>
          </button>

          {/* Download Final MP4 Button */}
          <a
            href={getFullMediaUrl(clip.video_url)}
            download={`${clip.clip_id}.mp4`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl salmon-gradient text-xs font-bold text-white shadow-md shadow-salmon/20 hover:opacity-95 transition ml-auto"
          >
            <Download className="w-4 h-4" />
            <span>Download MP4</span>
          </a>
        </div>
      </div>

      {/* Inline Subtitle Editor Modal */}
      {showEditor && (
        <SubtitleEditorModal
          clip={clip}
          jobId={jobId}
          onClose={() => setShowEditor(false)}
          onUpdatedClip={onClipUpdated}
        />
      )}
    </div>
  );
};
