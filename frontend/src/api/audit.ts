import { apiClient } from './client';
import type { AuditFilterParams, AuditLog, PaginatedResponse } from './types';

export const auditApi = {
  list: async (filters: AuditFilterParams = {}): Promise<PaginatedResponse<AuditLog>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<AuditLog>>(`/audit-logs${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<AuditLog> => {
    return apiClient<AuditLog>(`/audit-logs/${id}`);
  },
};
