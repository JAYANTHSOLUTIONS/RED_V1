export type PropertyStatus = 'published' | 'paused' | 'archived' | 'sold' | 'rented' | 'pending';
export type PropertyType = 'apartment' | 'villa' | 'plot' | 'commercial' | 'office';
export type VerificationStatus = 'verified' | 'needs_review' | 'pending' | 'unverified';
export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'negotiating' | 'converted' | 'lost';
export type VisitStatus = 'scheduled' | 'confirmed' | 'completed' | 'cancelled' | 'rescheduled';
export type FollowUpStatus = 'pending' | 'completed' | 'missed';
export type DocumentType = 'sale_deed' | 'encumbrance' | 'patta' | 'ec' | 'layout_approval' | 'noc' | 'agreement' | 'other';

export interface Property {
  id: string;
  ref: string;
  title: string;
  location: string;
  area: string;
  city: string;
  type: PropertyType;
  bedrooms?: number;
  bathrooms?: number;
  sqft: number;
  price: number;
  priceDisplay: string;
  status: PropertyStatus;
  verification: VerificationStatus;
  ownerId: string;
  ownerName: string;
  images: string[];
  description: string;
  updatedAt: string;
  createdAt: string;
  facing?: string;
  floor?: number;
  totalFloors?: number;
  amenities?: string[];
  highlighted?: boolean;
  matchScore?: number;
}

export interface Client {
  id: string;
  name: string;
  phone: string;
  email: string;
  type: 'owner' | 'buyer' | 'renter' | 'investor';
  status: 'active' | 'inactive';
  city: string;
  createdAt: string;
  lastActivity: string;
  notes?: string;
  leadsCount: number;
  requirementsCount: number;
}

export interface Lead {
  id: string;
  clientId: string;
  clientName: string;
  clientPhone: string;
  propertyId?: string;
  propertyTitle?: string;
  propertyRef?: string;
  status: LeadStatus;
  source: string;
  budget?: string;
  interest: string;
  notes?: string;
  createdAt: string;
  updatedAt: string;
  nextAction?: string;
  assignedTo: string;
}

export interface Requirement {
  id: string;
  clientId: string;
  clientName: string;
  propertyType: PropertyType;
  locations: string[];
  budgetMin: number;
  budgetMax: number;
  budgetDisplay: string;
  bedroomsMin?: number;
  bedroomsMax?: number;
  sqftMin?: number;
  sqftMax?: number;
  status: 'active' | 'fulfilled' | 'cancelled';
  notes?: string;
  createdAt: string;
  updatedAt: string;
  matchCount: number;
}

export interface SiteVisit {
  id: string;
  clientId: string;
  clientName: string;
  clientPhone: string;
  propertyId: string;
  propertyTitle: string;
  propertyRef: string;
  scheduledAt: string;
  status: VisitStatus;
  notes?: string;
  consultantName: string;
  duration?: number;
  feedback?: string;
  createdAt: string;
}

export interface FollowUp {
  id: string;
  clientId?: string;
  leadId?: string;
  clientName: string;
  type: 'call' | 'whatsapp' | 'email' | 'meeting' | 'site_visit';
  dueDate: string;
  status: FollowUpStatus;
  priority: 'high' | 'medium' | 'low';
  notes: string;
  createdAt: string;
  completedAt?: string;
}

export interface Document {
  id: string;
  name: string;
  type: DocumentType;
  entityType: 'property' | 'client' | 'lead';
  entityId: string;
  entityName: string;
  uploadedAt: string;
  uploadedBy: string;
  size: string;
  status: 'active' | 'archived' | 'under_review';
  mimeType: string;
}

export interface Notification {
  id: string;
  type: 'lead' | 'site_visit' | 'follow_up' | 'document' | 'property' | 'system';
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  entityId?: string;
  entityType?: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  actor: string;
  actorRole: string;
  action: string;
  resource: string;
  resourceId: string;
  result: 'success' | 'failure';
  ip: string;
  details?: string;
}

// ─── PROPERTIES ─────────────────────────────────────────────────────────────

export const properties: Property[] = [
  {
    id: 'prop-001',
    ref: 'RED-P-1001',
    title: '3 BHK Apartment — Ceebros Boulevard',
    location: 'Anna Nagar West',
    area: 'Anna Nagar',
    city: 'Chennai',
    type: 'apartment',
    bedrooms: 3,
    bathrooms: 2,
    sqft: 1480,
    price: 9500000,
    priceDisplay: '₹95 L',
    status: 'published',
    verification: 'verified',
    ownerId: 'cli-001',
    ownerName: 'Rajesh Kumar',
    images: [
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=900&h=600&fit=crop&auto=format',
      'https://images.unsplash.com/photo-1600607687939-ce8a6f349779?w=900&h=600&fit=crop&auto=format',
      'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Well-maintained 3 BHK apartment in a premium residential complex. Located in the heart of Anna Nagar West with excellent connectivity to major business districts. The property features a spacious living area, modular kitchen, and a private balcony overlooking the complex garden.',
    updatedAt: '2025-06-15T10:30:00Z',
    createdAt: '2025-04-10T09:00:00Z',
    facing: 'East',
    floor: 7,
    totalFloors: 14,
    amenities: ['24/7 Security', 'Covered Parking', 'Gymnasium', 'Clubhouse', 'Power Backup', 'Lift'],
    highlighted: true,
  },
  {
    id: 'prop-002',
    ref: 'RED-P-1002',
    title: '4 BHK Independent Villa — ECR Sholinganallur',
    location: 'Sholinganallur',
    area: 'ECR',
    city: 'Chennai',
    type: 'villa',
    bedrooms: 4,
    bathrooms: 4,
    sqft: 3200,
    price: 28000000,
    priceDisplay: '₹2.8 Cr',
    status: 'published',
    verification: 'verified',
    ownerId: 'cli-002',
    ownerName: 'Priya Subramaniam',
    images: [
      'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=900&h=600&fit=crop&auto=format',
      'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Stunning independent villa with private pool on the East Coast Road. Features contemporary architecture with premium finishes throughout. The property includes a landscaped garden, servant quarters, and a large terrace with sea views.',
    updatedAt: '2025-06-12T14:20:00Z',
    createdAt: '2025-03-15T11:00:00Z',
    facing: 'South-East',
    amenities: ['Private Pool', 'Landscaped Garden', 'Covered Parking ×3', 'Servant Quarters', 'Power Backup', 'CCTV'],
    highlighted: true,
  },
  {
    id: 'prop-003',
    ref: 'RED-P-1003',
    title: '2 BHK Apartment — Casagrand Nungambakkam',
    location: 'Nungambakkam',
    area: 'Central Chennai',
    city: 'Chennai',
    type: 'apartment',
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1120,
    price: 6500000,
    priceDisplay: '₹65 L',
    status: 'paused',
    verification: 'needs_review',
    ownerId: 'cli-003',
    ownerName: 'Anand Krishnan',
    images: [
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Compact 2 BHK apartment in prime Nungambakkam location. Ideal for professionals working in the business district. Currently under verification review for minor documentation updates.',
    updatedAt: '2025-06-10T09:45:00Z',
    createdAt: '2025-05-01T08:00:00Z',
    facing: 'North',
    floor: 3,
    totalFloors: 10,
    amenities: ['Security', 'Parking', 'Lift', 'Power Backup'],
  },
  {
    id: 'prop-004',
    ref: 'RED-P-1004',
    title: 'Commercial Space — T. Nagar Business Hub',
    location: 'Pondy Bazaar, T. Nagar',
    area: 'T. Nagar',
    city: 'Chennai',
    type: 'commercial',
    sqft: 4500,
    price: 42000000,
    priceDisplay: '₹4.2 Cr',
    status: 'published',
    verification: 'verified',
    ownerId: 'cli-005',
    ownerName: 'Suresh Rajan',
    images: [
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=900&h=600&fit=crop&auto=format',
      'https://images.unsplash.com/photo-1497366216548-37526070297c?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Premium ground-floor commercial space in the prime T. Nagar business corridor. High footfall area with excellent visibility. Suitable for retail, showroom, or banking operations.',
    updatedAt: '2025-06-08T16:00:00Z',
    createdAt: '2025-02-20T10:30:00Z',
    facing: 'West',
    floor: 0,
    totalFloors: 6,
    amenities: ['Corner Plot', '24/7 Access', 'Dedicated Parking', 'Power Backup', 'Loading Bay'],
  },
  {
    id: 'prop-005',
    ref: 'RED-P-1005',
    title: 'Residential Plot — OMR IT Corridor',
    location: 'Perungudi, OMR',
    area: 'OMR',
    city: 'Chennai',
    type: 'plot',
    sqft: 2400,
    price: 4800000,
    priceDisplay: '₹48 L',
    status: 'pending',
    verification: 'unverified',
    ownerId: 'cli-003',
    ownerName: 'Anand Krishnan',
    images: [
      'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'CMDA-approved residential plot in OMR IT Corridor. Located in a developing residential layout with planned infrastructure. Clear title with no encumbrances as per preliminary review.',
    updatedAt: '2025-06-05T11:20:00Z',
    createdAt: '2025-06-01T09:00:00Z',
    facing: 'North',
    amenities: ['CMDA Approved', 'Corner Plot', 'Road Facing'],
  },
  {
    id: 'prop-006',
    ref: 'RED-P-1006',
    title: '3 BHK Heritage Apartment — Mylapore',
    location: 'R. K. Mutt Road, Mylapore',
    area: 'Mylapore',
    city: 'Chennai',
    type: 'apartment',
    bedrooms: 3,
    bathrooms: 3,
    sqft: 1760,
    price: 11000000,
    priceDisplay: '₹1.1 Cr',
    status: 'published',
    verification: 'verified',
    ownerId: 'cli-008',
    ownerName: 'Kavitha Sundaram',
    images: [
      'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=900&h=600&fit=crop&auto=format',
      'https://images.unsplash.com/photo-1600607687939-ce8a6f349779?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Spacious 3 BHK apartment in the cultural heart of Chennai. This beautifully maintained property offers a unique blend of traditional architecture and modern amenities. Walking distance to Kapaleeshwarar Temple and Marina Beach.',
    updatedAt: '2025-06-14T13:00:00Z',
    createdAt: '2025-04-25T10:00:00Z',
    facing: 'East',
    floor: 4,
    totalFloors: 8,
    amenities: ['Temple View', 'Covered Parking', 'Security', 'Power Backup', 'Lift'],
  },
  {
    id: 'prop-007',
    ref: 'RED-P-1007',
    title: '5 BHK Luxury Villa — Adyar',
    location: 'Gandhi Nagar, Adyar',
    area: 'Adyar',
    city: 'Chennai',
    type: 'villa',
    bedrooms: 5,
    bathrooms: 5,
    sqft: 5500,
    price: 35000000,
    priceDisplay: '₹3.5 Cr',
    status: 'sold',
    verification: 'verified',
    ownerId: 'cli-006',
    ownerName: 'Deepa Venkataraman',
    images: [
      'https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Prestigious independent villa in the prestigious Gandhi Nagar, Adyar. This property was sold in May 2025 and serves as a benchmark comparable for the neighbourhood.',
    updatedAt: '2025-05-20T15:30:00Z',
    createdAt: '2025-01-10T09:00:00Z',
    facing: 'South',
    amenities: ['Private Pool', 'Garden', 'Servant Quarters', 'Multi-car Parking', 'Security Cabin'],
  },
  {
    id: 'prop-008',
    ref: 'RED-P-1008',
    title: 'Office Space — Nungambakkam High Road',
    location: 'Nungambakkam High Road',
    area: 'Nungambakkam',
    city: 'Chennai',
    type: 'office',
    sqft: 2800,
    price: 21000000,
    priceDisplay: '₹2.1 Cr',
    status: 'published',
    verification: 'verified',
    ownerId: 'cli-005',
    ownerName: 'Suresh Rajan',
    images: [
      'https://images.unsplash.com/photo-1497366216548-37526070297c?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Grade A office space on Nungambakkam High Road with excellent corporate address. Recently refurbished with premium finishes. Suitable for corporate headquarters, law firms, or tech companies.',
    updatedAt: '2025-06-13T10:00:00Z',
    createdAt: '2025-03-01T09:00:00Z',
    facing: 'East',
    floor: 5,
    totalFloors: 8,
    amenities: ['Dedicated Parking', '24/7 Access', 'Central AC', 'Conference Room', 'Power Backup', 'Lift'],
  },
  {
    id: 'prop-009',
    ref: 'RED-P-1009',
    title: '2 BHK Apartment — Velachery Main Road',
    location: 'Velachery',
    area: 'South Chennai',
    city: 'Chennai',
    type: 'apartment',
    bedrooms: 2,
    bathrooms: 2,
    sqft: 1050,
    price: 550000,
    priceDisplay: '₹55 L',
    status: 'rented',
    verification: 'verified',
    ownerId: 'cli-001',
    ownerName: 'Rajesh Kumar',
    images: [
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'Well-maintained 2 BHK apartment, currently rented at ₹28,000/month. Excellent rental yield property in a high-demand residential corridor near IT parks.',
    updatedAt: '2025-05-30T12:00:00Z',
    createdAt: '2025-02-15T09:00:00Z',
    facing: 'West',
    floor: 2,
    totalFloors: 6,
    amenities: ['Parking', 'Security', 'Lift'],
  },
  {
    id: 'prop-010',
    ref: 'RED-P-1010',
    title: 'Residential Plot — Tambaram East',
    location: 'Tambaram East',
    area: 'Tambaram',
    city: 'Chennai',
    type: 'plot',
    sqft: 1800,
    price: 3200000,
    priceDisplay: '₹32 L',
    status: 'published',
    verification: 'pending',
    ownerId: 'cli-007',
    ownerName: 'Kartik Natarajan',
    images: [
      'https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=900&h=600&fit=crop&auto=format',
    ],
    description: 'DTCP-approved residential plot in a well-developed layout. All civic amenities available. Clear title with documents under verification.',
    updatedAt: '2025-06-11T09:30:00Z',
    createdAt: '2025-05-20T10:00:00Z',
    facing: 'North-East',
    amenities: ['DTCP Approved', 'Concrete Roads', 'Water Supply', 'Underground Drainage'],
  },
];

// ─── CLIENTS ─────────────────────────────────────────────────────────────────

export const clients: Client[] = [
  { id: 'cli-001', name: 'Rajesh Kumar', phone: '+91 98400 12345', email: 'rajesh.kumar@email.com', type: 'owner', status: 'active', city: 'Chennai', createdAt: '2025-01-10', lastActivity: '2025-06-15', leadsCount: 2, requirementsCount: 0 },
  { id: 'cli-002', name: 'Priya Subramaniam', phone: '+91 94400 23456', email: 'priya.s@email.com', type: 'buyer', status: 'active', city: 'Coimbatore', createdAt: '2025-02-14', lastActivity: '2025-06-14', leadsCount: 1, requirementsCount: 2 },
  { id: 'cli-003', name: 'Anand Krishnan', phone: '+91 99400 34567', email: 'anand.k@email.com', type: 'investor', status: 'active', city: 'Chennai', createdAt: '2025-01-25', lastActivity: '2025-06-12', leadsCount: 3, requirementsCount: 1 },
  { id: 'cli-004', name: 'Meenakshi Iyer', phone: '+91 90000 45678', email: 'meenakshi.i@email.com', type: 'renter', status: 'active', city: 'Madurai', createdAt: '2025-03-08', lastActivity: '2025-06-10', leadsCount: 1, requirementsCount: 1 },
  { id: 'cli-005', name: 'Suresh Rajan', phone: '+91 98890 56789', email: 'suresh.rajan@email.com', type: 'owner', status: 'active', city: 'Chennai', createdAt: '2025-01-05', lastActivity: '2025-06-13', leadsCount: 0, requirementsCount: 0 },
  { id: 'cli-006', name: 'Deepa Venkataraman', phone: '+91 94870 67890', email: 'deepa.v@email.com', type: 'owner', status: 'inactive', city: 'Chennai', createdAt: '2024-11-20', lastActivity: '2025-05-20', leadsCount: 1, requirementsCount: 0 },
  { id: 'cli-007', name: 'Kartik Natarajan', phone: '+91 99000 78901', email: 'kartik.n@email.com', type: 'buyer', status: 'active', city: 'Coimbatore', createdAt: '2025-04-01', lastActivity: '2025-06-11', leadsCount: 2, requirementsCount: 1 },
  { id: 'cli-008', name: 'Kavitha Sundaram', phone: '+91 98450 89012', email: 'kavitha.s@email.com', type: 'owner', status: 'active', city: 'Chennai', createdAt: '2025-03-15', lastActivity: '2025-06-14', leadsCount: 0, requirementsCount: 0 },
];

// ─── LEADS ───────────────────────────────────────────────────────────────────

export const leads: Lead[] = [
  { id: 'lead-001', clientId: 'cli-002', clientName: 'Priya Subramaniam', clientPhone: '+91 94400 23456', propertyId: 'prop-001', propertyTitle: '3 BHK Apartment — Ceebros Boulevard', propertyRef: 'RED-P-1001', status: 'qualified', source: 'Referral', budget: '₹80L – ₹1.1Cr', interest: '3 BHK Apartment in Anna Nagar or Nungambakkam', notes: 'Looking to relocate from Coimbatore. School proximity is important.', createdAt: '2025-06-01', updatedAt: '2025-06-15', nextAction: 'Second site visit scheduled', assignedTo: 'Ravi Chandran' },
  { id: 'lead-002', clientId: 'cli-003', clientName: 'Anand Krishnan', clientPhone: '+91 99400 34567', propertyId: 'prop-004', propertyTitle: 'Commercial Space — T. Nagar Business Hub', propertyRef: 'RED-P-1004', status: 'negotiating', source: 'Direct', budget: '₹3.5Cr – ₹5Cr', interest: 'Commercial space in T. Nagar or Anna Nagar for retail expansion', notes: 'Serious buyer. Has confirmed financing. Negotiating on fixtures included.', createdAt: '2025-05-15', updatedAt: '2025-06-14', nextAction: 'Price negotiation call', assignedTo: 'Ravi Chandran' },
  { id: 'lead-003', clientId: 'cli-007', clientName: 'Kartik Natarajan', clientPhone: '+91 99000 78901', propertyId: 'prop-002', propertyTitle: '4 BHK Villa — ECR Sholinganallur', propertyRef: 'RED-P-1002', status: 'new', source: 'Website', budget: '₹2.5Cr – ₹3.2Cr', interest: 'Independent villa on ECR', notes: 'Initial inquiry via website. Has not visited yet.', createdAt: '2025-06-12', updatedAt: '2025-06-12', nextAction: 'Initial call', assignedTo: 'Meera Nair' },
  { id: 'lead-004', clientId: 'cli-003', clientName: 'Anand Krishnan', clientPhone: '+91 99400 34567', propertyId: 'prop-005', propertyTitle: 'Residential Plot — OMR IT Corridor', propertyRef: 'RED-P-1005', status: 'contacted', source: 'Direct', budget: '₹40L – ₹60L', interest: 'Residential plot in OMR for investment', createdAt: '2025-06-05', updatedAt: '2025-06-10', nextAction: 'Site visit pending', assignedTo: 'Ravi Chandran' },
  { id: 'lead-005', clientId: 'cli-004', clientName: 'Meenakshi Iyer', clientPhone: '+91 90000 45678', status: 'lost', source: 'MagicBricks', budget: '₹20K – ₹28K/month', interest: '2 BHK rental in Velachery or Pallikaranai', notes: 'Found a property through another broker.', createdAt: '2025-05-10', updatedAt: '2025-06-01', assignedTo: 'Meera Nair' },
  { id: 'lead-006', clientId: 'cli-002', clientName: 'Priya Subramaniam', clientPhone: '+91 94400 23456', propertyId: 'prop-006', propertyTitle: '3 BHK Heritage Apartment — Mylapore', propertyRef: 'RED-P-1006', status: 'contacted', source: '99acres', budget: '₹90L – ₹1.3Cr', interest: 'Heritage apartment in old Chennai neighbourhoods', createdAt: '2025-06-08', updatedAt: '2025-06-12', nextAction: 'Share more property details', assignedTo: 'Ravi Chandran' },
];

// ─── REQUIREMENTS ────────────────────────────────────────────────────────────

export const requirements: Requirement[] = [
  { id: 'req-001', clientId: 'cli-002', clientName: 'Priya Subramaniam', propertyType: 'apartment', locations: ['Anna Nagar', 'Nungambakkam', 'Kilpauk'], budgetMin: 8000000, budgetMax: 11000000, budgetDisplay: '₹80L – ₹1.1Cr', bedroomsMin: 3, bedroomsMax: 3, sqftMin: 1400, sqftMax: 1800, status: 'active', notes: 'Near school preferred. Must have covered parking.', createdAt: '2025-06-01', updatedAt: '2025-06-15', matchCount: 3 },
  { id: 'req-002', clientId: 'cli-003', clientName: 'Anand Krishnan', propertyType: 'plot', locations: ['OMR', 'Perungudi', 'Sholinganallur'], budgetMin: 4000000, budgetMax: 6500000, budgetDisplay: '₹40L – ₹65L', sqftMin: 1500, status: 'active', notes: 'Investment purpose. CMDA/DTCP approval required.', createdAt: '2025-06-05', updatedAt: '2025-06-10', matchCount: 2 },
  { id: 'req-003', clientId: 'cli-007', clientName: 'Kartik Natarajan', propertyType: 'villa', locations: ['ECR', 'Adyar', 'Boat Club'], budgetMin: 25000000, budgetMax: 35000000, budgetDisplay: '₹2.5Cr – ₹3.5Cr', bedroomsMin: 4, sqftMin: 3000, status: 'active', notes: 'Must have private garden. Pool preferred.', createdAt: '2025-04-01', updatedAt: '2025-06-11', matchCount: 2 },
  { id: 'req-004', clientId: 'cli-004', clientName: 'Meenakshi Iyer', propertyType: 'apartment', locations: ['Velachery', 'Pallikaranai', 'Medavakkam'], budgetMin: 200000, budgetMax: 330000, budgetDisplay: '₹20K – ₹33K/month', bedroomsMin: 2, bedroomsMax: 2, status: 'fulfilled', createdAt: '2025-05-10', updatedAt: '2025-06-01', matchCount: 0 },
];

// ─── SITE VISITS ─────────────────────────────────────────────────────────────

export const siteVisits: SiteVisit[] = [
  { id: 'sv-001', clientId: 'cli-002', clientName: 'Priya Subramaniam', clientPhone: '+91 94400 23456', propertyId: 'prop-001', propertyTitle: '3 BHK Apartment — Ceebros Boulevard', propertyRef: 'RED-P-1001', scheduledAt: '2025-06-18T11:00:00', status: 'confirmed', consultantName: 'Ravi Chandran', duration: 60, notes: 'Second visit. Client wants to check amenities and building maintenance standards.', createdAt: '2025-06-16' },
  { id: 'sv-002', clientId: 'cli-007', clientName: 'Kartik Natarajan', clientPhone: '+91 99000 78901', propertyId: 'prop-002', propertyTitle: '4 BHK Villa — ECR Sholinganallur', propertyRef: 'RED-P-1002', scheduledAt: '2025-06-19T10:00:00', status: 'scheduled', consultantName: 'Meera Nair', duration: 90, notes: 'First visit. Pick up client from Adyar signal at 9:45 AM.', createdAt: '2025-06-15' },
  { id: 'sv-003', clientId: 'cli-003', clientName: 'Anand Krishnan', clientPhone: '+91 99400 34567', propertyId: 'prop-004', propertyTitle: 'Commercial Space — T. Nagar Business Hub', propertyRef: 'RED-P-1004', scheduledAt: '2025-06-20T14:00:00', status: 'scheduled', consultantName: 'Ravi Chandran', duration: 60, createdAt: '2025-06-15' },
  { id: 'sv-004', clientId: 'cli-002', clientName: 'Priya Subramaniam', clientPhone: '+91 94400 23456', propertyId: 'prop-006', propertyTitle: '3 BHK Heritage Apartment — Mylapore', propertyRef: 'RED-P-1006', scheduledAt: '2025-06-14T11:30:00', status: 'completed', consultantName: 'Ravi Chandran', duration: 75, notes: 'Client liked the location and layout. Concerned about maintenance charges.', feedback: 'Positive. Will discuss with family.', createdAt: '2025-06-12' },
  { id: 'sv-005', clientId: 'cli-004', clientName: 'Meenakshi Iyer', clientPhone: '+91 90000 45678', propertyId: 'prop-009', propertyTitle: '2 BHK Apartment — Velachery Main Road', propertyRef: 'RED-P-1009', scheduledAt: '2025-06-11T16:00:00', status: 'cancelled', consultantName: 'Meera Nair', notes: 'Client cancelled day before due to travel.', createdAt: '2025-06-09' },
  { id: 'sv-006', clientId: 'cli-007', clientName: 'Kartik Natarajan', clientPhone: '+91 99000 78901', propertyId: 'prop-005', propertyTitle: 'Residential Plot — OMR IT Corridor', propertyRef: 'RED-P-1005', scheduledAt: '2025-06-21T09:00:00', status: 'scheduled', consultantName: 'Meera Nair', duration: 45, createdAt: '2025-06-16' },
];

// ─── FOLLOW-UPS ───────────────────────────────────────────────────────────────

export const followUps: FollowUp[] = [
  { id: 'fu-001', clientId: 'cli-002', leadId: 'lead-001', clientName: 'Priya Subramaniam', type: 'call', dueDate: '2025-06-17', status: 'pending', priority: 'high', notes: 'Confirm if second site visit at Ceebros is still on for 18th June.', createdAt: '2025-06-15' },
  { id: 'fu-002', clientId: 'cli-003', leadId: 'lead-002', clientName: 'Anand Krishnan', type: 'meeting', dueDate: '2025-06-18', status: 'pending', priority: 'high', notes: 'Price negotiation meeting for T. Nagar commercial space. Prepare comparables.', createdAt: '2025-06-14' },
  { id: 'fu-003', clientId: 'cli-007', leadId: 'lead-003', clientName: 'Kartik Natarajan', type: 'whatsapp', dueDate: '2025-06-13', status: 'missed', priority: 'medium', notes: 'Share ECR villa brochure and updated price sheet.', createdAt: '2025-06-12' },
  { id: 'fu-004', clientId: 'cli-001', clientName: 'Rajesh Kumar', type: 'call', dueDate: '2025-06-16', status: 'pending', priority: 'medium', notes: 'Discuss listing strategy for Velachery property renewal. Lease expires July.', createdAt: '2025-06-14' },
  { id: 'fu-005', clientId: 'cli-006', clientName: 'Deepa Venkataraman', type: 'email', dueDate: '2025-06-10', status: 'completed', priority: 'low', notes: 'Send post-sale satisfaction survey.', createdAt: '2025-06-09', completedAt: '2025-06-10' },
  { id: 'fu-006', clientId: 'cli-008', clientName: 'Kavitha Sundaram', type: 'call', dueDate: '2025-06-20', status: 'pending', priority: 'medium', notes: 'Check if owner has updated NOC from housing board for Mylapore property.', createdAt: '2025-06-15' },
  { id: 'fu-007', clientId: 'cli-004', leadId: 'lead-005', clientName: 'Meenakshi Iyer', type: 'whatsapp', dueDate: '2025-06-08', status: 'missed', priority: 'low', notes: 'Check if client found a suitable rental. Mark lead accordingly.', createdAt: '2025-06-07' },
  { id: 'fu-008', clientId: 'cli-002', leadId: 'lead-006', clientName: 'Priya Subramaniam', type: 'call', dueDate: '2025-06-22', status: 'pending', priority: 'medium', notes: 'Share heritage apartment brochure. Gauge interest level.', createdAt: '2025-06-16' },
];

// ─── DOCUMENTS ───────────────────────────────────────────────────────────────

export const documents: Document[] = [
  { id: 'doc-001', name: 'Sale Deed — RED-P-1001', type: 'sale_deed', entityType: 'property', entityId: 'prop-001', entityName: 'RED-P-1001 · 3 BHK Anna Nagar', uploadedAt: '2025-04-12', uploadedBy: 'Ravi Chandran', size: '2.4 MB', status: 'active', mimeType: 'application/pdf' },
  { id: 'doc-002', name: 'Encumbrance Certificate — RED-P-1001', type: 'encumbrance', entityType: 'property', entityId: 'prop-001', entityName: 'RED-P-1001 · 3 BHK Anna Nagar', uploadedAt: '2025-04-14', uploadedBy: 'Ravi Chandran', size: '890 KB', status: 'active', mimeType: 'application/pdf' },
  { id: 'doc-003', name: 'Patta — RED-P-1002', type: 'patta', entityType: 'property', entityId: 'prop-002', entityName: 'RED-P-1002 · 4 BHK Villa ECR', uploadedAt: '2025-03-20', uploadedBy: 'Meera Nair', size: '1.1 MB', status: 'active', mimeType: 'application/pdf' },
  { id: 'doc-004', name: 'Layout Approval — RED-P-1005', type: 'layout_approval', entityType: 'property', entityId: 'prop-005', entityName: 'RED-P-1005 · Plot OMR', uploadedAt: '2025-06-02', uploadedBy: 'Ravi Chandran', size: '3.2 MB', status: 'under_review', mimeType: 'application/pdf' },
  { id: 'doc-005', name: 'KYC — Priya Subramaniam', type: 'other', entityType: 'client', entityId: 'cli-002', entityName: 'Priya Subramaniam', uploadedAt: '2025-06-01', uploadedBy: 'Ravi Chandran', size: '512 KB', status: 'active', mimeType: 'application/pdf' },
  { id: 'doc-006', name: 'NOC — Housing Board — RED-P-1006', type: 'noc', entityType: 'property', entityId: 'prop-006', entityName: 'RED-P-1006 · Mylapore', uploadedAt: '2025-04-28', uploadedBy: 'Meera Nair', size: '780 KB', status: 'under_review', mimeType: 'application/pdf' },
];

// ─── NOTIFICATIONS ───────────────────────────────────────────────────────────

export const notifications: Notification[] = [
  { id: 'notif-001', type: 'lead', title: 'New lead received', message: 'Kartik Natarajan submitted an inquiry for 4 BHK Villa ECR via website.', read: false, createdAt: '2025-06-15T14:32:00', entityId: 'lead-003', entityType: 'lead' },
  { id: 'notif-002', type: 'site_visit', title: 'Site visit confirmed', message: 'Priya Subramaniam confirmed site visit for RED-P-1001 on 18 June at 11:00 AM.', read: false, createdAt: '2025-06-15T11:05:00', entityId: 'sv-001', entityType: 'site_visit' },
  { id: 'notif-003', type: 'follow_up', title: 'Follow-up overdue', message: 'Follow-up with Kartik Natarajan (WhatsApp) was due on 13 June and is now overdue.', read: false, createdAt: '2025-06-13T09:00:00', entityId: 'fu-003', entityType: 'follow_up' },
  { id: 'notif-004', type: 'document', title: 'Document under review', message: 'Layout approval for RED-P-1005 has been submitted and is under verification review.', read: true, createdAt: '2025-06-02T16:20:00', entityId: 'doc-004', entityType: 'document' },
  { id: 'notif-005', type: 'property', title: 'Property status updated', message: 'RED-P-1007 (5 BHK Villa Adyar) has been marked as Sold by Ravi Chandran.', read: true, createdAt: '2025-05-20T15:35:00', entityId: 'prop-007', entityType: 'property' },
  { id: 'notif-006', type: 'lead', title: 'Lead status changed', message: 'Lead for Anand Krishnan (T. Nagar Commercial) has moved to Negotiating stage.', read: true, createdAt: '2025-06-14T13:00:00', entityId: 'lead-002', entityType: 'lead' },
  { id: 'notif-007', type: 'site_visit', title: 'Site visit cancelled', message: 'Site visit for Meenakshi Iyer at Velachery was cancelled. Reschedule required.', read: true, createdAt: '2025-06-11T08:30:00', entityId: 'sv-005', entityType: 'site_visit' },
  { id: 'notif-008', type: 'system', title: 'Monthly summary available', message: 'Your June 2025 activity summary is ready. 6 site visits completed, 2 leads converted.', read: true, createdAt: '2025-06-01T08:00:00' },
];

// ─── AUDIT LOGS ───────────────────────────────────────────────────────────────

export const auditLogs: AuditLog[] = [
  { id: 'al-001', timestamp: '2025-06-15T14:32:11Z', actor: 'Meera Nair', actorRole: 'Consultant', action: 'Lead Created', resource: 'Lead', resourceId: 'lead-003', result: 'success', ip: '103.21.x.x', details: 'New lead from Kartik Natarajan via website form' },
  { id: 'al-002', timestamp: '2025-06-15T11:05:45Z', actor: 'Ravi Chandran', actorRole: 'Consultant', action: 'Site Visit Updated', resource: 'SiteVisit', resourceId: 'sv-001', result: 'success', ip: '103.21.x.x', details: 'Status changed from scheduled → confirmed' },
  { id: 'al-003', timestamp: '2025-06-14T16:20:00Z', actor: 'Ravi Chandran', actorRole: 'Consultant', action: 'Lead Status Updated', resource: 'Lead', resourceId: 'lead-002', result: 'success', ip: '103.21.x.x', details: 'Status changed from contacted → negotiating' },
  { id: 'al-004', timestamp: '2025-06-13T10:15:33Z', actor: 'Admin', actorRole: 'Admin', action: 'Property Verified', resource: 'Property', resourceId: 'prop-001', result: 'success', ip: '14.97.x.x', details: 'Verification status set to verified after EC review' },
  { id: 'al-005', timestamp: '2025-06-12T09:44:22Z', actor: 'Meera Nair', actorRole: 'Consultant', action: 'Document Uploaded', resource: 'Document', resourceId: 'doc-004', result: 'success', ip: '103.21.x.x', details: 'Layout approval PDF uploaded for RED-P-1005' },
  { id: 'al-006', timestamp: '2025-06-11T17:05:00Z', actor: 'Ravi Chandran', actorRole: 'Consultant', action: 'Site Visit Cancelled', resource: 'SiteVisit', resourceId: 'sv-005', result: 'success', ip: '103.21.x.x', details: 'Cancelled at client request. Reason: travel' },
  { id: 'al-007', timestamp: '2025-06-10T14:22:18Z', actor: 'Ravi Chandran', actorRole: 'Consultant', action: 'Property Published', resource: 'Property', resourceId: 'prop-006', result: 'success', ip: '103.21.x.x' },
  { id: 'al-008', timestamp: '2025-06-09T11:00:00Z', actor: 'Meera Nair', actorRole: 'Consultant', action: 'Login', resource: 'Session', resourceId: 'sess-009', result: 'success', ip: '49.205.x.x' },
  { id: 'al-009', timestamp: '2025-06-08T08:55:12Z', actor: 'Unknown', actorRole: '—', action: 'Login Attempt Failed', resource: 'Session', resourceId: '—', result: 'failure', ip: '185.xx.x.x', details: 'Invalid credentials for meera.nair@red.co.in' },
  { id: 'al-010', timestamp: '2025-06-07T16:40:00Z', actor: 'Ravi Chandran', actorRole: 'Consultant', action: 'Property Paused', resource: 'Property', resourceId: 'prop-003', result: 'success', ip: '103.21.x.x', details: 'Paused pending documentation update' },
  { id: 'al-011', timestamp: '2025-06-05T13:30:00Z', actor: 'Admin', actorRole: 'Admin', action: 'Client Created', resource: 'Client', resourceId: 'cli-007', result: 'success', ip: '14.97.x.x' },
  { id: 'al-012', timestamp: '2025-05-20T15:35:00Z', actor: 'Ravi Chandran', actorRole: 'Consultant', action: 'Property Sold', resource: 'Property', resourceId: 'prop-007', result: 'success', ip: '103.21.x.x', details: 'Status changed to sold. Buyer: Deepa Venkataraman (internal)' },
];

// ─── HELPERS ─────────────────────────────────────────────────────────────────

export function formatPrice(n: number): string {
  if (n >= 10000000) return `₹${(n / 10000000).toFixed(1).replace(/\.0$/, '')} Cr`;
  if (n >= 100000) return `₹${(n / 100000).toFixed(0)} L`;
  return `₹${n.toLocaleString('en-IN')}`;
}

export function formatDate(s: string): string {
  return new Date(s).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function timeAgo(s: string): string {
  const diff = Date.now() - new Date(s).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d ago`;
  return formatDate(s);
}
