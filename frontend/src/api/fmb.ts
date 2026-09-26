/**
 * FMB Map Generation API client.
 *
 * All CollabLand government API communication happens server-side.
 * These functions call RED_V1 backend endpoints only — never the
 * government service directly from the browser.
 */
import { apiClient } from './client';
import type { DocumentItem } from './types';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FmbGenerateRequest {
  survey_number: string;
  subdivision_number?: string;
}

export interface FmbGenerateResponse {
  pdf_base64: string;
  filename: string;
  file_size: number;
  district: string;
  taluk?: string | null;
  village?: string | null;
  survey_number: string;
  subdivision_number?: string | null;
  gis_code: string;
  scale: number;
  source: string;
}

export interface FmbSaveRequest {
  survey_number: string;
  subdivision_number?: string;
  pdf_base64: string;
  filename: string;
  force_duplicate?: boolean;
}

export interface FmbSaveResponse {
  document_id: string;
  document_type: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  status: string;
  notes?: string | null;
  created_at: string;
  duplicate_existed: boolean;
  source: string;
}

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export const fmbApi = {
  /**
   * Generate an FMB map PDF via the backend → CollabLand service.
   * Returns Base64-encoded PDF for in-browser preview.
   */
  generate: async (
    propertyId: string,
    req: FmbGenerateRequest
  ): Promise<FmbGenerateResponse> => {
    return apiClient<FmbGenerateResponse>(
      `/fmb/properties/${encodeURIComponent(propertyId)}/generate`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    );
  },

  /**
   * Save a previously generated FMB map PDF to the Property Document Vault.
   */
  saveToVault: async (
    propertyId: string,
    req: FmbSaveRequest
  ): Promise<FmbSaveResponse> => {
    return apiClient<FmbSaveResponse>(
      `/fmb/properties/${encodeURIComponent(propertyId)}/save`,
      {
        method: 'POST',
        body: JSON.stringify(req),
      }
    );
  },

  /**
   * Download a generated FMB map as a file — triggers browser download.
   */
  downloadBase64Pdf: (base64: string, filename: string): void => {
    const byteChars = atob(base64);
    const byteArray = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) {
      byteArray[i] = byteChars.charCodeAt(i);
    }
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};
