// Centralized API configuration for IndoClip Pro
// Mendukung localhost maupun deployment remote (Google Colab / Cloudflare / Ngrok) via NEXT_PUBLIC_API_URL
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim() !== ''
    ? process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, '')
    : 'http://127.0.0.1:8000';

export function getFullMediaUrl(url: string | undefined | null): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  return `${API_BASE}${url.startsWith('/') ? '' : '/'}${url}`;
}
