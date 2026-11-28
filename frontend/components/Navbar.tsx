'use client';

import React, { useState, useEffect } from 'react';
import { Flame, Cpu, Key, CheckCircle, AlertCircle, Settings2, Sparkles, Server, Globe, ExternalLink, RefreshCw } from 'lucide-react';
import { getApiBase, apiFetch, DEFAULT_API_URL } from '../utils/api';

interface NavbarProps {
  apiKey: string;
  setApiKey: (key: string) => void;
  onBackendChange?: (newUrl: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ apiKey, setApiKey, onBackendChange }) => {
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [showServerModal, setShowServerModal] = useState(false);
  const [inputKey, setInputKey] = useState(apiKey);
  const [currentBackendUrl, setCurrentBackendUrl] = useState('');
  const [inputBackendUrl, setInputBackendUrl] = useState('');
  const [isTestingServer, setIsTestingServer] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; msg: string } | null>(null);

  const [systemHealth, setSystemHealth] = useState<{
    status: string;
    cuda_device?: string;
    compute_type?: string;
    default_whisper_model?: string;
  } | null>(null);

  const checkHealth = (url?: string) => {
    const targetUrl = url || getApiBase();
    apiFetch(`${targetUrl}/api/health`, { method: 'GET' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.status === 'online') {
          setSystemHealth(data);
        } else {
          setSystemHealth({ status: 'offline' });
        }
      })
      .catch(() => setSystemHealth({ status: 'offline' }));
  };

  useEffect(() => {
    const base = getApiBase();
    setCurrentBackendUrl(base);
    setInputBackendUrl(base);
    checkHealth(base);
  }, []);

  const handleSaveKey = () => {
    setApiKey(inputKey);
    localStorage.setItem('GEMINI_API_KEY', inputKey);
    setShowKeyModal(false);
  };

  const handleTestAndSaveBackend = async () => {
    const cleanUrl = inputBackendUrl.trim().replace(/\/$/, '');
    if (!cleanUrl) return;

    setIsTestingServer(true);
    setTestResult(null);

    try {
      const res = await apiFetch(`${cleanUrl}/api/health`, { method: 'GET' });
      if (!res.ok) {
        throw new Error(`Server membalas dengan status: ${res.status}`);
      }
      const healthData = await res.json();
      localStorage.setItem('CUSTOM_BACKEND_URL', cleanUrl);
      setCurrentBackendUrl(cleanUrl);
      setSystemHealth(healthData);
      setTestResult({
        success: true,
        msg: `Koneksi Berhasil! Terhubung ke backend (${healthData.cuda_device?.toUpperCase() || 'Online'}).`,
      });
      if (onBackendChange) onBackendChange(cleanUrl);
      setTimeout(() => setShowServerModal(false), 1500);
    } catch (err: any) {
      setTestResult({
        success: false,
        msg: `Gagal terhubung ke ${cleanUrl}. Pastikan server backend / tunnel Ngrok aktif.`,
      });
    } finally {
      setIsTestingServer(false);
    }
  };

  const isOnline = systemHealth?.status === 'online';

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
                0 Budget
              </span>
            </div>
            <p className="text-xs text-gray-400">
              OpusClip Alternative for Indonesian Creators
            </p>
          </div>
        </div>

        {/* Right Status Badges & Settings */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Backend Connection Indicator & Modal Trigger */}
          <button
            onClick={() => {
              setInputBackendUrl(getApiBase());
              setTestResult(null);
              setShowServerModal(true);
            }}
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
              isOnline
                ? 'bg-dark-card border-green-500/30 text-green-400 hover:bg-dark-hover'
                : 'bg-red-500/10 border-red-500/40 text-red-400 hover:bg-red-500/20'
            }`}
            title="Klik untuk konfigurasi URL Server Backend jika diperlukan"
          >
            <Server className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">
              Backend:{' '}
              {isOnline
                ? systemHealth?.cuda_device
                  ? `${systemHealth.cuda_device.toUpperCase()} (GPU)`
                  : 'Online (CPU)'
                : 'Offline / Set URL'}
            </span>
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isOnline ? 'bg-green-400 animate-pulse' : 'bg-red-500'
              }`}
            />
          </button>

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
            <span className="hidden sm:inline">
              {apiKey ? 'Gemini Key Configured' : 'Set Gemini API Key'}
            </span>
          </button>
        </div>
      </div>

      {/* Modal Setup Backend Server URL */}
      {showServerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-dark-card border border-dark-border rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center space-x-3 mb-4">
              <div className="p-2.5 rounded-xl bg-salmon/15 text-salmon">
                <Globe className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Hubungkan Backend Server</h3>
                <p className="text-xs text-gray-400">
                  Backend default otomatis terhubung ke domain statis Ngrok.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Backend API URL:
                </label>
                <input
                  type="url"
                  value={inputBackendUrl}
                  onChange={(e) => setInputBackendUrl(e.target.value)}
                  placeholder="https://brunette-crimson-yen.ngrok-free.dev"
                  className="w-full px-3.5 py-2.5 bg-dark-input border border-dark-border rounded-xl text-sm text-white focus:outline-none focus:border-salmon font-mono"
                />
                <p className="text-[11px] text-gray-400 mt-1.5 leading-relaxed">
                  💡 <strong>Default Otomatis:</strong> Aplikasi default terhubung ke domain statis Ngrok Anda: <code className="text-salmon">{DEFAULT_API_URL}</code>.
                </p>
              </div>

              {testResult && (
                <div
                  className={`p-3 rounded-xl border text-xs font-medium ${
                    testResult.success
                      ? 'bg-green-500/10 border-green-500/30 text-green-400'
                      : 'bg-red-500/10 border-red-500/30 text-red-400'
                  }`}
                >
                  {testResult.msg}
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <div className="flex space-x-3 text-xs">
                  <button
                    type="button"
                    onClick={() => {
                      setInputBackendUrl(DEFAULT_API_URL);
                    }}
                    className="text-gray-400 hover:text-salmon underline"
                  >
                    Reset ke Ngrok Statis
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setInputBackendUrl('http://127.0.0.1:8000');
                    }}
                    className="text-gray-500 hover:text-gray-300 underline"
                  >
                    Localhost (8000)
                  </button>
                </div>

                <div className="flex space-x-2">
                  <button
                    onClick={() => setShowServerModal(false)}
                    className="px-4 py-2 text-xs font-medium text-gray-400 hover:text-white rounded-lg transition"
                  >
                    Tutup
                  </button>
                  <button
                    disabled={isTestingServer || !inputBackendUrl.trim()}
                    onClick={handleTestAndSaveBackend}
                    className="flex items-center space-x-2 px-5 py-2 text-xs font-semibold text-white salmon-gradient rounded-xl shadow-md hover:opacity-90 disabled:opacity-50 transition"
                  >
                    {isTestingServer && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>{isTestingServer ? 'Menguji...' : 'Uji & Simpan URL'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

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
                  API Key (gemini-3.8-flash)
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
