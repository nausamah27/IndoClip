'use client';

import React, { useState } from 'react';
import { X, Sparkles, RefreshCw, Palette, Check } from 'lucide-react';
import { ClipResultItem, SubtitleColor, WordTiming } from '../types';
import { apiFetch } from '../utils/api';

interface SubtitleEditorModalProps {
  clip: ClipResultItem;
  jobId: string;
  onClose: () => void;
  onUpdatedClip: (updatedClip: ClipResultItem) => void;
}

export const SubtitleEditorModal: React.FC<SubtitleEditorModalProps> = ({
  clip,
  jobId,
  onClose,
  onUpdatedClip,
}) => {
  const [hookBanner, setHookBanner] = useState(clip.hook_banner);
  const [subtitleColor, setSubtitleColor] = useState<SubtitleColor>('OPUS_GREEN');
  const [words, setWords] = useState<WordTiming[]>(clip.corrected_words || []);
  const [fullText, setFullText] = useState(
    (clip.corrected_words || []).map((w) => w.word).join(' ')
  );
  const [isReRendering, setIsReRendering] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleWordChange = (index: number, newText: string) => {
    const updated = [...words];
    updated[index].word = newText;
    setWords(updated);
    setFullText(updated.map((w) => w.word).join(' '));
  };

  const handleFullTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newFullText = e.target.value;
    setFullText(newFullText);
    const newWordList = newFullText.split(/\s+/).filter(Boolean);
    
    // Sinkronisasi kata dengan timestamp yang ada
    const syncedWords: WordTiming[] = newWordList.map((w, idx) => {
      if (words[idx]) {
        return { ...words[idx], word: w };
      }
      // Kata tambahan di akhir
      const lastWord = words[words.length - 1];
      const start = lastWord ? lastWord.end : 0.0;
      return { word: w, start, end: start + 0.3, probability: 1.0 };
    });
    setWords(syncedWords);
  };

  const handleReRender = async () => {
    setIsReRendering(true);
    setErrorMsg('');
    try {
      const res = await apiFetch('/api/rerender-subtitle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          clip_id: clip.clip_id,
          subtitle_color: subtitleColor,
          hook_banner: hookBanner.trim().toUpperCase(),
          edited_words: words,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Gagal merender ulang subtitle.');
      }

      const data = await res.json();
      onUpdatedClip(data.clip);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Terjadi kesalahan saat re-rendering.');
    } finally {
      setIsReRendering(false);
    }
  };

  const colorOptions: { id: SubtitleColor; label: string; hex: string }[] = [
    { id: 'OPUS_GREEN', label: 'Opus Green', hex: '#00FF66' },
    { id: 'SALMON_PINK', label: 'Salmon Pink', hex: '#FA8072' },
    { id: 'CYBER_YELLOW', label: 'Cyber Yellow', hex: '#FFE600' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fade-in">
      <div className="bg-dark-card border border-dark-border rounded-3xl max-w-2xl w-full p-6 sm:p-8 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-dark-border">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-salmon" />
              <span>Inline Subtitle & Hook Editor</span>
            </h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Edit kata/ejaan bahasa gaul lalu re-render dalam ~2 detik tanpa download ulang video.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white rounded-xl bg-dark-input hover:bg-dark-hover transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Scrollable */}
        <div className="flex-1 overflow-y-auto py-5 space-y-5 pr-1">
          {/* Hook Banner Input */}
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
              🔥 3-Second Hook Banner (Maks 5 Kata Kapital)
            </label>
            <input
              type="text"
              value={hookBanner}
              onChange={(e) => setHookBanner(e.target.value.toUpperCase())}
              placeholder="DETIK-DETIK KETAHUAN BOHONG!"
              className="w-full px-4 py-2.5 bg-dark-input border border-dark-border rounded-xl text-sm font-bold text-white focus:outline-none focus:border-salmon uppercase"
            />
          </div>

          {/* Color Highlight Choice */}
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2 flex items-center space-x-1.5">
              <Palette className="w-3.5 h-3.5 text-salmon" />
              <span>Warna Highlight Kata Aktif</span>
            </label>
            <div className="flex space-x-3">
              {colorOptions.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setSubtitleColor(opt.id)}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl border text-xs font-semibold transition ${
                    subtitleColor === opt.id
                      ? 'border-salmon bg-salmon/15 text-white'
                      : 'border-dark-border bg-dark-input text-gray-400 hover:text-white'
                  }`}
                >
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: opt.hex }}
                  />
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Full Paragraph Editor */}
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
              Teks Transkrip Lengkap
            </label>
            <textarea
              rows={4}
              value={fullText}
              onChange={handleFullTextChange}
              className="w-full p-3.5 bg-dark-input border border-dark-border rounded-xl text-sm text-gray-200 focus:outline-none focus:border-salmon font-sans leading-relaxed"
            />
          </div>

          {/* Interactive Word Pills */}
          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-2">
              Daftar Kata Ber-Timestamp ({words.length} Kata)
            </label>
            <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto p-3 bg-dark-input/60 rounded-2xl border border-dark-border">
              {words.map((w, idx) => (
                <div
                  key={idx}
                  className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-dark-card border border-dark-border text-xs"
                >
                  <input
                    type="text"
                    value={w.word}
                    onChange={(e) => handleWordChange(idx, e.target.value)}
                    className="bg-transparent text-white font-medium focus:outline-none w-auto max-w-[120px]"
                  />
                  <span className="text-[10px] text-gray-500 font-mono">
                    {w.start.toFixed(1)}s
                  </span>
                </div>
              ))}
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400 font-medium">
              {errorMsg}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end space-x-3 pt-4 border-t border-dark-border">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2.5 text-xs font-semibold text-gray-400 hover:text-white rounded-xl transition"
          >
            Batal
          </button>
          <button
            type="button"
            disabled={isReRendering}
            onClick={handleReRender}
            className="flex items-center space-x-2 px-6 py-2.5 rounded-xl text-xs font-bold text-white salmon-gradient shadow-lg shadow-salmon/25 hover:opacity-90 active:scale-95 transition disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isReRendering ? 'animate-spin' : ''}`} />
            <span>{isReRendering ? 'Re-rendering Subtitle...' : 'Re-render Subtitle Sekarang'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
