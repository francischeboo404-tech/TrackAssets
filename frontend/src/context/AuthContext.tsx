import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api, { clearAuthTokens } from '../services/api';
import { hasStoredSession } from '../lib/authStorage';

interface User {
  id: number;
  username: string;
  role: string;
  organisation_id: number;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string, userData: User) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function mapUserPayload(data: Record<string, unknown> | null | undefined): User | null {
  if (!data || typeof data.id !== 'number') {
    return null;
  }

  return {
    id: data.id,
    username: String(data.username ?? ''),
    role: String(data.role ?? 'staff'),
    organisation_id: Number(data.organisation_id ?? 0),
  };
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const checkSession = useCallback(async () => {
    const sessionConfig = { skipAuthRedirect: true } as const;

    try {
      const resp = await api.get('/auth/me', sessionConfig);
      const payload = resp.data as Record<string, unknown>;

      if (payload?.authenticated === false) {
        if (!hasStoredSession()) {
          setUser(null);
          return;
        }
      } else {
        const mapped = mapUserPayload(payload.user ? (payload.user as Record<string, unknown>) : payload);
        if (mapped) {
          setUser(mapped);
          return;
        }
      }
    } catch {
      if (!hasStoredSession()) {
        setUser(null);
        return;
      }
    }

    if (hasStoredSession()) {
      try {
        const refreshResp = await api.post('/auth/refresh', {}, sessionConfig);
        if (refreshResp.data?.refreshed === false) {
          clearAuthTokens();
          setUser(null);
          return;
        }

        const retry = await api.get('/auth/me', sessionConfig);
        const retryPayload = retry.data as Record<string, unknown>;
        if (retryPayload?.authenticated === false) {
          clearAuthTokens();
          setUser(null);
          return;
        }

        const mapped = mapUserPayload(
          retryPayload.user ? (retryPayload.user as Record<string, unknown>) : retryPayload,
        );
        if (mapped) {
          setUser(mapped);
          return;
        }
      } catch {
        clearAuthTokens();
      }
    }

    setUser(null);
  }, []);

  useEffect(() => {
    let active = true;

    const init = async () => {
      await checkSession();
      if (active) {
        setLoading(false);
      }
    };

    init();

    return () => {
      active = false;
    };
  }, [checkSession]);

  const login = (_token: string, userData: User) => {
    setUser(userData);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout', {}, { skipAuthRedirect: true } as const);
    } catch {
      // Clear local state even if the server session is already gone.
    } finally {
      clearAuthTokens();
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
