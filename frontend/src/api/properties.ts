import { apiClient, generateIdempotencyKey } from './client';
import type {
  PaginatedResponse,
  Property,
  PropertyCreatePayload,
  PropertyUpdatePayload,
  PropertyFilterParams,
  PropertyImage,
  PropertyImageCreatePayload,
  PropertyImageUpdatePayload,
} from './types';

export const propertiesApi = {
  list: async (filters: PropertyFilterParams = {}): Promise<PaginatedResponse<Property>> => {
    const query = new URLSearchParams();
    Object.entries(filters).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    const qs = query.toString();
    return apiClient<PaginatedResponse<Property>>(`/properties${qs ? `?${qs}` : ''}`);
  },

  get: async (id: string): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}`);
  },

  create: async (payload: PropertyCreatePayload): Promise<Property> => {
    return apiClient<Property>('/properties', {
      method: 'POST',
      idempotencyKey: generateIdempotencyKey(),
      body: JSON.stringify(payload),
    });
  },

  update: async (id: string, payload: PropertyUpdatePayload): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  // Lifecycle Status Mutations
  publish: async (id: string): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}/publish`, {
      method: 'POST',
    });
  },

  pause: async (id: string): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}/pause`, {
      method: 'POST',
    });
  },

  archive: async (id: string): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}/archive`, {
      method: 'POST',
    });
  },

  markSold: async (id: string): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}/mark-sold`, {
      method: 'POST',
    });
  },

  markRented: async (id: string): Promise<Property> => {
    return apiClient<Property>(`/properties/${id}/mark-rented`, {
      method: 'POST',
    });
  },

  // Image Metadata Operations
  listImages: async (propertyId: string): Promise<PropertyImage[]> => {
    return apiClient<PropertyImage[]>(`/properties/${propertyId}/images`);
  },

  uploadImage: async (
    propertyId: string,
    file: File,
    isPrimary: boolean = false,
    displayOrder: number = 0
  ): Promise<PropertyImage> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_primary', String(isPrimary));
    formData.append('display_order', String(displayOrder));

    return apiClient<PropertyImage>(`/properties/${propertyId}/images/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  addImage: async (propertyId: string, payload: PropertyImageCreatePayload): Promise<PropertyImage> => {
    return apiClient<PropertyImage>(`/properties/${propertyId}/images`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateImage: async (
    propertyId: string,
    imageId: string,
    payload: PropertyImageUpdatePayload
  ): Promise<PropertyImage> => {
    return apiClient<PropertyImage>(`/properties/${propertyId}/images/${imageId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteImage: async (propertyId: string, imageId: string): Promise<void> => {
    return apiClient<void>(`/properties/${propertyId}/images/${imageId}`, {
      method: 'DELETE',
    });
  },
};
