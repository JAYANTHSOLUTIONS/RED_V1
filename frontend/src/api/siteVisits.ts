import { apiClient } from './client';
import type {
  PaginatedResponse,
  SiteVisit,
  SiteVisitCancelPayload,
  SiteVisitCompletePayload,
  SiteVisitConfirmPayload,
  SiteVisitCreatePayload,
  SiteVisitPublicRequestPayload,
  SiteVisitReschedulePayload,
} from './types';

export const siteVisitsApi = {
  list: async (filters: Record<string, unknown> = {}): Promise<PaginatedResponse<SiteVisit>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<SiteVisit>>(`/site-visits${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<SiteVisit> => {
    return apiClient<SiteVisit>(`/site-visits/${id}`);
  },

  create: async (payload: SiteVisitCreatePayload): Promise<SiteVisit> => {
    return apiClient<SiteVisit>('/site-visits', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update: async (id: string, payload: { scheduled_at?: string; notes?: string; feedback?: string }): Promise<SiteVisit> => {
    return apiClient<SiteVisit>(`/site-visits/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  confirm: async (id: string, payload?: SiteVisitConfirmPayload): Promise<SiteVisit> => {
    return apiClient<SiteVisit>(`/site-visits/${id}/confirm`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    });
  },

  complete: async (id: string, payload?: SiteVisitCompletePayload): Promise<SiteVisit> => {
    return apiClient<SiteVisit>(`/site-visits/${id}/complete`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    });
  },

  cancel: async (id: string, payload: SiteVisitCancelPayload): Promise<SiteVisit> => {
    return apiClient<SiteVisit>(`/site-visits/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  reschedule: async (id: string, payload: SiteVisitReschedulePayload): Promise<SiteVisit> => {
    return apiClient<SiteVisit>(`/site-visits/${id}/reschedule`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Public customer submission
  requestPublicVisit: async (payload: SiteVisitPublicRequestPayload): Promise<SiteVisit> => {
    return apiClient<SiteVisit>('/site-visits/request', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuth: true,
    });
  },
};
