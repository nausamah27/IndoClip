'use client';

import React from 'react';
import {
  Volume2,
  FileText,
  Sparkles,
  Download,
  Maximize2,
  Tv,
  CheckCircle2,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { PipelineProgressEvent } from '../types';

interface PipelineTrackerProps {
  progress: number;
  currentStage: string;
  message: string;
  logs: PipelineProgressEvent[];
  isCompleted: boolean;
  isError: boolean;
  errorMessage?: string;
}

export const PipelineTracker: React.FC<PipelineTrackerProps> = ({
  progress,
  currentStage,
  message,
  logs,
  isCompleted,
  isError,
  errorMessage,
}) => {
  const stages = [
    { number: 1, title: 'Audio-First & Peaks', desc: 'yt-dlp + scipy tawa/teriakan', icon: <Volume2 className="w-4 h-4" /> },
    { number: 2, title: 'Transkripsi Indo', desc: 'faster-whisper word-timestamps', icon: <FileText className="w-4 h-4" /> },
    { number: 3, title: 'Kurasi Viral Gemini', desc: 'gemini-2.5-flash scoring & hook', icon: <Sparkles className="w-4 h-4" /> },
    { number: 4, title: 'Partial Download', desc: '1080p bagian terpilih', icon: <Download className="w-4 h-4" /> },
    { number: 5, title: 'Reframing 9:16', desc: 'MediaPipe Face Mesh (Auto/Podcast)', icon: <Maximize2 className="w-4 h-4" /> },
    { number: 6, title: 'Render Subtitle Animasi', desc: 'Punch-in zoom + .ass subtitle', icon: <Tv className="w-4 h-4" /> },
  ];

  // Tentukan stage saat ini (1-6)
  const currentStageNumber = Math.min(
    6,
    Math.max(
      1,
      progress < 20 ? 1 : progress < 40 ? 2 : progress < 55 ? 3 : progress < 70 ? 4 : progress < 85 ? 5 : 6
    )
  );

  return (
    <div className="w-full max-w-4xl mx-auto glass-panel p-6 sm:p-7 rounded-3xl shadow-xl mt-8 animate-fade-in">
      {/* Header Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-dark-border gap-3">
        <div>
          <div className="flex items-center space-x-2.5">
            {!isCompleted && !isError && (
              <Loader2 className="w-5 h-5 text-salmon animate-spin" />
            )}
            {isCompleted && (
              <CheckCircle2 className="w-5 h-5 text-green-400" />
            )}
            {isError && (
              <AlertCircle className="w-5 h-5 text-red-400" />
            )}
            <h3 className="text-base font-bold text-white tracking-wide">
              {isCompleted
                ? 'Pipeline Pemrosesan Selesai 100%'
                : isError
                ? 'Pemrosesan Terhenti Karena Error'
                : 'Real-Time Pipeline Processing Tracker'}
            </h3>
          </div>
          <p className="text-xs text-gray-400 mt-1">{message}</p>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-2xl font-black salmon-text-gradient">
            {progress}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-dark-input h-3 rounded-full mt-5 overflow-hidden p-0.5 border border-dark-border">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isError ? 'bg-red-500' : 'salmon-gradient'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* 6 Stage Steps Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mt-6">
        {stages.map((stg) => {
          const isDone = progress >= (stg.number * 16);
          const isCurrent = !isDone && currentStageNumber === stg.number && !isError;
          return (
            <div
              key={stg.number}
              className={`p-3 rounded-xl border text-center transition-all ${
                isDone
                  ? 'bg-dark-card border-green-500/30 text-green-400'
                  : isCurrent
                  ? 'bg-dark-card border-salmon text-salmon shadow-lg shadow-salmon/10 animate-pulse-glow'
                  : 'bg-dark-input/40 border-dark-border text-gray-500'
              }`}
            >
              <div className="flex items-center justify-center mb-1.5">
                <span
                  className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${
                    isDone
                      ? 'bg-green-500/20 text-green-400'
                      : isCurrent
                      ? 'bg-salmon/20 text-salmon'
                      : 'bg-dark-bg text-gray-500'
                  }`}
                >
                  {isDone ? '✓' : stg.icon}
                </span>
              </div>
              <h4 className="text-[11px] font-bold text-white truncate">
                {stg.number}. {stg.title}
              </h4>
              <p className="text-[10px] text-gray-400 truncate mt-0.5">
                {stg.desc}
              </p>
            </div>
          );
        })}
      </div>

      {/* Live Log Stream Console */}
      <div className="mt-6 bg-dark-bg/90 rounded-2xl p-4 border border-dark-border/80 text-xs font-mono max-h-48 overflow-y-auto">
        <div className="text-[10px] uppercase font-bold text-gray-500 mb-2 tracking-wider flex items-center justify-between">
          <span>Live Console Stream (SSE)</span>
          <span className="w-2 h-2 rounded-full bg-salmon animate-ping" />
        </div>
        <div className="space-y-1.5">
          {logs.map((log, index) => (
            <div key={index} className="flex items-start space-x-2 text-gray-300">
              <span className="text-salmon">[{log.stage_number || '0'}/6]</span>
              <span className="text-gray-400">[{log.stage}]</span>
              <span>{log.message}</span>
            </div>
          ))}
          {isError && errorMessage && (
            <div className="text-red-400 font-semibold">
              [FATAL ERROR] {errorMessage}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
