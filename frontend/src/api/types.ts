
// RED_V1 Phase 18 Frozen API Types & Domain Contracts

export interface SuccessEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
}

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface ErrorEnvelope {
  success: boolean;
  error: ErrorDetail;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

// ---------------------------------------------------------------------------
// Properties
// ---------------------------------------------------------------------------

export interface PropertyImage {
  id: string;
  property_id?: string;
  storage_key: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  display_order: number;
  is_primary: boolean;
  checksum?: string | null;
  is_archived?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface PropertyImageCreatePayload {
  storage_key: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  display_order?: number;
  is_primary?: boolean;
}

export interface PropertyImageUpdatePayload {
  display_order?: number;
  is_primary?: boolean;
}

export interface Property {
  id: string;
  public_reference: string;
  title: string;
  description?: string | null;
  property_type: string; // Apartment, Villa, Plot, Commercial, Agricultural
  transaction_type: 'SALE' | 'RENT' | 'LEASE';
  price: number;
  price_negotiable: boolean;
  status: 'DRAFT' | 'PUBLISHED' | 'PAUSED' | 'ARCHIVED' | 'SOLD' | 'RENTED';

  // Dimensions & Specs
  built_up_area?: number | null;
  plot_area?: number | null;
  area_unit: string;
  bedrooms?: number | null;
  bathrooms?: number | null;
  floor?: number | null;
  total_floors?: number | null;
  facing?: string | null;
  furnishing_state?: string | null;
  parking_spaces?: number | null;
  property_age?: number | null;

  // Location
  district: string;
  city: string;
  taluk?: string | null;
  locality: string;
  pincode: string;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  google_maps_url?: string | null;

  // Private / Owner
  owner_name?: string | null;
  owner_phone?: string | null;
  owner_email?: string | null;
  inventory_source?: string | null;
  advertisement_authorized: boolean;
  internal_notes?: string | null;

  images: PropertyImage[];
  created_at: string;
  updated_at: string;
}

export interface PropertyCreatePayload {
  title: string;
  description?: string;
  property_type: string;
  transaction_type: 'SALE' | 'RENT' | 'LEASE';
  price: number;
  price_negotiable?: boolean;
  built_up_area?: number;
  plot_area?: number;
  area_unit?: string;
  bedrooms?: number;
  bathrooms?: number;
  floor?: number;
  total_floors?: number;
  facing?: string;
  furnishing_state?: string;
  parking_spaces?: number;
  property_age?: number;
  district: string;
  city: string;
  taluk?: string;
  locality: string;
  pincode: string;
  address?: string;
  latitude?: number;
  longitude?: number;
  google_maps_url?: string;
  owner_name?: string;
  owner_phone?: string;
  owner_email?: string;
  inventory_source?: string;
  advertisement_authorized?: boolean;
  internal_notes?: string;
}

export type PropertyUpdatePayload = Partial<PropertyCreatePayload>;

export interface PropertyFilterParams {
  status?: string;
  property_type?: string;
  transaction_type?: string;
  district?: string;
  city?: string;
  min_price?: number;
  max_price?: number;
  bedrooms?: number;
  search?: string;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// ---------------------------------------------------------------------------
// Clients
// ---------------------------------------------------------------------------

export interface Client {
  id: string;
  full_name: string;
  phone: string;
  email?: string | null;
  preferred_contact_method: 'CALL' | 'WHATSAPP' | 'EMAIL' | 'SMS';
  postal_address?: string | null;
  classification: 'BUYER' | 'SELLER' | 'TENANT' | 'LANDLORD' | 'INVESTOR';
  source?: string | null;
  status: string;
  notes?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClientWithLeads extends Client {
  leads: Lead[];
}

export interface ClientCreatePayload {
  full_name: string;
  phone: string;
  email?: string;
  preferred_contact_method?: 'CALL' | 'WHATSAPP' | 'EMAIL' | 'SMS';
  postal_address?: string;
  classification?: 'BUYER' | 'SELLER' | 'TENANT' | 'LANDLORD' | 'INVESTOR';
  source?: string;
  notes?: string;
}

export type ClientUpdatePayload = Partial<ClientCreatePayload> & { status?: string };

export interface ClientFilterParams {
  classification?: string;
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Leads
// ---------------------------------------------------------------------------

export interface Lead {
  id: string;
  client_id: string;
  property_id?: string | null;
  requirement_id?: string | null;
  source: string;
  status: 'NEW' | 'CONTACTED' | 'INTERESTED' | 'SITE_VISIT' | 'NEGOTIATION' | 'CONVERTED' | 'LOST';
  lost_reason?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  client?: {
    id: string;
    full_name: string;
    phone: string;
    email?: string | null;
    classification: string;
    status: string;
  } | null;
  property?: {
    id: string;
    public_reference: string;
    title: string;
    property_type: string;
    transaction_type: string;
    price: number;
    city: string;
    locality: string;
    status: string;
  } | null;
}

export interface LeadCreatePayload {
  client_id: string;
  property_id?: string;
  requirement_id?: string;
  source: string;
  notes?: string;
}

export interface LeadUpdatePayload {
  property_id?: string;
  requirement_id?: string;
  source?: string;
  notes?: string;
}

export interface LeadFilterParams {
  status?: string;
  client_id?: string;
  property_id?: string;
  source?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Requirements & Matching
// ---------------------------------------------------------------------------

export interface PropertyRequirement {
  id: string;
  client_id: string;
  transaction_type: 'BUY' | 'SALE' | 'RENT' | 'LEASE';
  property_types?: string | null;
  target_locations?: string | null;
  min_budget?: number | null;
  max_budget?: number | null;
  min_area?: number | null;
  max_area?: number | null;
  area_unit: string;
  bedrooms?: number | null;
  bathrooms?: number | null;
  facing?: string | null;
  furnishing_state?: string | null;
  status: 'ACTIVE' | 'FULFILLED' | 'CANCELLED' | 'ARCHIVED';
  notes?: string | null;
  created_at: string;
  updated_at: string;
  client?: {
    id: string;
    full_name: string;
    phone: string;
    email?: string | null;
  } | null;
}

export interface PropertyRequirementCreatePayload {
  client_id: string;
  transaction_type: 'BUY' | 'SALE' | 'RENT' | 'LEASE';
  property_types?: string;
  target_locations?: string;
  min_budget?: number;
  max_budget?: number;
  min_area?: number;
  max_area?: number;
  area_unit?: string;
  bedrooms?: number;
  bathrooms?: number;
  facing?: string;
  furnishing_state?: string;
  notes?: string;
}

export type PropertyRequirementUpdatePayload = Partial<Omit<PropertyRequirementCreatePayload, 'client_id'>>;

export interface PropertyMatchItem {
  property: {
    id: string;
    public_reference: string;
    title: string;
    property_type: string;
    transaction_type: string;
    price: number;
    price_negotiable: boolean;
    built_up_area?: number | null;
    plot_area?: number | null;
    area_unit: string;
    bedrooms?: number | null;
    bathrooms?: number | null;
    facing?: string | null;
    furnishing_state?: string | null;
    parking_spaces?: number | null;
    district: string;
    city: string;
    locality: string;
    status: string;
  };
  match_grade: 'EXACT_MATCH' | 'PARTIAL_MATCH';
  score: number;
  matched_criteria: string[];
  unmatched_criteria: string[];
}

// ---------------------------------------------------------------------------
// Site Visits
// ---------------------------------------------------------------------------

export interface SiteVisit {
  id: string;
  client_id: string;
  property_id: string;
  lead_id?: string | null;
  scheduled_at: string;
  status: 'REQUESTED' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED' | 'RESCHEDULED';
  notes?: string | null;
  cancellation_reason?: string | null;
  rescheduled_from_id?: string | null;
  feedback?: string | null;
  created_at: string;
  updated_at: string;
  client?: {
    id: string;
    full_name: string;
    phone: string;
    classification?: string | null;
  } | null;
  property?: {
    id: string;
    title: string;
    public_reference: string;
    property_type: string;
    city: string;
    locality?: string | null;
    district?: string | null;
  } | null;
  disclaimer?: string;
}

export interface SiteVisitCreatePayload {
  client_id: string;
  property_id: string;
  lead_id?: string;
  scheduled_at: string;
  status?: 'REQUESTED' | 'CONFIRMED';
  notes?: string;
}

export interface SiteVisitConfirmPayload {
  scheduled_at?: string;
  notes?: string;
}

export interface SiteVisitCompletePayload {
  feedback?: string;
  notes?: string;
}

export interface SiteVisitCancelPayload {
  cancellation_reason: string;
  notes?: string;
}

export interface SiteVisitReschedulePayload {
  new_scheduled_at: string;
  reason?: string;
  notes?: string;
}

export interface SiteVisitPublicRequestPayload {
  client_id: string;
  property_id: string;
  lead_id?: string;
  scheduled_at: string;
  notes?: string;
}

// ---------------------------------------------------------------------------
// Follow-ups
// ---------------------------------------------------------------------------

export interface FollowUp {
  id: string;
  client_id?: string | null;
  lead_id?: string | null;
  property_id?: string | null;
  scheduled_at: string;
  action_type: 'CALL' | 'SEND_DOCS' | 'ARRANGE_VISIT' | 'OWNER_FOLLOW_UP' | 'MISSING_PAPERWORK';
  status: 'SCHEDULED' | 'COMPLETED' | 'MISSED';
  notes?: string | null;
  completion_notes?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  client?: {
    id: string;
    full_name: string;
    phone: string;
    classification?: string | null;
  } | null;
  lead?: {
    id: string;
    status: string;
    source?: string | null;
  } | null;
  property?: {
    id: string;
    title: string;
    public_reference: string;
    property_type: string;
    city: string;
  } | null;
  disclaimer?: string;
}

export interface FollowUpCreatePayload {
  client_id?: string;
  lead_id?: string;
  property_id?: string;
  action_type: 'CALL' | 'SEND_DOCS' | 'ARRANGE_VISIT' | 'OWNER_FOLLOW_UP' | 'MISSING_PAPERWORK';
  scheduled_at: string;
  notes?: string;
}

export interface FollowUpCompletePayload {
  completion_notes?: string;
}

export interface FollowUpMissPayload {
  notes?: string;
}

// ---------------------------------------------------------------------------
// Preliminary Property Verification (Tamil Nadu Intelligence)
// ---------------------------------------------------------------------------

export interface CheckResult {
  checklist_code: string;
  item_name: string;
  category: string;
  status: 'PASS' | 'REVIEW' | 'FAIL' | 'NOT_APPLICABLE' | 'INFO';
  is_present: boolean;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'INFO';
  notes?: string | null;
  evidence: Array<{
    document_id?: string | null;
    document_type: string;
    original_filename?: string | null;
  }>;
}

export interface CheckExplanation {
  checklist_code: string;
  result: string;
  explanation: string;
  risk: string;
  recommended_action: string;
}

export interface ConsultantActionItem {
  action_type: string;
  priority: string;
  target_document_type?: string | null;
  description: string;
}

export interface VerificationSummary {
  property_id: string;
  overall_risk: string;
  documentary_completeness_score: number;
  critical_issue_count: number;
  high_risk_issue_count: number;
  medium_risk_issue_count: number;
  low_risk_issue_count: number;
  missing_document_count: number;
  review_required_count: number;
  disclaimer: string;
}

export interface EvidenceIntelligenceReport {
  property_id: string;
  evidence_completeness: number;
  evidence_quality: string;
  evidence_conflict_count: number;
  missing_critical_evidence: string[];
  unresolved_review_items: string[];
  chronology_integrity: string;
  identity_consistency: string;
  evidence_items: Array<{
    evidence_type: string;
    status: string;
    source_document_id?: string | null;
    confidence: string;
    notes?: string | null;
  }>;
  disclaimer: string;
}

export interface VerificationCase {
  id: string;
  property_id: string;
  status: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'INFO';
  completeness_score: number;
  completeness_notes: string;
  planning_authority_type: string;
  rera_applicability: string;
  rera_applicability_reason?: string | null;
  risk_flags: string[];
  missing_information: string[];
  checks: CheckResult[];
  explanations: CheckExplanation[];
  actions: ConsultantActionItem[];
  evidence_report?: EvidenceIntelligenceReport | null;
  summary?: VerificationSummary | null;
  consultant_observations?: string | null;
  disclaimer: string;
  disclaimer_acknowledged: boolean;
  engine_version: string;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyVerificationInput {
  survey_number?: string;
  subdivision_number?: string;
  patta_number?: string;
  plot_number?: string;
  door_number?: string;
  flat_number?: string;
  block?: string;
  taluk?: string;
  village?: string;
  district?: string;
  sro_name?: string;
  ec_start_date?: string;
  ec_end_date?: string;
  ec_has_encumbrance_entries?: boolean;
  ec_notes?: string;
  planning_authority?: string;
  planning_approval_number?: string;
  layout_approval_number?: string;
  rera_registration_number?: string;
  rera_project_name?: string;
  rera_promoter_name?: string;
  is_new_project_or_promoter_sale?: boolean;
  parent_document_date?: string;
  current_deed_date?: string;
  property_tax_assessment_number?: string;
  property_tax_paid_period?: string;
  consultant_notes?: string;
  disclaimer_acknowledged?: boolean;
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------

export interface DocumentItem {
  id: string;
  property_id?: string | null;
  client_id?: string | null;
  document_type: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  checksum: string;
  status: 'UPLOADED' | 'UNDER_REVIEW' | 'PRELIMINARILY_CHECKED' | 'REQUIRES_ATTENTION' | 'ARCHIVED';
  notes?: string | null;
  is_archived: boolean;
  uploaded_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentFilterParams {
  property_id?: string;
  client_id?: string;
  document_type?: string;
  status?: string;
  is_archived?: boolean;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface NotificationItem {
  id: string;
  user_id?: string | null;
  title: string;
  message: string;
  channel: string;
  notification_type: string;
  entity_type?: string | null;
  entity_id?: string | null;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export interface WhatsAppLinkPayload {
  phone: string;
  message: string;
}

export interface WhatsAppLinkResponse {
  phone: string;
  message: string;
  whatsapp_url: string;
}

// ---------------------------------------------------------------------------
// Audit Logs
// ---------------------------------------------------------------------------

export interface AuditLog {
  id: string;
  user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  old_values?: Record<string, unknown> | null;
  new_values?: Record<string, unknown> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  correlation_id?: string | null;
  created_at: string;
}

export interface AuditFilterParams {
  action?: string;
  entity_type?: string;
  entity_id?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}
