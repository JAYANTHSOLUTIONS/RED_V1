import { apiClient } from './client';
import type { TokenResponse, UserResponse } from './types';

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    return apiClient<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    });
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    return apiClient<TokenResponse>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      skipAuth: true,
    });
  },

  logout: async (refreshToken: string): Promise<void> => {
    return apiClient<void>('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  getMe: async (): Promise<UserResponse> => {
    return apiClient<UserResponse>('/auth/me', {
      method: 'GET',
    });
  },
};
