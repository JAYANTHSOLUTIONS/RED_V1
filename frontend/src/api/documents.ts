import { apiClient } from './client';
import type { DocumentFilterParams, DocumentItem, PaginatedResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const documentsApi = {
  list: async (filters: DocumentFilterParams = {}): Promise<PaginatedResponse<DocumentItem>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<DocumentItem>>(`/documents${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<DocumentItem> => {
    return apiClient<DocumentItem>(`/documents/${id}`);
  },

  upload: async (
    file: File,
    documentType: string,
    options: { propertyId?: string; clientId?: string; notes?: string } = {}
  ): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (options.propertyId) formData.append('property_id', options.propertyId);
    if (options.clientId) formData.append('client_id', options.clientId);
    if (options.notes) formData.append('notes', options.notes);

    return apiClient<DocumentItem>('/documents', {
      method: 'POST',
      body: formData,
    });
  },

  getDownloadUrl: (id: string): string => {
    return `${BASE_URL}/documents/${id}/download`;
  },

  download: async (id: string, filename: string): Promise<void> => {
    const token = localStorage.getItem('red_token');
    const headers = new Headers();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const res = await fetch(`${BASE_URL}/documents/${id}/download`, { headers });
    if (!res.ok) throw new Error('Failed to download document');

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },

  review: async (id: string, status: 'PRELIMINARILY_CHECKED' | 'REQUIRES_ATTENTION', notes?: string): Promise<DocumentItem> => {
    return apiClient<DocumentItem>(`/documents/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ status, review_notes: notes }),
    });
  },

  archive: async (id: string): Promise<DocumentItem> => {
    return apiClient<DocumentItem>(`/documents/${id}/archive`, {
      method: 'POST',
    });
  },
};
