import { apiClient } from './client';
import type {
  PaginatedResponse,
  PropertyMatchItem,
  PropertyRequirement,
  PropertyRequirementCreatePayload,
  PropertyRequirementUpdatePayload,
} from './types';

export const requirementsApi = {
  list: async (filters: Record<string, unknown> = {}): Promise<PaginatedResponse<PropertyRequirement>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<PropertyRequirement>>(`/property-requirements${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<PropertyRequirement> => {
    return apiClient<PropertyRequirement>(`/property-requirements/${id}`);
  },

  create: async (payload: PropertyRequirementCreatePayload): Promise<PropertyRequirement> => {
    return apiClient<PropertyRequirement>('/property-requirements', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update: async (id: string, payload: PropertyRequirementUpdatePayload): Promise<PropertyRequirement> => {
    return apiClient<PropertyRequirement>(`/property-requirements/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  fulfill: async (id: string): Promise<PropertyRequirement> => {
    return apiClient<PropertyRequirement>(`/property-requirements/${id}/fulfill`, {
      method: 'POST',
    });
  },

  cancel: async (id: string): Promise<PropertyRequirement> => {
    return apiClient<PropertyRequirement>(`/property-requirements/${id}/cancel`, {
      method: 'POST',
    });
  },

  archive: async (id: string): Promise<PropertyRequirement> => {
    return apiClient<PropertyRequirement>(`/property-requirements/${id}/archive`, {
      method: 'POST',
    });
  },

  findMatches: async (
    id: string,
    params: { min_score?: number; limit?: number; offset?: number } = {}
  ): Promise<PaginatedResponse<PropertyMatchItem>> => {
    const query = new URLSearchParams();
    if (params.min_score !== undefined) query.append('min_score', String(params.min_score));
    if (params.limit !== undefined) query.append('limit', String(params.limit));
    if (params.offset !== undefined) query.append('offset', String(params.offset));
    const qs = query.toString();
    return apiClient<PaginatedResponse<PropertyMatchItem>>(`/property-requirements/${id}/matches${qs ? `?${qs}` : ''}`);
  },
};
