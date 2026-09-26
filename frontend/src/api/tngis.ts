import { apiClient } from './client';

export interface TngisLookupRequest {
  district: string;
  taluk: string;
  village: string;
  survey_number: string;
  subdivision?: string;
  area_type?: string;
  live_scrape?: boolean;
}

export interface TngisOwnerRecord {
  index: number;
  owner: string;
  relative?: string | null;
  relation?: string | null;
}

export interface TngisLandDetails {
  land_type?: string | null;
  land_type_eng?: string | null;
  land_type_tamil?: string | null;
  govt_pri_code?: string | null;
  soil_class?: string | null;
  soil_type_pri?: string | null;
  soil_type_sec?: string | null;
  extent_hectares?: string | null;
  extent_ares?: string | null;
  total_tax?: string | null;
  patta_number?: string | null;
  poramboke?: string | null;
  assessed?: string | null;
  cultivable?: string | null;
  raw_fields?: Record<string, string>;
}

export interface TngisVertex {
  vertex_number: number;
  latitude: number;
  longitude: number;
}

export interface TngisCoordinates {
  latitude: number;
  longitude: number;
  google_maps_url: string;
  vertices: TngisVertex[];
}

export interface TngisGuidelineValue {
  land_type?: string | null;
  metric_rate?: string | null;
  guideline_amount?: string | null;
}

export interface TngisDocumentStatus {
  patta_available: boolean;
  patta_rendered_pdf?: string | null;
  fmb_available: boolean;
  fmb_rendered_pdf?: string | null;
  fmb_screenshot?: string | null;
  ec_available: boolean;
  ec_rendered_pdf?: string | null;
}

export interface TngisLookupResponse {
  search: Record<string, string>;
  owners: TngisOwnerRecord[];
  land_details: TngisLandDetails;
  guideline_value: TngisGuidelineValue;
  coordinates?: TngisCoordinates | null;
  document_status: TngisDocumentStatus;
  raw_sections: Record<string, string>;
  is_cached_sample: boolean;
  message: string;
}

export interface TngisSaveRequest {
  property_id?: string | null;
  create_new_property?: boolean;
  district: string;
  taluk: string;
  village: string;
  survey_number: string;
  subdivision?: string | null;
  patta_number?: string | null;
  land_type?: string | null;
  land_type_detail?: string | null;
  extent_hectares?: string | null;
  extent_ares?: string | null;
  total_tax?: string | null;
  guideline_rate?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  google_maps_url?: string | null;
  owners: TngisOwnerRecord[];
  vertices?: TngisVertex[];
  consultant_notes?: string | null;
}

export interface TngisSaveResponse {
  saved: boolean;
  property_id?: string;
  public_reference?: string;
  action?: 'CREATED' | 'UPDATED';
  message: string;
}

export interface TngisScrapeStartRequest {
  district: string;
  taluk: string;
  village: string;
  survey_number: string;
  subdivision?: string;
  area_type?: string;
  headless?: boolean;
}

export interface TngisScrapeStatusResponse {
  session_id: string;
  status: 'starting' | 'logging_in' | 'navigating' | 'waiting_for_pin' | 'extracting' | 'completed' | 'error';
  message: string;
  timestamp?: number;
  extra?: Record<string, unknown>;
  map_image?: string | null;
  data?: TngisLookupResponse | null;
}

export const tngisApi = {
  lookup: async (data: TngisLookupRequest): Promise<TngisLookupResponse> => {
    return apiClient<TngisLookupResponse>('/tngis/lookup', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  startScrape: async (data: TngisScrapeStartRequest): Promise<TngisScrapeStatusResponse> => {
    return apiClient<TngisScrapeStatusResponse>('/tngis/scrape/start', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getScrapeStatus: async (sessionId: string): Promise<TngisScrapeStatusResponse> => {
    return apiClient<TngisScrapeStatusResponse>(`/tngis/scrape/status/${sessionId}`);
  },

  continueScrape: async (sessionId: string, xRatio = 0.5, yRatio = 0.5): Promise<{ session_id: string; resumed: boolean }> => {
    return apiClient<{ session_id: string; resumed: boolean }>(`/tngis/scrape/continue/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ x_ratio: xRatio, y_ratio: yRatio }),
    });
  },

  getSample: async (): Promise<TngisLookupResponse> => {
    return apiClient<TngisLookupResponse>('/tngis/sample');
  },

  save: async (data: TngisSaveRequest): Promise<TngisSaveResponse> => {
    return apiClient<TngisSaveResponse>('/tngis/save', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
