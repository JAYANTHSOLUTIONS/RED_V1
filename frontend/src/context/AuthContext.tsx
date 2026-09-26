import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import type { UserResponse } from '../api/types';

interface AuthContextType {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(() => {
    const cached = localStorage.getItem('red_user');
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('red_token');
    if (!token || token === 'demo-jwt-token') {
      localStorage.removeItem('red_token');
      localStorage.removeItem('red_refresh_token');
      localStorage.removeItem('red_user');
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const me = await authApi.getMe();
      setUser(me);
      localStorage.setItem('red_user', JSON.stringify(me));
    } catch {
      // Token is invalid or expired
      localStorage.removeItem('red_token');
      localStorage.removeItem('red_refresh_token');
      localStorage.removeItem('red_user');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const res = await authApi.login(email, password);
      localStorage.setItem('red_token', res.access_token);
      localStorage.setItem('red_refresh_token', res.refresh_token);
      localStorage.setItem('red_user', JSON.stringify(res.user));
      setUser(res.user);
    } catch (error) {
      localStorage.removeItem('red_token');
      localStorage.removeItem('red_refresh_token');
      localStorage.removeItem('red_user');
      setUser(null);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('red_refresh_token');
    if (refreshToken) {
      try {
        await authApi.logout(refreshToken);
      } catch {
        // Ignore logout errors
      }
    }
    localStorage.removeItem('red_token');
    localStorage.removeItem('red_refresh_token');
    localStorage.removeItem('red_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
