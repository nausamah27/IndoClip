// Centralized API configuration for IndoClip Pro
// Mendukung localhost maupun deployment remote (Google Colab / Cloudflare / Ngrok)
// Prioritas: 1. localStorage ('CUSTOM_BACKEND_URL') -> 2. process.env.NEXT_PUBLIC_API_URL -> 3. http://127.0.0.1:8000

export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const customUrl = localStorage.getItem('CUSTOM_BACKEND_URL');
    if (customUrl && customUrl.trim() !== '') {
      return customUrl.trim().replace(/\/$/, '');
    }
  }
  if (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim() !== '') {
    return process.env.NEXT_PUBLIC_API_URL.trim().replace(/\/$/, '');
  }
  return 'http://127.0.0.1:8000';
}

// Export getter property for backwards compatibility
export const API_BASE = getApiBase();

export function getFullMediaUrl(url: string | undefined | null): string {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  const base = getApiBase();
  return `${base}${url.startsWith('/') ? '' : '/'}${url}`;
}
