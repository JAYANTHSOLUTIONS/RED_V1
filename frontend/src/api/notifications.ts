import { apiClient } from './client';
import type {
  NotificationItem,
  PaginatedResponse,
  WhatsAppLinkPayload,
  WhatsAppLinkResponse,
} from './types';

export const notificationsApi = {
  list: async (filters: Record<string, unknown> = {}): Promise<PaginatedResponse<NotificationItem>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<NotificationItem>>(`/notifications${qs ? `?${qs}` : ''}`);
  },

  getUnreadCount: async (): Promise<number> => {
    const res = await apiClient<{ unread_count: number }>('/notifications/unread-count');
    return res.unread_count;
  },

  get: async (id: string): Promise<NotificationItem> => {
    return apiClient<NotificationItem>(`/notifications/${id}`);
  },

  markAsRead: async (id: string): Promise<NotificationItem> => {
    return apiClient<NotificationItem>(`/notifications/${id}/read`, {
      method: 'POST',
    });
  },

  markAsUnread: async (id: string): Promise<NotificationItem> => {
    return apiClient<NotificationItem>(`/notifications/${id}/unread`, {
      method: 'POST',
    });
  },

  generateWhatsAppLink: async (payload: WhatsAppLinkPayload): Promise<WhatsAppLinkResponse> => {
    return apiClient<WhatsAppLinkResponse>('/notifications/whatsapp-link', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
