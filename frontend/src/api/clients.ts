
import { apiClient } from './client';
import type {
  Client,
  ClientWithLeads,
  ClientCreatePayload,
  ClientUpdatePayload,
  ClientFilterParams,
  PaginatedResponse,
} from './types';

export const clientsApi = {
  list: async (filters: ClientFilterParams = {}): Promise<PaginatedResponse<Client>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<Client>>(`/clients${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<ClientWithLeads> => {
    return apiClient<ClientWithLeads>(`/clients/${id}`);
  },

  create: async (payload: ClientCreatePayload): Promise<Client> => {
    return apiClient<Client>('/clients', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  update: async (id: string, payload: ClientUpdatePayload): Promise<ClientWithLeads> => {
    return apiClient<ClientWithLeads>(`/clients/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  archive: async (id: string): Promise<ClientWithLeads> => {
    return apiClient<ClientWithLeads>(`/clients/${id}/archive`, {
      method: 'POST',
    });
  },
};
