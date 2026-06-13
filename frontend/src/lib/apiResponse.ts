/**
 * Backend list responses are wrapped as:
 * { success, status_code, data: T[] }
 * Dict responses only add success/status_code on the same object.
 */
export function unwrapApiPayload<T = unknown>(body: unknown): T {
  if (body === null || body === undefined) {
    return body as T;
  }

  if (!isListWrapper(body)) {
    return body as T;
  }

  return (body as { data: T }).data;
}

function isListWrapper(body: unknown): body is {
  success: boolean;
  status_code: number;
  data: unknown;
} {
  if (!body || typeof body !== 'object' || Array.isArray(body)) {
    return false;
  }

  const record = body as Record<string, unknown>;
  const keys = Object.keys(record);
  if (!keys.includes('success') || !keys.includes('status_code') || !keys.includes('data')) {
    return false;
  }

  // Only unwrap the standard 3-field list envelope from the API normalizer.
  if (keys.length > 3) {
    return false;
  }

  return Array.isArray(record.data) || record.data === null;
}

/** Coerce unknown API values to arrays for .map() in UI. */
export function asArray<T>(value: unknown): T[] {
  if (Array.isArray(value)) {
    return value;
  }
  if (value && typeof value === 'object' && Array.isArray((value as { data?: unknown }).data)) {
    return (value as { data: T[] }).data;
  }
  return [];
}
