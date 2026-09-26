import { apiClient } from './client';
import type {
  FollowUp,
  FollowUpCompletePayload,
  FollowUpCreatePayload,
  FollowUpMissPayload,
  PaginatedResponse,
} from './types';

export const followUpsApi = {
  list: async (filters: Record<string, unknown> = {}): Promise<PaginatedResponse<FollowUp>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<FollowUp>>(`/follow-ups${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<FollowUp> => {
    return apiClient<FollowUp>(`/follow-ups/${id}`);
  },

  create: async (payload: FollowUpCreatePayload): Promise<FollowUp> => {
    return apiClient<FollowUp>('/follow-ups', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update: async (id: string, payload: Partial<FollowUpCreatePayload>): Promise<FollowUp> => {
    return apiClient<FollowUp>(`/follow-ups/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  complete: async (id: string, payload?: FollowUpCompletePayload): Promise<FollowUp> => {
    return apiClient<FollowUp>(`/follow-ups/${id}/complete`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    });
  },

  markMissed: async (id: string, payload?: FollowUpMissPayload): Promise<FollowUp> => {
    return apiClient<FollowUp>(`/follow-ups/${id}/miss`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    });
  },
};
