// Centralized API configuration for IndoClip Pro
// Mendukung localhost maupun deployment remote (Google Colab / Cloudflare / Ngrok)
// Prioritas: 1. localStorage ('CUSTOM_BACKEND_URL') -> 2. process.env.NEXT_PUBLIC_API_URL -> 3. https://brunette-crimson-yen.ngrok-free.dev

export const DEFAULT_API_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://brunette-crimson-yen.ngrok-free.dev';

export function getApiBase(): string {
  if (typeof window !== 'undefined') {
    const customUrl = localStorage.getItem('CUSTOM_BACKEND_URL');
    if (customUrl && customUrl.trim() !== '') {
      return customUrl.trim().replace(/\/$/, '');
    }
  }
  return DEFAULT_API_URL.replace(/\/$/, '');
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

/**
 * Fetch wrapper dengan otomatis menyertakan header 'ngrok-skip-browser-warning': 'true'
 * untuk membypass halaman interstitial / peringatan browser Ngrok gratis.
 */
export async function apiFetch(
  endpointOrUrl: string,
  init?: RequestInit
): Promise<Response> {
  const base = getApiBase();
  const url =
    endpointOrUrl.startsWith('http://') || endpointOrUrl.startsWith('https://')
      ? endpointOrUrl
      : `${base}${endpointOrUrl.startsWith('/') ? '' : '/'}${endpointOrUrl}`;

  const headers = new Headers(init?.headers);
  if (!headers.has('ngrok-skip-browser-warning')) {
    headers.set('ngrok-skip-browser-warning', 'true');
  }

  return fetch(url, {
    ...init,
    headers,
  });
}

/**
 * Mengunduh media (video/gambar) via fetch dengan bypass ngrok warning,
 * lalu mengubahnya menjadi object URL (blob:) untuk pemutaran tanpa blokir.
 */
export async function fetchBlobWithNgrokBypass(mediaUrl: string): Promise<string> {
  const fullUrl = getFullMediaUrl(mediaUrl);
  const res = await apiFetch(fullUrl);
  if (!res.ok) {
    throw new Error(`Gagal memuat media: ${res.statusText}`);
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
