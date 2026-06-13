import axios from 'axios';
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  hasStoredSession,
  setAuthTokens,
} from '../lib/authStorage';
import { unwrapApiPayload } from '../lib/apiResponse';

declare module 'axios' {
  export interface AxiosRequestConfig {
    skipAuthRedirect?: boolean;
    _retry?: boolean;
  }
}

// Choose a sensible default: prefer VITE_API_URL, otherwise
// when running on Vercel use the known Render backend, else use local '/api'.
const resolvedBase = (() => {
  const envBase = import.meta.env.VITE_API_URL;
  if (envBase) {
    return envBase;
  }
  if (typeof window !== 'undefined' && window.location.hostname.includes('vercel.app')) {
    return 'https://trackit-uxil.onrender.com';
  }
  return '/api';
})();

export const baseWithApi = (() => {
  try {
    if (resolvedBase === '/api') return resolvedBase;
    if (resolvedBase.endsWith('/api')) return resolvedBase.replace(/\/+$/, '');
    return resolvedBase.replace(/\/+$/, '') + '/api';
  } catch {
    return resolvedBase;
  }
})();

const api = axios.create({
  baseURL: baseWithApi,
  withCredentials: true,
  xsrfCookieName: 'csrf_access_token',
  xsrfHeaderName: 'X-CSRF-TOKEN',
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshPromise: Promise<void> | null = null;

function persistTokensFromResponse(data: Record<string, unknown> | undefined) {
  if (!data) {
    return;
  }
  const access = typeof data.access_token === 'string' ? data.access_token : null;
  const refresh = typeof data.refresh_token === 'string' ? data.refresh_token : undefined;
  if (access || refresh !== undefined) {
    setAuthTokens(access, refresh ?? getRefreshToken());
  }
}

async function refreshSession(): Promise<void> {
  if (!hasStoredSession()) {
    return;
  }

  if (!refreshPromise) {
    refreshPromise = api
      .post('/auth/refresh', {}, { skipAuthRedirect: true })
      .then((response) => {
        persistTokensFromResponse(response.data);
        if (response.data?.refreshed === false) {
          clearAuthTokens();
        }
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

function shouldRedirectOn401(config?: { skipAuthRedirect?: boolean; url?: string }) {
  if (config?.skipAuthRedirect) {
    return false;
  }
  if (typeof window === 'undefined') {
    return false;
  }
  return !window.location.pathname.includes('/login')
    && !window.location.pathname.includes('/register');
}

api.interceptors.request.use((config) => {
  const path = config.url || '';
  if (path.includes('/auth/refresh')) {
    const refresh = getRefreshToken();
    if (refresh) {
      config.headers.Authorization = `Bearer ${refresh}`;
    }
  } else if (!path.includes('/auth/login') && !path.includes('/auth/register-org')) {
    const access = getAccessToken();
    if (access) {
      config.headers.Authorization = `Bearer ${access}`;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if (response.data !== undefined) {
      response.data = unwrapApiPayload(response.data);
    }
    if (response.config.url?.includes('/auth/login')) {
      persistTokensFromResponse(
        response.data as Record<string, unknown> | undefined,
      );
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const bodyStatus = error.response?.data?.status_code;

    if (
      originalRequest
      && !originalRequest._retry
      && (status === 401 || bodyStatus === 401)
      && !originalRequest.url?.includes('/auth/login')
      && !originalRequest.url?.includes('/auth/register-org')
      && !originalRequest.url?.includes('/auth/refresh')
      && !originalRequest.url?.includes('/auth/me')
      && hasStoredSession()
    ) {
      originalRequest._retry = true;
      try {
        await refreshSession();
        return api(originalRequest);
      } catch {
        clearAuthTokens();
        if (shouldRedirectOn401(originalRequest)) {
          window.location.href = '/login';
        }
      }
    } else if ((status === 401 || bodyStatus === 401) && shouldRedirectOn401(originalRequest)) {
      window.location.href = '/login';
    }

    if (status === 403 || bodyStatus === 403) {
      const message =
        error.response?.data?.message ||
        'You do not have permission to perform this action.';
      error.forbiddenMessage = message;
    }

    return Promise.reject(error);
  }
);

export { clearAuthTokens, refreshSession, setAuthTokens };
export default api;
