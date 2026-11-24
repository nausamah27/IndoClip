'use client';

import React, { useState } from 'react';
import { Youtube, Sparkles, Wand2, Users, Gamepad2, User, Palette, Play } from 'lucide-react';
import { LayoutMode, SubtitleColor } from '../types';

interface ControlPanelProps {
  onStartProcess: (params: {
    youtubeUrl: string;
    layoutMode: LayoutMode;
    subtitleColor: SubtitleColor;
  }) => void;
  isProcessing: boolean;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  onStartProcess,
  isProcessing,
}) => {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('AUTO');
  const [subtitleColor, setSubtitleColor] = useState<SubtitleColor>('OPUS_GREEN');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;
    onStartProcess({
      youtubeUrl: youtubeUrl.trim(),
      layoutMode,
      subtitleColor,
    });
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) setYoutubeUrl(text);
    } catch {
      // Fallback
    }
  };

  const layoutOptions: { id: LayoutMode; label: string; desc: string; icon: React.ReactNode }[] = [
    {
      id: 'AUTO',
      label: 'Auto Detect',
      desc: 'AI MediaPipe otomatis deteksi Podcast/Gaming/Solo',
      icon: <Wand2 className="w-4 h-4 text-salmon" />,
    },
    {
      id: 'PODCAST',
      label: 'Podcast Multi-Speaker',
      desc: 'Split-Screen 2 Wajah / Active Speaker Switching',
      icon: <Users className="w-4 h-4 text-purple-400" />,
    },
    {
      id: 'GAMING',
      label: 'Gaming Facecam',
      desc: 'Facecam Streamer atas (620px) + Gameplay bawah (1300px)',
      icon: <Gamepad2 className="w-4 h-4 text-green-400" />,
    },
    {
      id: 'SOLO',
      label: 'Solo Creator',
      desc: 'Dynamic Face Tracking halus dengan EMA smoothing',
      icon: <User className="w-4 h-4 text-blue-400" />,
    },
  ];

  const colorOptions: { id: SubtitleColor; label: string; bg: string; border: string; hex: string }[] = [
    {
      id: 'OPUS_GREEN',
      label: 'Opus Green',
      bg: 'bg-[#00FF66]/20',
      border: 'border-[#00FF66]',
      hex: '#00FF66',
    },
    {
      id: 'SALMON_PINK',
      label: 'Salmon Pink',
      bg: 'bg-salmon/20',
      border: 'border-salmon',
      hex: '#FA8072',
    },
    {
      id: 'CYBER_YELLOW',
      label: 'Cyber Yellow',
      bg: 'bg-[#FFE600]/20',
      border: 'border-[#FFE600]',
      hex: '#FFE600',
    },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto glass-panel p-6 sm:p-8 rounded-3xl shadow-2xl relative overflow-hidden">
      {/* Decorative gradient blur */}
      <div className="absolute -top-24 -left-24 w-60 h-60 bg-salmon/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-24 -right-24 w-60 h-60 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      <form onSubmit={handleSubmit} className="space-y-6 relative z-10">
        {/* Main URL Input Bar */}
        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-2">
            Link Video YouTube (Podcast, Gaming, Reaction, Storytelling)
          </label>
          <div className="relative flex items-center">
            <div className="absolute left-4 text-red-500 pointer-events-none">
              <Youtube className="w-6 h-6" />
            </div>
            <input
              type="url"
              required
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              disabled={isProcessing}
              className="w-full pl-13 pr-24 py-4 bg-dark-input/90 border border-dark-border rounded-2xl text-base text-white placeholder-gray-500 focus:outline-none focus:border-salmon focus:ring-2 focus:ring-salmon/20 transition-all shadow-inner"
            />
            <button
              type="button"
              onClick={handlePaste}
              disabled={isProcessing}
              className="absolute right-3 px-3 py-1.5 bg-dark-card hover:bg-dark-hover text-xs font-medium text-gray-300 hover:text-white rounded-xl border border-dark-border transition"
            >
              Paste URL
            </button>
          </div>
        </div>

        {/* Layout Mode Selector */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2.5">
            Pilih Mode Reframing Video 9:16
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {layoutOptions.map((opt) => {
              const isSelected = layoutMode === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  disabled={isProcessing}
                  onClick={() => setLayoutMode(opt.id)}
                  className={`p-3.5 rounded-2xl border text-left transition-all relative ${
                    isSelected
                      ? 'bg-dark-card border-salmon ring-1 ring-salmon/40 shadow-lg shadow-salmon/10'
                      : 'bg-dark-input/60 border-dark-border hover:border-gray-600 hover:bg-dark-card/50'
                  }`}
                >
                  <div className="flex items-center space-x-2.5 mb-1.5">
                    <div className="p-1.5 rounded-lg bg-dark-bg border border-dark-border">
                      {opt.icon}
                    </div>
                    <span className="text-xs font-bold text-white">{opt.label}</span>
                  </div>
                  <p className="text-[11px] text-gray-400 leading-relaxed line-clamp-2">
                    {opt.desc}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Subtitle Highlight Color Selector */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2.5 flex items-center space-x-2">
            <Palette className="w-3.5 h-3.5 text-salmon" />
            <span>Warna Highlight Subtitle Animasi (.ass)</span>
          </label>
          <div className="flex flex-wrap gap-3">
            {colorOptions.map((col) => {
              const isSelected = subtitleColor === col.id;
              return (
                <button
                  key={col.id}
                  type="button"
                  disabled={isProcessing}
                  onClick={() => setSubtitleColor(col.id)}
                  className={`flex items-center space-x-2.5 px-4 py-2 rounded-xl border text-xs font-semibold transition-all ${
                    isSelected
                      ? `${col.bg} ${col.border} text-white ring-1 ring-white/20 shadow-md`
                      : 'bg-dark-input/60 border-dark-border text-gray-400 hover:text-white'
                  }`}
                >
                  <span
                    className="w-3 h-3 rounded-full border border-black/40 shadow-sm"
                    style={{ backgroundColor: col.hex }}
                  />
                  <span>{col.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* CTA Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isProcessing || !youtubeUrl.trim()}
            className={`w-full py-4 rounded-2xl text-base font-bold text-white shadow-xl transition-all flex items-center justify-center space-x-3 ${
              isProcessing || !youtubeUrl.trim()
                ? 'bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-700'
                : 'salmon-gradient hover:opacity-95 shadow-salmon/30 hover:shadow-salmon/50 active:scale-[0.99] cursor-pointer'
            }`}
          >
            <Sparkles className="w-5 h-5 text-white animate-spin-slow" />
            <span>
              {isProcessing
                ? 'Sedang Memproses Pipeline AI...'
                : 'Generate Klip Viral Vertikal 9:16 Sekarang'}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
};
