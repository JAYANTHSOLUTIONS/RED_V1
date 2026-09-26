import { apiClient } from './client';
import type {
  Lead,
  LeadCreatePayload,
  LeadUpdatePayload,
  LeadFilterParams,
  PaginatedResponse,
} from './types';

export const leadsApi = {
  list: async (filters: LeadFilterParams = {}): Promise<PaginatedResponse<Lead>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<Lead>>(`/leads${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}`);
  },

  create: async (payload: LeadCreatePayload): Promise<Lead> => {
    return apiClient<Lead>('/leads', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update: async (id: string, payload: LeadUpdatePayload): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  // Lifecycle Transitions
  contact: async (id: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}/contact`, {
      method: 'POST',
    });
  },

  markInterested: async (id: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}/mark-interested`, {
      method: 'POST',
    });
  },

  scheduleSiteVisitStage: async (id: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}/site-visit-stage`, {
      method: 'POST',
    });
  },

  moveToNegotiation: async (id: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}/negotiation`, {
      method: 'POST',
    });
  },

  convert: async (id: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}/convert`, {
      method: 'POST',
    });
  },

  markLost: async (id: string, lostReason: string): Promise<Lead> => {
    return apiClient<Lead>(`/leads/${id}/lost`, {
      method: 'POST',
      body: JSON.stringify({ lost_reason: lostReason }),
    });
  },
};
