'use client';

import React, { useState, useEffect } from 'react';
import { Flame, Cpu, Key, CheckCircle, AlertCircle, Settings2, Sparkles } from 'lucide-react';
import { API_BASE } from '../utils/api';

interface NavbarProps {
  apiKey: string;
  setApiKey: (key: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ apiKey, setApiKey }) => {
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [inputKey, setInputKey] = useState(apiKey);
  const [systemHealth, setSystemHealth] = useState<{
    status: string;
    cuda_device?: string;
    compute_type?: string;
    default_whisper_model?: string;
  } | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then((data) => setSystemHealth(data))
      .catch(() => setSystemHealth({ status: 'offline' }));
  }, []);

  const handleSaveKey = () => {
    setApiKey(inputKey);
    localStorage.setItem('GEMINI_API_KEY', inputKey);
    setShowKeyModal(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-dark-border bg-dark-bg/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo & Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl salmon-gradient flex items-center justify-center shadow-lg shadow-salmon/25">
            <Flame className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-white">
                Indo<span className="salmon-text-gradient">Clip Pro</span>
              </span>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-salmon/15 text-salmon border border-salmon/30">
                0 Budget Local
              </span>
            </div>
            <p className="text-xs text-gray-400">
              OpusClip Alternative for Indonesian Creators
            </p>
          </div>
        </div>

        {/* Right Status Badges & Settings */}
        <div className="flex items-center space-x-3">
          {/* Device Hardware Indicator */}
          <div className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-dark-card border border-dark-border text-xs">
            <Cpu className="w-4 h-4 text-salmon" />
            <span className="text-gray-300">
              Hardware:{' '}
              <strong className="text-white">
                {systemHealth?.cuda_device ? `${systemHealth.cuda_device.toUpperCase()} (GPU)` : 'CPU (int8)'}
              </strong>
            </span>
            <span className="inline-block w-2 h-2 rounded-full bg-opusGreen animate-pulse ml-1" />
          </div>

          {/* Gemini API Key Button */}
          <button
            onClick={() => setShowKeyModal(true)}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              apiKey
                ? 'bg-dark-card border-green-500/30 text-green-400 hover:bg-dark-hover'
                : 'bg-salmon/10 border-salmon/40 text-salmon hover:bg-salmon/20'
            }`}
          >
            <Key className="w-3.5 h-3.5" />
            <span>{apiKey ? 'Gemini Key Configured' : 'Set Gemini API Key'}</span>
          </button>
        </div>
      </div>

      {/* Modal Setup API Key */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-dark-card border border-dark-border rounded-2xl max-w-md w-full p-6 shadow-2xl animate-fade-in">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2 rounded-lg bg-salmon/15 text-salmon">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Google Gemini API Key</h3>
                <p className="text-xs text-gray-400">
                  Digunakan untuk kurasi momen viral & copywriting bahasa gaul.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  API Key (gemini-2.5-flash)
                </label>
                <input
                  type="password"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  placeholder="AIzaSy..."
                  className="w-full px-3.5 py-2.5 bg-dark-input border border-dark-border rounded-xl text-sm text-white focus:outline-none focus:border-salmon"
                />
                <p className="text-[11px] text-gray-400 mt-1.5">
                  Tersimpan secara lokal di browser Anda. Dapatkan gratis di{' '}
                  <a
                    href="https://aistudio.google.com"
                    target="_blank"
                    rel="noreferrer"
                    className="text-salmon hover:underline font-medium"
                  >
                    Google AI Studio
                  </a>.
                </p>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  onClick={() => setShowKeyModal(false)}
                  className="px-4 py-2 text-xs font-medium text-gray-400 hover:text-white rounded-lg transition"
                >
                  Batal
                </button>
                <button
                  onClick={handleSaveKey}
                  className="px-5 py-2 text-xs font-semibold text-white salmon-gradient rounded-lg shadow-md hover:opacity-90 transition"
                >
                  Simpan Key
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
