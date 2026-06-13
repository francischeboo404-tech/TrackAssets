const ACCESS_KEY = 'trackit_access_token';
const REFRESH_KEY = 'trackit_refresh_token';

export function setAuthTokens(
  access?: string | null,
  refresh?: string | null,
): void {
  if (access) {
    sessionStorage.setItem(ACCESS_KEY, access);
  } else {
    sessionStorage.removeItem(ACCESS_KEY);
  }

  if (refresh) {
    sessionStorage.setItem(REFRESH_KEY, refresh);
  } else if (refresh === null) {
    sessionStorage.removeItem(REFRESH_KEY);
  }
}

export function clearAuthTokens(): void {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_KEY);
}

export function hasStoredSession(): boolean {
  return !!(getAccessToken() || getRefreshToken());
}
