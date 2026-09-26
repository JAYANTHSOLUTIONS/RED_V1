import { apiClient } from './client';
import type {
  ConsultantActionItem,
  EvidenceIntelligenceReport,
  PropertyVerificationInput,
  VerificationCase,
  VerificationSummary,
} from './types';

export const verificationApi = {
  run: async (propertyId: string, payload?: PropertyVerificationInput): Promise<VerificationCase> => {
    return apiClient<VerificationCase>(`/properties/${propertyId}/verification`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    });
  },

  getLatestForProperty: async (propertyId: string): Promise<VerificationCase> => {
    return apiClient<VerificationCase>(`/properties/${propertyId}/verification`);
  },

  getSummary: async (propertyId: string): Promise<VerificationSummary> => {
    return apiClient<VerificationSummary>(`/properties/${propertyId}/verification/summary`);
  },

  getEvidence: async (propertyId: string): Promise<EvidenceIntelligenceReport> => {
    return apiClient<EvidenceIntelligenceReport>(`/properties/${propertyId}/verification/evidence`);
  },

  getActions: async (propertyId: string): Promise<ConsultantActionItem[]> => {
    return apiClient<ConsultantActionItem[]>(`/properties/${propertyId}/verification/actions`);
  },

  getById: async (verificationId: string): Promise<VerificationCase> => {
    return apiClient<VerificationCase>(`/verifications/${verificationId}`);
  },
};
