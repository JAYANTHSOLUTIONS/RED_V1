import type { DocumentItem } from '../api/types';

export interface VaultSectionDef {
  id: string;
  shortName: string;
  name: string;
  description: string;
  defaultDocType: string;
  allowedTypes: string[];
  color: string;
  borderColor: string;
  bgColor: string;
  badgeBg: string;
}

export const VAULT_SECTIONS: VaultSectionDef[] = [
  {
    id: 'EC',
    shortName: 'EC',
    name: 'Encumbrance Certificate (EC)',
    description: 'Registration department encumbrance record (Form 15/16) tracking transaction history',
    defaultDocType: 'EC',
    allowedTypes: ['EC', 'ENCUMBRANCE_CERTIFICATE'],
    color: 'text-blue-700',
    borderColor: 'border-blue-200',
    bgColor: 'bg-blue-50/50',
    badgeBg: 'bg-blue-100 text-blue-800',
  },
  {
    id: 'Patta',
    shortName: 'Patta',
    name: 'Patta / Chitta / TSLR',
    description: 'Revenue administration record of rights, e-Patta passbook, or Town Survey Land Register',
    defaultDocType: 'PATTA',
    allowedTypes: ['PATTA', 'CHITTA', 'TSLR', 'PATTA_CHITTA'],
    color: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    bgColor: 'bg-emerald-50/50',
    badgeBg: 'bg-emerald-100 text-emerald-800',
  },
  {
    id: 'A-register',
    shortName: 'A-register',
    name: 'A-Register Extract',
    description: 'Permanent village settlement register recording classification, extent, and revenue assessment',
    defaultDocType: 'A_REGISTER',
    allowedTypes: ['A_REGISTER', 'A-REGISTER', 'ADANGAL'],
    color: 'text-purple-700',
    borderColor: 'border-purple-200',
    bgColor: 'bg-purple-50/50',
    badgeBg: 'bg-purple-100 text-purple-800',
  },
  {
    id: 'FMB',
    shortName: 'FMB',
    name: 'Field Measurement Book (FMB)',
    description: 'Revenue survey sketch detailing property boundaries, ladder dimensions, and subdivision lines',
    defaultDocType: 'FMB',
    allowedTypes: ['FMB', 'FIELD_MEASUREMENT_BOOK', 'SURVEY_DOCUMENT'],
    color: 'text-amber-800',
    borderColor: 'border-amber-200',
    bgColor: 'bg-amber-50/50',
    badgeBg: 'bg-amber-100 text-amber-900',
  },
  {
    id: 'Certified Copy',
    shortName: 'Certified Copy',
    name: 'Certified Copy (Title Deed)',
    description: 'SRO issued certified true copy of registered Sale Deed, Parent Document, or Title Chain',
    defaultDocType: 'CERTIFIED_COPY',
    allowedTypes: [
      'CERTIFIED_COPY',
      'SALE_DEED',
      'PARENT_DOCUMENT',
      'LINK_DOCUMENT',
      'SALE_AGREEMENT',
      'AGREEMENT_OF_SALE',
      'GIFT_DEED',
      'SETTLEMENT_DEED',
      'PARTITION_DEED',
      'RELEASE_DEED',
      'POWER_OF_ATTORNEY',
      'MORTGAGE_DEED',
      'LEASE_DEED',
    ],
    color: 'text-indigo-700',
    borderColor: 'border-indigo-200',
    bgColor: 'bg-indigo-50/50',
    badgeBg: 'bg-indigo-100 text-indigo-800',
  },
  {
    id: 'Combined Sketch',
    shortName: 'Combined Sketch',
    name: 'Combined Sketch',
    description: 'Composite town survey, layout plan, or combined revenue subdivision sketch',
    defaultDocType: 'COMBINED_SKETCH',
    allowedTypes: ['COMBINED_SKETCH', 'LAYOUT_APPROVAL', 'SUBDIVISION_DOCUMENT'],
    color: 'text-teal-700',
    borderColor: 'border-teal-200',
    bgColor: 'bg-teal-50/50',
    badgeBg: 'bg-teal-100 text-teal-800',
  },
];

export const OTHER_VAULT_SECTION: VaultSectionDef = {
  id: 'Other',
  shortName: 'Other',
  name: 'Other Approvals & Records',
  description: 'Building permissions, property tax receipts, TNRERA filings, and general legal records',
  defaultDocType: 'OTHER',
  allowedTypes: [],
  color: 'text-gray-700',
  borderColor: 'border-gray-200',
  bgColor: 'bg-gray-50/50',
  badgeBg: 'bg-gray-100 text-gray-800',
};

/**
 * Returns which vault section a given document_type belongs to.
 */
export function getSectionForDocType(docType: string): VaultSectionDef {
  const norm = (docType || '').trim().toUpperCase();
  for (const section of VAULT_SECTIONS) {
    if (section.allowedTypes.some((t) => t.toUpperCase() === norm)) {
      return section;
    }
  }
  return OTHER_VAULT_SECTION;
}

/**
 * Groups an array of documents by the 6 core vault categories plus an optional Other bucket.
 */
export function groupDocumentsByVaultSection(
  documents: DocumentItem[]
): Record<string, DocumentItem[]> {
  const groups: Record<string, DocumentItem[]> = {};

  // Initialize all 6 sections with empty arrays
  for (const section of VAULT_SECTIONS) {
    groups[section.id] = [];
  }
  groups[OTHER_VAULT_SECTION.id] = [];

  for (const doc of documents) {
    const section = getSectionForDocType(doc.document_type);
    groups[section.id].push(doc);
  }

  return groups;
}
