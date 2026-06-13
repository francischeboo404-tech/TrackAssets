import { baseWithApi } from '../services/api';

/**
 * Resolve backend static asset URLs (logos, uploads).
 * Works in dev (Vite proxy), production API host, and Render/Vercel splits.
 */
export function resolveStaticUrl(path?: string | null): string {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }

  const apiBase = baseWithApi.replace(/\/api\/?$/, '');
  const origin =
    apiBase && apiBase !== '/api'
      ? apiBase
      : typeof window !== 'undefined'
        ? window.location.origin
        : '';

  return `${origin}${path.startsWith('/') ? path : `/${path}`}`;
}
