'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from '../components/Navbar';
import { ControlPanel } from '../components/ControlPanel';
import { PipelineTracker } from '../components/PipelineTracker';
import { ClipCard } from '../components/ClipCard';
import { LayoutMode, SubtitleColor, ClipResultItem, PipelineProgressEvent } from '../types';
import { Sparkles, CheckCircle2 } from 'lucide-react';
import { API_BASE } from '../utils/api';

export default function Home() {
  const [apiKey, setApiKey] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJobId, setCurrentJobId] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [logs, setLogs] = useState<PipelineProgressEvent[]>([]);
  const [clips, setClips] = useState<ClipResultItem[]>([]);
  const [videoTitle, setVideoTitle] = useState('');
  const [isCompleted, setIsCompleted] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load API Key & cek job aktif dari localStorage saat refresh halaman
  useEffect(() => {
    const savedKey = localStorage.getItem('GEMINI_API_KEY');
    if (savedKey) setApiKey(savedKey);

    const savedJobId = localStorage.getItem('CURRENT_JOB_ID');
    if (savedJobId) {
      // Cek apakah job tersebut masih berjalan atau sudah selesai
      fetch(`${API_BASE}/api/jobs/${savedJobId}`)
        .then((res) => (res.ok ? res.json() : null))
        .then((jobData) => {
          if (jobData && (jobData.status === 'PROCESSING' || jobData.status === 'COMPLETED')) {
            setCurrentJobId(savedJobId);
            setProgress(jobData.progress || 0);
            setCurrentStage(jobData.current_stage || '');
            setStatusMessage(jobData.message || '');
            if (jobData.video_title) setVideoTitle(jobData.video_title);

            if (jobData.status === 'PROCESSING') {
              setIsProcessing(true);
              startTracking(savedJobId);
            } else if (jobData.status === 'COMPLETED') {
              setIsCompleted(true);
              setClips(jobData.clips || []);
            }
          } else {
            localStorage.removeItem('CURRENT_JOB_ID');
            setIsProcessing(false);
          }
        })
        .catch(() => {
          localStorage.removeItem('CURRENT_JOB_ID');
          setIsProcessing(false);
        });
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  const startTracking = (jobId: string) => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    if (eventSourceRef.current) eventSourceRef.current.close();

    // 1. Dual-Channel: Polling Fallback setiap 1.5 detik (100% tahan buffer proxy)
    pollingRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
        if (!res.ok) {
          if (res.status === 404) {
            setIsProcessing(false);
            setStatusMessage('Job sebelumnya sudah tidak aktif. Silakan masukkan URL dan klik Generate Klip Viral.');
            if (pollingRef.current) clearInterval(pollingRef.current);
            if (eventSourceRef.current) eventSourceRef.current.close();
            localStorage.removeItem('CURRENT_JOB_ID');
          }
          return;
        }
        const data = await res.json();

        if (data.progress > 0) setProgress(data.progress);
        if (data.current_stage) setCurrentStage(data.current_stage);
        if (data.message) setStatusMessage(data.message);
        if (data.video_title) setVideoTitle(data.video_title);

        if (data.status === 'COMPLETED') {
          setIsProcessing(false);
          setIsCompleted(true);
          setClips(data.clips || []);
          if (pollingRef.current) clearInterval(pollingRef.current);
          if (eventSourceRef.current) eventSourceRef.current.close();
        } else if (data.status === 'FAILED') {
          setIsProcessing(false);
          setIsError(true);
          setErrorMessage(data.error || 'Terjadi kesalahan sistem.');
          if (pollingRef.current) clearInterval(pollingRef.current);
          if (eventSourceRef.current) eventSourceRef.current.close();
        }
      } catch {
        // Abaikan error polling sementara
      }
    }, 1500);

    // 2. Real-Time Server-Sent Events (SSE) langsung ke 127.0.0.1:8000
    try {
      const eventSource = new EventSource(`${API_BASE}/api/progress/${jobId}`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const evtData: PipelineProgressEvent = JSON.parse(event.data);
          if (evtData.progress) setProgress(evtData.progress);
          if (evtData.stage) setCurrentStage(evtData.stage);
          if (evtData.message) setStatusMessage(evtData.message);

          setLogs((prev) => {
            if (prev.length > 0 && prev[prev.length - 1].message === evtData.message) {
              return prev;
            }
            return [...prev, evtData];
          });

          if (evtData.data?.title) {
            setVideoTitle(evtData.data.title);
          }

          if (evtData.stage === 'COMPLETED') {
            setIsProcessing(false);
            setIsCompleted(true);
            if (pollingRef.current) clearInterval(pollingRef.current);
            eventSource.close();

            fetch(`${API_BASE}/api/jobs/${jobId}`)
              .then((r) => r.json())
              .then((jobData) => {
                setClips(jobData.clips || []);
                if (jobData.video_title) setVideoTitle(jobData.video_title);
              });
          }

          if (evtData.stage === 'ERROR') {
            setIsProcessing(false);
            setIsError(true);
            setErrorMessage(evtData.message || 'Terjadi kesalahan sistem.');
            if (pollingRef.current) clearInterval(pollingRef.current);
            eventSource.close();
          }
        } catch {
          // Keep-alive ping
        }
      };

      eventSource.onerror = () => {
        // Jika SSE terputus, polling timer tetap berjalan terus di background
      };
    } catch {
      // Fallback tetap mengandalkan polling timer
    }
  };

  const handleStartProcess = async (params: {
    youtubeUrl: string;
    layoutMode: LayoutMode;
    subtitleColor: SubtitleColor;
  }) => {
    setIsProcessing(true);
    setIsCompleted(false);
    setIsError(false);
    setErrorMessage('');
    setProgress(5);
    setCurrentStage('INIT');
    setStatusMessage('Mengirim permintaan ke backend IndoClip Pro...');
    setLogs([]);
    setClips([]);
    setVideoTitle('');

    try {
      const response = await fetch(`${API_BASE}/api/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          youtube_url: params.youtubeUrl,
          gemini_api_key: apiKey || undefined,
          layout_mode: params.layoutMode,
          subtitle_color: params.subtitleColor,
          language: 'id',
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Gagal memulai pipeline pemrosesan.');
      }

      const data = await response.json();
      const jobId = data.job_id;
      setCurrentJobId(jobId);
      localStorage.setItem('CURRENT_JOB_ID', jobId);

      // Mulai tracking real-time
      startTracking(jobId);
    } catch (err: any) {
      setIsProcessing(false);
      setIsError(true);
      setErrorMessage(err.message || 'Gagal terhubung ke server backend.');
    }
  };

  const handleClipUpdated = (updatedClip: ClipResultItem) => {
    setClips((prevClips) =>
      prevClips.map((c) =>
        c.clip_id === updatedClip.clip_id ? updatedClip : c
      )
    );
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar apiKey={apiKey} setApiKey={setApiKey} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-16">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-salmon/10 border border-salmon/25 text-salmon text-xs font-semibold mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Kloningan 100% Fitur OpusClip Khusus Kreator Indonesia</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight">
            Potong Video Panjang Jadi{' '}
            <span className="salmon-text-gradient">Shorts & TikTok Viral</span>
          </h1>

          <p className="mt-5 text-base sm:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
            Otomatis deteksi tawa & klimaks audio, transkripsi gaul Bahasa Indonesia, kurasi hook Gemini 2.5 Flash, dan reframing cerdas MediaPipe. 0 Budget di localhost.
          </p>

          {/* Quick Stats Badges */}
          <div className="flex flex-wrap items-center justify-center gap-6 mt-8 text-xs text-gray-400">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-salmon" />
              <span>Audio Peaks Detection</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-green-400" />
              <span>faster-whisper Bahasa Indo</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-purple-400" />
              <span>Gemini 2.5 Flash Scoring</span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-blue-400" />
              <span>MediaPipe 9:16 Reframing</span>
            </div>
          </div>
        </div>

        {/* Control Panel */}
        <ControlPanel
          onStartProcess={handleStartProcess}
          isProcessing={isProcessing}
        />

        {/* Pipeline Tracker */}
        {(isProcessing || isCompleted || isError) && (
          <PipelineTracker
            progress={progress}
            currentStage={currentStage}
            message={statusMessage}
            logs={logs}
            isCompleted={isCompleted}
            isError={isError}
            errorMessage={errorMessage}
          />
        )}

        {/* Results Section */}
        {clips.length > 0 && (
          <div className="mt-16 sm:mt-20">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-8 pb-4 border-b border-dark-border gap-4">
              <div>
                <span className="text-xs font-bold text-salmon tracking-wider uppercase">
                  Hasil Kurasi Video Viral
                </span>
                <h2 className="text-2xl sm:text-3xl font-black text-white mt-1">
                  {videoTitle || 'Daftar Klip Viral IndoClip Pro'}
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  Ditemukan {clips.length} klip berpotensi tinggi dengan hook kuat & alur cerita utuh.
                </p>
              </div>

              <div className="flex items-center space-x-2 text-xs font-medium text-gray-300">
                <CheckCircle2 className="w-4 h-4 text-green-400" />
                <span>Format 1080x1920 Vertikal 9:16 Siap Ekspor</span>
              </div>
            </div>

            {/* Clips List */}
            <div className="space-y-6">
              {clips.map((clip) => (
                <ClipCard
                  key={clip.clip_id}
                  clip={clip}
                  jobId={currentJobId}
                  onClipUpdated={handleClipUpdated}
                />
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-border py-8 text-center text-xs text-gray-500 mt-20">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-2 text-gray-400">
            <span className="font-bold text-white">IndoClip Pro</span>
            <span>•</span>
            <span>Local 0 Budget OpusClip for Indonesian Content Creators</span>
          </div>
          <p>© 2026 IndoClip Pro. Built for Windows localhost with Next.js, FastAPI & FFmpeg.</p>
        </div>
      </footer>
    </div>
  );
}
