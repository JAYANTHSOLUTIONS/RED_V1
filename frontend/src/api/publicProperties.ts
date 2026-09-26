import { apiClient } from './client';
import type { PaginatedResponse, Property, PropertyFilterParams } from './types';

export const publicPropertiesApi = {
  list: async (filters: PropertyFilterParams = {}): Promise<PaginatedResponse<Property>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<Property>>(`/public/properties${qs ? `?${qs}` : ''}`, {
      skipAuth: true,
    });
  },

  get: async (publicReference: string): Promise<Property> => {
    return apiClient<Property>(`/public/properties/${publicReference}`, {
      skipAuth: true,
    });
  },
};
