import { apiClient } from './client';

export interface HierarchyItem {
  id: string;
  name: string;
}

export interface SurveySubdivisionItem {
  survey_no: string;
  sub_division_no?: string;
}

export interface TnecScrapeRequest {
  property_id?: string;
  zone_id: string;
  zone_name?: string;
  district_id: string;
  district_name?: string;
  sro_id: string;
  sro_name?: string;
  village_id: string;
  village_name?: string;
  start_date: string; // DD/MM/YYYY
  end_date: string;   // DD/MM/YYYY
  surveys: SurveySubdivisionItem[];
}

export interface TnecJobStatus {
  job_id: string;
  status: 'running' | 'waiting_for_captcha' | 'completed' | 'failed';
  current_step: number;
  message: string;
  captcha_image?: string;
  pdf_filename?: string;
  pdf_url?: string;
  document_id?: string;
  surveys_count: number;
  is_nil_encumbrance?: boolean;
  error?: string;
}

export const tnecApi = {
  getZones: async (): Promise<HierarchyItem[]> => {
    return apiClient<HierarchyItem[]>('/tnec/hierarchy/zones');
  },

  getDistricts: async (zoneId: string): Promise<HierarchyItem[]> => {
    return apiClient<HierarchyItem[]>(`/tnec/hierarchy/districts?zone_id=${encodeURIComponent(zoneId)}`);
  },

  getSros: async (districtId: string, zoneId?: string): Promise<HierarchyItem[]> => {
    const query = zoneId
      ? `district_id=${encodeURIComponent(districtId)}&zone_id=${encodeURIComponent(zoneId)}`
      : `district_id=${encodeURIComponent(districtId)}`;
    return apiClient<HierarchyItem[]>(`/tnec/hierarchy/sros?${query}`);
  },

  getVillages: async (sroId: string): Promise<HierarchyItem[]> => {
    return apiClient<HierarchyItem[]>(`/tnec/hierarchy/villages?sro_id=${encodeURIComponent(sroId)}`);
  },

  matchLocation: async (data: { district: string; taluk?: string; village?: string }): Promise<any> => {
    return apiClient<any>('/tnec/match-location', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  startScrape: async (req: TnecScrapeRequest): Promise<{ job_id: string; status: string; surveys_count: number }> => {
    return apiClient<{ job_id: string; status: string; surveys_count: number }>('/tnec/scrape/start', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  getStatus: async (jobId: string): Promise<TnecJobStatus> => {
    return apiClient<TnecJobStatus>(`/tnec/scrape/status/${encodeURIComponent(jobId)}`);
  },

  submitCaptcha: async (jobId: string, captchaText: string): Promise<{ success: boolean; job_id: string }> => {
    return apiClient<{ success: boolean; job_id: string }>('/tnec/scrape/captcha', {
      method: 'POST',
      body: JSON.stringify({ job_id: jobId, captcha_text: captchaText }),
    });
  },

  getDownloadUrl: (jobId: string): string => {
    return `/api/v1/tnec/download/${encodeURIComponent(jobId)}`;
  },

  downloadPdf: async (jobId: string, filename: string): Promise<void> => {
    const token = localStorage.getItem('red_token');
    const headers = new Headers();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const res = await fetch(`/api/v1/tnec/download/${encodeURIComponent(jobId)}`, { headers });
    if (!res.ok) throw new Error('Failed to download EC PDF');

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
};


