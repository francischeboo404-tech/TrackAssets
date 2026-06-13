import type { AxiosResponse } from 'axios';
import api from '../services/api';

function filenameFromDisposition(
  disposition: string | undefined,
  fallback: string,
): string {
  if (!disposition) return fallback;
  const quoted = disposition.match(/filename="([^"]+)"/i);
  if (quoted?.[1]) return quoted[1];
  const plain = disposition.match(/filename=([^;\s]+)/i);
  if (plain?.[1]) return plain[1].replace(/"/g, '');
  return fallback;
}

/**
 * Authenticated file download (JWT cookies). Prefer over window.open for protected routes.
 */
export async function downloadAuthenticatedFile(
  path: string,
  params: Record<string, string> = {},
  fallbackFilename = 'download',
  method: 'GET' | 'POST' = 'GET',
): Promise<void> {
  const config = { params, responseType: 'blob' as const };
  const response: AxiosResponse<Blob> =
    method === 'POST'
      ? await api.post(path, {}, config)
      : await api.get(path, config);

  const filename = filenameFromDisposition(
    response.headers['content-disposition'],
    fallbackFilename,
  );
  const rawType = response.headers['content-type'];
  const contentType =
    typeof rawType === 'string' ? rawType : 'application/octet-stream';

  const url = window.URL.createObjectURL(
    new Blob([response.data], { type: contentType }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
