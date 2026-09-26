import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import {
  ChevronLeft,
  Edit,
  MapPin,
  Building,
  ShieldCheck,
  Upload,
  Trash2,
  Star,
  FileText,
  Calendar,
  AlertTriangle,
  Play,
  Pause,
  Archive,
  Download,
  CheckCircle2,
  Clock,
  Search,
} from 'lucide-react';
import { TngisSearchModal } from '../components/tngis/TngisSearchModal';
import { TngisPropertyTab } from '../components/tngis/TngisPropertyTab';
import {
  propertiesApi,
  verificationApi,
  documentsApi,
  siteVisitsApi,
} from '../api';
import type {
  Property,
  PropertyUpdatePayload,
  PropertyImageCreatePayload,
  VerificationCase,
  EvidenceIntelligenceReport,
  ConsultantActionItem,
  DocumentItem,
  SiteVisit,
} from '../api/types';
import { TnLocationSelector } from '../components/common/TnLocationSelector';
import { getTnDistricts, getTnTaluks, getTnVillages } from '../utils/tnLocations';
import {
  VAULT_SECTIONS,
  OTHER_VAULT_SECTION,
  groupDocumentsByVaultSection,
  VaultSectionDef,
} from '../utils/vaultSections';
import { TnecModal } from '../components/tnec/TnecModal';
import { FmbGeneratorPanel } from '../components/fmb/FmbGeneratorPanel';

export default function PropertyDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [property, setProperty] = useState<Property | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'tngis' | 'images' | 'verification' | 'documents' | 'visits'>('overview');

  // Verification state
  const [verification, setVerification] = useState<VerificationCase | null>(null);
  const [evidenceReport, setEvidenceReport] = useState<EvidenceIntelligenceReport | null>(null);
  const [actions, setActions] = useState<ConsultantActionItem[]>([]);
  const [verifLoading, setVerifLoading] = useState(false);

  // Documents state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [selectedVaultSection, setSelectedVaultSection] = useState<string>('all');

  // Visits state
  const [visits, setVisits] = useState<SiteVisit[]>([]);
  const [visitsLoading, setVisitsLoading] = useState(false);

  // Action / Mutation modals
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isAddImageModalOpen, setIsAddImageModalOpen] = useState(false);
  const [isUploadDocModalOpen, setIsUploadDocModalOpen] = useState(false);
  const [isBookVisitModalOpen, setIsBookVisitModalOpen] = useState(false);
  const [isTnecModalOpen, setIsTnecModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Form states
  const [editForm, setEditForm] = useState<PropertyUpdatePayload>({});
  const [imageUploadMode, setImageUploadMode] = useState<'file' | 'url'>('file');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageIsPrimary, setImageIsPrimary] = useState(false);
  const [newImage, setNewImage] = useState<PropertyImageCreatePayload>({
    storage_key: '',
    original_filename: '',
    mime_type: 'image/jpeg',
    file_size: 1024 * 500,
    is_primary: false,
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('SALE_DEED');
  const [docNotes, setDocNotes] = useState('');

  const [visitClientId, setVisitClientId] = useState('');
  const [visitDate, setVisitDate] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
  const [visitNotes, setVisitNotes] = useState('');

  // Verification custom input form
  const [verifDistrict, setVerifDistrict] = useState('Chennai');
  const [verifTaluk, setVerifTaluk] = useState('');
  const [verifVillage, setVerifVillage] = useState('');
  const [surveyNum, setSurveyNum] = useState('');
  const [subdivNum, setSubdivNum] = useState('');
  const [pattaNum, setPattaNum] = useState('');
  const [planningAuth, setPlanningAuth] = useState('CMDA');
  const [planningNum, setPlanningNum] = useState('');
  const [isTngisModalOpen, setIsTngisModalOpen] = useState(false);

  const verifTaluks = useMemo(() => getTnTaluks(verifDistrict), [verifDistrict]);
  const verifVillages = useMemo(
    () => getTnVillages(verifDistrict, verifTaluk),
    [verifDistrict, verifTaluk]
  );

  // Helper to extract Survey Number, Subdivision, and Patta Number from property details
  const extractRevenueIdentifiers = (prop: Property) => {
    const parts = [
      prop.internal_notes || '',
      prop.title || '',
      prop.address || '',
      prop.description || '',
    ];
    const text = parts.join('\n');

    let survey_no = '';
    let subdivision_no = '';
    let patta_no = '';

    // 1. Structured labels e.g. "Survey No: 370 | Subdivision: 4" or "Patta No: 582"
    const synoMatch = text.match(/(?:Survey\s*(?:No\.?|Number)?|Sy\.?\s*No\.?|S\.?F\.?\s*No\.?)\s*[:=]\s*([A-Za-z0-9]+)/i);
    const subdivMatch = text.match(/(?:Subdivision|Sub[\s_-]*div(?:ision)?(?:\s*No\.?)?)\s*[:=]\s*([A-Za-z0-9]+)/i);
    const pattaMatch = text.match(/Patta\s*(?:No\.?|Number)?\s*[:=]\s*([A-Za-z0-9]+)/i);

    if (synoMatch && synoMatch[1]) {
      survey_no = synoMatch[1].trim();
    }
    if (subdivMatch && subdivMatch[1]) {
      const val = subdivMatch[1].trim();
      if (val !== '-' && val.toLowerCase() !== 'null' && val.toLowerCase() !== 'none') {
        subdivision_no = val;
      }
    }
    if (pattaMatch && pattaMatch[1]) {
      patta_no = pattaMatch[1].trim();
    }

    // 2. Slash format: e.g. "Survey 217/1B2", "370/4", "217/6"
    if (!survey_no || !subdivision_no) {
      const slashMatch = text.match(/(?:Survey\s*(?:No\.?)?|Sy\.?\s*No\.?|S\.?F\.?\s*No\.?|S\.?No\.?|\b)\s*([0-9]{1,4})\s*[\/\\-]\s*([0-9A-Za-z]{1,8})\b/i);
      if (slashMatch) {
        if (!survey_no) survey_no = slashMatch[1];
        if (!subdivision_no) subdivision_no = slashMatch[2];
      }
    }

    // 3. Standalone survey number: e.g. "Survey 370"
    if (!survey_no) {
      const standMatch = text.match(/(?:Survey\s*(?:No\.?)?|Sy\.?\s*No\.?|S\.?F\.?\s*No\.?|S\.?No\.?)\s*[:.\s-]*([0-9]{1,4})\b/i);
      if (standMatch) {
        survey_no = standMatch[1];
      }
    }

    return { survey_no, subdivision_no, patta_no };
  };

  const loadProperty = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const prop = await propertiesApi.get(id);
      setProperty(prop);
      setVerifDistrict(prop.district || 'Chennai');
      setVerifTaluk(prop.taluk || '');
      setVerifVillage(prop.locality || '');

      // Automatically extract Revenue & Survey identifiers from property record
      const rev = extractRevenueIdentifiers(prop);
      if (rev.survey_no) setSurveyNum(rev.survey_no);
      if (rev.subdivision_no) setSubdivNum(rev.subdivision_no);
      if (rev.patta_no) setPattaNum(rev.patta_no);
      setEditForm({
        title: prop.title,
        description: prop.description || '',
        price: prop.price,
        bedrooms: prop.bedrooms || undefined,
        bathrooms: prop.bathrooms || undefined,
        built_up_area: prop.built_up_area || undefined,
        plot_area: prop.plot_area || undefined,
        locality: prop.locality,
        taluk: prop.taluk || '',
        district: prop.district,
        city: prop.city,
        pincode: prop.pincode,
        address: prop.address || '',
        google_maps_url: prop.google_maps_url || '',
        owner_name: prop.owner_name || '',
        owner_phone: prop.owner_phone || '',
        internal_notes: prop.internal_notes || '',
      });
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  const loadVerificationData = useCallback(async () => {
    if (!id) return;
    setVerifLoading(true);
    try {
      const [verifRes, evRes, actRes] = await Promise.allSettled([
        verificationApi.getLatestForProperty(id),
        verificationApi.getEvidence(id),
        verificationApi.getActions(id),
      ]);
      if (verifRes.status === 'fulfilled') setVerification(verifRes.value);
      if (evRes.status === 'fulfilled') setEvidenceReport(evRes.value);
      if (actRes.status === 'fulfilled') setActions(actRes.value);
    } catch {
      // Handle
    } finally {
      setVerifLoading(false);
    }
  }, [id]);

  const loadDocuments = useCallback(async () => {
    if (!id) return;
    setDocsLoading(true);
    try {
      const res = await documentsApi.list({ property_id: id });
      setDocuments(res.items);
    } catch {
      // Handle
    } finally {
      setDocsLoading(false);
    }
  }, [id]);

  const loadVisits = useCallback(async () => {
    if (!id) return;
    setVisitsLoading(true);
    try {
      const res = await siteVisitsApi.list({ property_id: id });
      setVisits(res.items);
    } catch {
      // Handle
    } finally {
      setVisitsLoading(false);
    }
  }, [id]);

  const groupedDocs = useMemo(
    () => groupDocumentsByVaultSection(documents),
    [documents]
  );

  const openUploadForSection = (defaultType?: string) => {
    if (defaultType) {
      setDocType(defaultType);
    }
    setIsUploadDocModalOpen(true);
  };

  useEffect(() => {
    loadProperty();
  }, [loadProperty]);

  useEffect(() => {
    if (activeTab === 'verification') loadVerificationData();
    if (activeTab === 'documents') loadDocuments();
    if (activeTab === 'visits') loadVisits();
  }, [activeTab, loadVerificationData, loadDocuments, loadVisits]);

  // Lifecycle action handlers
  const handlePublish = async () => {
    if (!id) return;
    try {
      const updated = await propertiesApi.publish(id);
      setProperty(updated);
      alert('Property published to public discovery.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Publish failed');
    }
  };

  const handlePause = async () => {
    if (!id) return;
    try {
      const updated = await propertiesApi.pause(id);
      setProperty(updated);
      alert('Property listing paused.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Pause failed');
    }
  };

  const handleArchive = async () => {
    if (!id) return;
    if (!confirm('Are you sure you want to archive this property? It will be removed from active inventory.')) return;
    try {
      const updated = await propertiesApi.archive(id);
      setProperty(updated);
      alert('Property archived.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Archive failed');
    }
  };

  const handleMarkSold = async () => {
    if (!id) return;
    try {
      const updated = await propertiesApi.markSold(id);
      setProperty(updated);
      alert('Property marked as SOLD.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleMarkRented = async () => {
    if (!id) return;
    try {
      const updated = await propertiesApi.markRented(id);
      setProperty(updated);
      alert('Property marked as RENTED.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setActionLoading(true);
    try {
      const updated = await propertiesApi.update(id, editForm);
      setProperty(updated);
      setIsEditModalOpen(false);
      alert('Property details updated successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Image actions
  const handleAddImage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setActionLoading(true);
    try {
      if (imageUploadMode === 'file') {
        if (!imageFile) {
          alert('Please select a photo file from your computer.');
          setActionLoading(false);
          return;
        }
        await propertiesApi.uploadImage(id, imageFile, imageIsPrimary);
      } else {
        await propertiesApi.addImage(id, newImage);
      }
      setIsAddImageModalOpen(false);
      setImageFile(null);
      setImagePreview(null);
      loadProperty();
      alert('Photo added to gallery successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to add image');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMakePrimaryImage = async (imageId: string) => {
    if (!id) return;
    try {
      await propertiesApi.updateImage(id, imageId, { is_primary: true });
      loadProperty();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update image');
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!id) return;
    if (!confirm('Remove this image?')) return;
    try {
      await propertiesApi.deleteImage(id, imageId);
      loadProperty();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete image');
    }
  };

  // Run Preliminary Verification
  const handleRunVerification = async () => {
    if (!id) return;
    setVerifLoading(true);
    try {
      const res = await verificationApi.run(id, {
        survey_number: surveyNum || undefined,
        subdivision_number: subdivNum || undefined,
        patta_number: pattaNum || undefined,
        planning_authority: planningAuth || undefined,
        planning_approval_number: planningNum || undefined,
        disclaimer_acknowledged: true,
      });
      setVerification(res);
      loadVerificationData();
      alert('Preliminary verification assessment executed successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Verification failed');
    } finally {
      setVerifLoading(false);
    }
  };

  // Upload Document
  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !selectedFile) return;
    setActionLoading(true);
    try {
      await documentsApi.upload(selectedFile, docType, {
        propertyId: id,
        notes: docNotes,
      });
      setIsUploadDocModalOpen(false);
      setSelectedFile(null);
      setDocNotes('');
      loadDocuments();
      alert('Document uploaded successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Book Visit
  const handleBookVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !visitClientId) return;
    setActionLoading(true);
    try {
      await siteVisitsApi.create({
        property_id: id,
        client_id: visitClientId,
        scheduled_at: new Date(visitDate).toISOString(),
        status: 'CONFIRMED',
        notes: visitNotes,
      });
      setIsBookVisitModalOpen(false);
      loadVisits();
      alert('Site visit confirmed and booked.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Booking failed');
    } finally {
      setActionLoading(false);
    }
  };

  const formatPrice = (price: number) => {
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  if (isLoading) {
    return <div className="p-12 text-center text-xs text-gray-500">Loading property record...</div>;
  }

  if (!property) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm font-semibold text-gray-900">Property not found</p>
        <Link to="/properties" className="text-xs text-[var(--color-primary)] hover:underline mt-2 inline-block">
          Return to properties list
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--color-border-ui)] pb-4">
        <div className="flex items-center space-x-2">
          <Link
            to="/properties"
            className="inline-flex items-center text-xs font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-ink)]"
          >
            <ChevronLeft className="mr-1 h-4 w-4" /> Properties
          </Link>
          <span className="text-gray-300">/</span>
          <span className="font-mono text-xs font-bold text-[var(--color-ink)]">{property.public_reference}</span>
        </div>

        {/* Lifecycle Mutators */}
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant={
              property.status === 'PUBLISHED'
                ? 'success'
                : property.status === 'DRAFT'
                ? 'neutral'
                : property.status === 'PAUSED'
                ? 'warning'
                : 'secondary'
            }
          >
            {property.status}
          </Badge>

          {property.status !== 'PUBLISHED' && (
            <Button size="sm" variant="default" onClick={handlePublish} className="text-xs h-8 flex items-center gap-1">
              <Play className="h-3 w-3" /> Publish
            </Button>
          )}

          {property.status === 'PUBLISHED' && (
            <Button size="sm" variant="outline" onClick={handlePause} className="text-xs h-8 flex items-center gap-1">
              <Pause className="h-3 w-3" /> Pause
            </Button>
          )}

          {property.transaction_type === 'SALE' && property.status !== 'SOLD' && (
            <Button size="sm" variant="outline" onClick={handleMarkSold} className="text-xs h-8 text-emerald-800">
              Mark Sold
            </Button>
          )}

          {property.transaction_type !== 'SALE' && property.status !== 'RENTED' && (
            <Button size="sm" variant="outline" onClick={handleMarkRented} className="text-xs h-8 text-blue-800">
              Mark Rented
            </Button>
          )}

          <Button size="sm" variant="secondary" onClick={() => setIsEditModalOpen(true)} className="text-xs h-8 flex items-center gap-1">
            <Edit className="h-3 w-3" /> Edit
          </Button>

          {property.status !== 'ARCHIVED' && (
            <Button size="sm" variant="ghost" onClick={handleArchive} className="text-xs h-8 text-red-600 hover:bg-red-50">
              <Archive className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>

      {/* Hero Presentation Header */}
      <div className="bg-white rounded-lg border border-[var(--color-border-ui)] p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-2 max-w-3xl">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-[10px]">{property.property_type}</Badge>
              <Badge variant="outline" className="text-[10px]">For {property.transaction_type}</Badge>
              {property.taluk && <span className="text-xs text-gray-500">Taluk: {property.taluk}</span>}
            </div>
            <h1 className="font-serif text-3xl font-bold text-[var(--color-ink)] leading-tight">
              {property.title}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--color-ink-secondary)] pt-1">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-gray-400" />
                {property.locality}, {property.city} ({property.pincode})
              </span>
              <span className="flex items-center gap-1">
                <Building className="h-3.5 w-3.5 text-gray-400" />
                {property.bedrooms ? `${property.bedrooms} BHK` : 'Plotted'} • {property.built_up_area || property.plot_area} sq.ft
              </span>
              <span className="flex items-center gap-1 text-[var(--color-forest)] font-semibold">
                <ShieldCheck className="h-3.5 w-3.5" />
                Tamil Nadu Legal Verification Ready
              </span>
            </div>
          </div>

          <div className="shrink-0 bg-[var(--color-parchment-warm)] p-5 rounded-md border border-[var(--color-border-ui)] text-right lg:min-w-[220px]">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[var(--color-ink-muted)]">
              {property.transaction_type === 'SALE' ? 'Asking Price' : 'Monthly Rent'}
            </p>
            <div className="font-serif text-3xl font-bold text-[var(--color-forest)] mt-1">
              {formatPrice(property.price)}
            </div>
            <p className="text-[11px] text-[var(--color-ink-muted)] mt-0.5">
              {property.price_negotiable ? 'Price Negotiable' : 'Fixed Price'}
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <Button size="sm" onClick={() => setIsBookVisitModalOpen(true)} className="w-full text-xs">
                Schedule Site Visit
              </Button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="mt-8 border-b border-[var(--color-border-ui)] flex space-x-6 text-xs">
          {[
            { key: 'overview', label: 'Overview & Details' },
            {
              key: 'tngis',
              label: (
                <span className="flex items-center gap-1.5">
                  TNGIS Land Records
                  {property.internal_notes?.includes('[TNGIS') && (
                    <span className="h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-emerald-200" title="Verified in Database" />
                  )}
                </span>
              ),
            },
            { key: 'images', label: `Gallery (${property.images?.length || 0})` },
            { key: 'verification', label: 'Preliminary Verification (TN Intelligence)' },
            { key: 'documents', label: 'Documents Vault' },
            { key: 'visits', label: 'Site Visits' },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`pb-3 font-semibold transition-colors border-b-2 whitespace-nowrap ${
                activeTab === tab.key
                  ? 'border-[var(--color-gold)] text-[var(--color-forest)]'
                  : 'border-transparent text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Col 1: Specifications */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-[var(--color-ink-muted)]">
                Specifications
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Built-up Area</span>
                <span className="font-medium text-gray-900">{property.built_up_area || '-'} sq.ft</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Plot Area</span>
                <span className="font-medium text-gray-900">{property.plot_area || '-'} sq.ft</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Bedrooms</span>
                <span className="font-medium text-gray-900">{property.bedrooms || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Bathrooms</span>
                <span className="font-medium text-gray-900">{property.bathrooms || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Floor Level</span>
                <span className="font-medium text-gray-900">
                  {property.floor !== null && property.floor !== undefined ? `${property.floor} of ${property.total_floors || '-'}` : '-'}
                </span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Facing</span>
                <span className="font-medium text-gray-900">{property.facing || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Furnishing</span>
                <span className="font-medium text-gray-900">{property.furnishing_state || '-'}</span>
              </div>
            </CardContent>
          </Card>

          {/* Col 2: Location Details */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-[var(--color-ink-muted)]">
                Location & Survey Boundaries
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">District</span>
                <span className="font-medium text-gray-900">{property.district}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Taluk</span>
                <span className="font-medium text-gray-900">{property.taluk || '-'}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Locality</span>
                <span className="font-medium text-gray-900">{property.locality}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Pincode</span>
                <span className="font-medium text-gray-900">{property.pincode}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Full Address</span>
                <span className="font-medium text-gray-900 text-right max-w-[150px] truncate">
                  {property.address || `${property.locality}, ${property.city}`}
                </span>
              </div>
              <div className="flex items-center justify-between pt-1">
                <span className="text-gray-500">Location Link</span>
                {property.google_maps_url ? (
                  <a
                    href={property.google_maps_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    <MapPin className="h-3.5 w-3.5 text-red-500" /> Open Map Link ↗
                  </a>
                ) : (
                  <span className="text-gray-400 italic">Not set</span>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Col 3: Private Owner Details */}
          <Card className="bg-amber-50/30 border-amber-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs uppercase tracking-wider text-amber-900">
                Private Owner Mandate
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between border-b border-amber-100 pb-2">
                <span className="text-gray-500">Owner Name</span>
                <span className="font-semibold text-gray-900">{property.owner_name || 'Direct / On-file'}</span>
              </div>
              <div className="flex justify-between border-b border-amber-100 pb-2">
                <span className="text-gray-500">Owner Contact</span>
                <span className="font-mono text-gray-900">{property.owner_phone || 'Private'}</span>
              </div>
              <div className="flex justify-between border-b border-amber-100 pb-2">
                <span className="text-gray-500">Ad Authorization</span>
                <span className="font-medium text-emerald-800">
                  {property.advertisement_authorized ? 'Authorized' : 'Pending'}
                </span>
              </div>
              <div>
                <span className="text-gray-500 block mb-1">Consultant Internal Notes:</span>
                <p className="bg-white p-2 rounded border border-amber-200 text-gray-700 italic text-[11px]">
                  {property.internal_notes || 'No confidential consultant notes recorded.'}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TAB: TNGIS REVENUE & GIS RECORDS */}
      {activeTab === 'tngis' && (
        <TngisPropertyTab
          property={property}
          onOpenTngisSearch={() => setIsTngisModalOpen(true)}
          onOpenTnecModal={() => setIsTnecModalOpen(true)}
        />
      )}

      {/* TAB 2: IMAGES GALLERY */}
      {activeTab === 'images' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-white p-4 rounded-lg border border-[var(--color-border-ui)]">
            <div>
              <h3 className="text-xs font-semibold text-gray-900 uppercase tracking-wider">Property Photo Vault</h3>
              <p className="text-[11px] text-gray-500">Manage promotional photos and set primary search thumbnail</p>
            </div>
            <Button size="sm" onClick={() => setIsAddImageModalOpen(true)} className="text-xs flex items-center gap-1">
              <Upload className="h-3.5 w-3.5" /> Add Photo
            </Button>
          </div>

          {property.images && property.images.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
              {property.images.map((img) => (
                <div key={img.id} className="relative group rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                  <img src={img.storage_key} alt="" className="h-44 w-full object-cover" />
                  {img.is_primary && (
                    <div className="absolute top-2 left-2 bg-[var(--color-gold)] text-white px-2 py-0.5 rounded text-[10px] font-bold flex items-center gap-1 shadow">
                      <Star className="h-3 w-3 fill-current" /> Primary
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    {!img.is_primary && (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleMakePrimaryImage(img.id)}
                        className="text-xs h-7 px-2"
                      >
                        Set Primary
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteImage(img.id)}
                      className="text-xs h-7 px-2 text-red-400 hover:text-red-200"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white p-12 text-center rounded-lg border border-[var(--color-border-ui)]">
              <p className="text-xs text-gray-500">No images uploaded yet. Click "Add Photo" to attach photos.</p>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: TAMIL NADU PRELIMINARY VERIFICATION */}
      {activeTab === 'verification' && (
        <div className="space-y-6">
          {/* Action Header */}
          <div className="bg-white p-5 rounded-lg border border-[var(--color-border-ui)] flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-[var(--color-forest)]" />
                <h3 className="text-sm font-bold text-gray-900">Tamil Nadu Preliminary Property Verification</h3>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Deterministic rule evaluation for Patta, EC encumbrance history, CMDA/DTCP planning approval & TNRERA compliance.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Button
                variant="outline"
                onClick={() => setIsTngisModalOpen(true)}
                className="text-xs flex items-center gap-1.5 border-[var(--color-forest)] text-[var(--color-forest)] font-bold hover:bg-emerald-50"
              >
                <Search className="h-4 w-4" /> Fetch & Verify TNGIS Records
              </Button>
              <Button
                onClick={handleRunVerification}
                isLoading={verifLoading}
                className="text-xs flex items-center gap-1.5"
              >
                <ShieldCheck className="h-4 w-4" /> Run Verification Engine
              </Button>
            </div>
          </div>

          {/* Verification Parameters Override */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Registration & Revenue Identifiers (Tamil Nadu)
              </h4>
              <span className="text-[11px] text-gray-500 font-mono bg-white px-2 py-0.5 rounded border border-gray-200">
                17,237 Revenue Villages Database Linked
              </span>
            </div>

            {/* Row 1: Location Dropdowns (District -> Taluk -> Revenue Village) */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white p-3 rounded-md border border-gray-200">
              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-0.5">
                  1. District (TN)
                </label>
                <Select
                  className="h-8 text-xs"
                  value={verifDistrict}
                  onChange={(e) => {
                    const d = e.target.value;
                    setVerifDistrict(d);
                    setVerifTaluk('');
                    setVerifVillage('');
                  }}
                >
                  <option value="">Select District</option>
                  {getTnDistricts().map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-0.5">
                  2. Taluk
                </label>
                <Select
                  className="h-8 text-xs"
                  value={verifTaluk}
                  onChange={(e) => {
                    const t = e.target.value;
                    setVerifTaluk(t);
                    setVerifVillage('');
                  }}
                  disabled={!verifDistrict || verifTaluks.length === 0}
                >
                  <option value="">
                    {!verifDistrict ? 'Select District first' : 'Select Taluk'}
                  </option>
                  {verifTaluks.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-gray-600 mb-0.5">
                  3. Revenue Village {verifVillages.length > 0 && `(${verifVillages.length})`}
                </label>
                <Select
                  className="h-8 text-xs"
                  value={verifVillage}
                  onChange={(e) => setVerifVillage(e.target.value)}
                  disabled={!verifTaluk || verifVillages.length === 0}
                >
                  <option value="">
                    {!verifTaluk
                      ? 'Select Taluk first'
                      : verifVillages.length === 0
                      ? 'No villages found'
                      : 'Select Revenue Village'}
                  </option>
                  {verifVillage && !verifVillages.includes(verifVillage) && (
                    <option value={verifVillage}>{verifVillage} (Current)</option>
                  )}
                  {verifVillages.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            {/* Row 2: Survey, Patta & Planning Authority */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div>
                <label className="block text-[11px] text-gray-600 mb-0.5">Survey Number</label>
                <Input
                  className="h-8 text-xs"
                  placeholder="e.g. 142"
                  value={surveyNum}
                  onChange={(e) => setSurveyNum(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[11px] text-gray-600 mb-0.5">Subdivision Number</label>
                <Input
                  className="h-8 text-xs"
                  placeholder="e.g. 2B"
                  value={subdivNum}
                  onChange={(e) => setSubdivNum(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[11px] text-gray-600 mb-0.5">Patta Number</label>
                <Input
                  className="h-8 text-xs"
                  placeholder="e.g. 1045"
                  value={pattaNum}
                  onChange={(e) => setPattaNum(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-[11px] text-gray-600 mb-0.5">Planning Authority</label>
                <Select
                  className="h-8 text-xs"
                  value={planningAuth}
                  onChange={(e) => setPlanningAuth(e.target.value)}
                >
                  <option value="CMDA">CMDA</option>
                  <option value="DTCP">DTCP</option>
                  <option value="LOCAL_BODY">LOCAL BODY</option>
                </Select>
              </div>
              <div>
                <label className="block text-[11px] text-gray-600 mb-0.5">Approval Number</label>
                <Input
                  className="h-8 text-xs"
                  placeholder="e.g. PPA/WDCN09/..."
                  value={planningNum}
                  onChange={(e) => setPlanningNum(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Verification Results Display */}
          {verification ? (
            <div className="space-y-6">
              {/* Top Score Banner */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="bg-white">
                  <CardContent className="p-4">
                    <span className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">Overall Risk</span>
                    <div className="mt-1 flex items-center gap-2">
                      <Badge
                        variant={
                          verification.risk_level === 'LOW'
                            ? 'success'
                            : verification.risk_level === 'MEDIUM'
                            ? 'warning'
                            : 'danger'
                        }
                        className="text-sm px-3 py-1 font-bold"
                      >
                        {verification.risk_level} RISK
                      </Badge>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-white">
                  <CardContent className="p-4">
                    <span className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                      Documentary Completeness
                    </span>
                    <div className="mt-1 flex items-baseline gap-2">
                      <span className="text-2xl font-bold text-gray-900">{verification.completeness_score}%</span>
                      <span className="text-xs text-gray-400">of standard TN checklist</span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-white">
                  <CardContent className="p-4">
                    <span className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">TNRERA Status</span>
                    <div className="mt-1 text-sm font-semibold text-gray-900">
                      {verification.rera_applicability}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Granular Checks Table */}
              <Card>
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-xs uppercase tracking-wider text-gray-700">
                    Granular Check Findings & Explainability
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y divide-gray-100 text-xs">
                    {verification.checks.map((c) => (
                      <div key={c.checklist_code} className="p-4 flex items-start justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900">{c.item_name}</span>
                            <span className="font-mono text-[10px] text-gray-400">{c.checklist_code}</span>
                          </div>
                          <p className="text-gray-600 text-[11px]">{c.notes || 'Evaluated against documentary evidence.'}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Badge
                            variant={
                              c.status === 'PASS'
                                ? 'success'
                                : c.status === 'REVIEW'
                                ? 'warning'
                                : c.status === 'FAIL'
                                ? 'danger'
                                : 'neutral'
                            }
                          >
                            {c.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Consultant Recommended Actions */}
              {actions.length > 0 && (
                <Card>
                  <CardHeader className="py-3 px-4">
                    <CardTitle className="text-xs uppercase tracking-wider text-gray-700">
                      Prioritized Consultant Action Items
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="divide-y divide-gray-100 text-xs">
                      {actions.map((act, i) => (
                        <div key={i} className="p-3.5 flex items-start gap-3">
                          <Badge
                            variant={act.priority === 'HIGH' ? 'danger' : act.priority === 'MEDIUM' ? 'warning' : 'info'}
                            className="mt-0.5 text-[10px]"
                          >
                            {act.priority}
                          </Badge>
                          <div>
                            <p className="font-medium text-gray-900">{act.description}</p>
                            <span className="text-[10px] text-gray-400 uppercase tracking-wider">Action: {act.action_type}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Mandatory Legal Disclaimer */}
              <div className="rounded-md bg-amber-50 p-4 border border-amber-200 text-[11px] text-amber-900 leading-relaxed flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-semibold">Statutory Preliminary Disclaimer:</strong>
                  {verification.disclaimer}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white p-12 text-center rounded-lg border border-[var(--color-border-ui)]">
              <ShieldCheck className="h-8 w-8 text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-500">
                Preliminary verification has not been run for this property yet.
              </p>
              <Button size="sm" onClick={handleRunVerification} isLoading={verifLoading} className="mt-3 text-xs">
                Execute Verification Assessment
              </Button>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: DOCUMENTS VAULT */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-4 rounded-lg border border-[var(--color-border-ui)] shadow-sm">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-[var(--color-forest)]" />
                <h3 className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                  Property Documents & Title Vault
                </h3>
              </div>
              <p className="text-[11px] text-gray-500 mt-0.5">
                Organized into official Tamil Nadu land record & deed sections: EC, Patta, A-register, FMB, Certified Copy & Combined Sketch.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsTnecModalOpen(true)}
                className="text-xs flex items-center gap-1.5 bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 text-blue-700 hover:bg-blue-100 font-semibold shadow-2xs"
              >
                <FileText className="h-3.5 w-3.5 text-blue-600" />
                Get EC (TNREGINET)
              </Button>
              <Button
                size="sm"
                onClick={() => openUploadForSection()}
                className="text-xs flex items-center gap-1 shrink-0"
              >
                <Upload className="h-3.5 w-3.5" /> Upload Document
              </Button>
            </div>
          </div>

          {/* Section Selector Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs border-b border-gray-200">
            <button
              onClick={() => setSelectedVaultSection('all')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap text-xs flex items-center gap-1.5 ${
                selectedVaultSection === 'all'
                  ? 'bg-[var(--color-forest)] text-white font-bold shadow-sm'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              All Sections ({documents.length})
            </button>
            {VAULT_SECTIONS.map((sec) => {
              const count = groupedDocs[sec.id]?.length || 0;
              const isActive = selectedVaultSection === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setSelectedVaultSection(sec.id)}
                  className={`px-3 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap text-xs flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-[var(--color-forest)] text-white font-bold shadow-sm'
                      : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
                  }`}
                >
                  <span>{sec.shortName}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      isActive ? 'bg-white/20 text-white' : count > 0 ? sec.badgeBg : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
            {(groupedDocs['Other']?.length || 0) > 0 && (
              <button
                onClick={() => setSelectedVaultSection('Other')}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors whitespace-nowrap text-xs flex items-center gap-1.5 ${
                  selectedVaultSection === 'Other'
                    ? 'bg-[var(--color-forest)] text-white font-bold shadow-sm'
                    : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
                }`}
              >
                <span>Other</span>
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-gray-100 text-gray-600">
                  {groupedDocs['Other'].length}
                </span>
              </button>
            )}
          </div>

          {docsLoading ? (
            <div className="p-12 text-center text-xs text-gray-500 bg-white rounded-lg border border-gray-200">
              Loading property document vault...
            </div>
          ) : (
            <div className="space-y-4">
              {VAULT_SECTIONS.filter(
                (sec) => selectedVaultSection === 'all' || selectedVaultSection === sec.id
              ).map((sec) => {
                const sectionDocs = groupedDocs[sec.id] || [];
                return (
                  <div
                    key={sec.id}
                    className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden"
                  >
                    {/* Section Header */}
                    <div className="p-3.5 bg-gray-50/70 border-b border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${sec.badgeBg}`}>
                          {sec.shortName}
                        </span>
                        <div>
                          <h4 className="text-xs font-bold text-gray-900">{sec.name}</h4>
                          <p className="text-[11px] text-gray-500 line-clamp-1">{sec.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                        <span className="text-[11px] text-gray-500 font-medium">
                          {sectionDocs.length === 1
                            ? '1 Document'
                            : `${sectionDocs.length} Documents`}
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openUploadForSection(sec.defaultDocType)}
                          className="h-7 text-xs px-2.5"
                        >
                          <Upload className="h-3 w-3 mr-1" /> Upload {sec.shortName}
                        </Button>
                      </div>
                    </div>

                    {/* FMB Map Generator — only for the FMB section */}
                    {sec.id === 'FMB' && (
                      <FmbGeneratorPanel
                        propertyId={id!}
                        onDocumentSaved={loadDocuments}
                      />
                    )}

                    {/* Section Body */}
                    {sectionDocs.length === 0 ? (
                      <div className="p-6 text-center bg-white">
                        <p className="text-xs text-gray-400">
                          No {sec.shortName} document uploaded yet for this property.
                        </p>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => openUploadForSection(sec.defaultDocType)}
                          className="mt-1.5 text-xs text-[var(--color-forest)] font-medium"
                        >
                          + Upload {sec.name}
                        </Button>
                      </div>
                    ) : (
                      <div className="divide-y divide-gray-100 text-xs">
                        {sectionDocs.map((doc) => (
                          <div
                            key={doc.id}
                            className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-gray-50/50 transition-colors"
                          >
                            <div className="flex items-start space-x-3">
                              <div className="p-2 rounded bg-amber-50 text-amber-800 border border-amber-200/60 mt-0.5">
                                <FileText className="h-4 w-4" />
                              </div>
                              <div>
                                <p className="font-semibold text-gray-900 text-xs">{doc.original_filename}</p>
                                <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500 mt-0.5">
                                  <Badge variant="outline" className="text-[10px] font-mono">
                                    {doc.document_type}
                                  </Badge>
                                  <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                                  <span>• Uploaded on {new Date(doc.created_at).toLocaleDateString()}</span>
                                  {doc.notes && (
                                    <span className="text-gray-600 italic bg-gray-100 px-1.5 py-0.5 rounded">
                                      Ref: {doc.notes}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                              <Badge
                                variant={
                                  doc.status === 'PRELIMINARILY_CHECKED'
                                    ? 'success'
                                    : doc.status === 'REQUIRES_ATTENTION'
                                    ? 'danger'
                                    : 'warning'
                                }
                                className="text-[10px]"
                              >
                                {doc.status}
                              </Badge>

                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => documentsApi.download(doc.id, doc.original_filename)}
                                className="text-xs h-7 px-2.5 flex items-center gap-1"
                              >
                                <Download className="h-3 w-3" /> Download
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Other Section if any */}
              {(selectedVaultSection === 'all' || selectedVaultSection === 'Other') &&
                (groupedDocs['Other'] || []).length > 0 && (
                  <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
                    <div className="p-3.5 bg-gray-50/70 border-b border-gray-200 flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2 py-0.5 rounded text-xs font-bold font-mono bg-gray-100 text-gray-800">
                          Other
                        </span>
                        <div>
                          <h4 className="text-xs font-bold text-gray-900">Other Approvals & Records</h4>
                          <p className="text-[11px] text-gray-500">
                            Planning permits, building sanctions, property tax receipts, and general files
                          </p>
                        </div>
                      </div>
                      <span className="text-[11px] text-gray-500 font-medium">
                        {groupedDocs['Other'].length} Documents
                      </span>
                    </div>

                    <div className="divide-y divide-gray-100 text-xs">
                      {groupedDocs['Other'].map((doc) => (
                        <div
                          key={doc.id}
                          className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-gray-50/50"
                        >
                          <div className="flex items-start space-x-3">
                            <div className="p-2 rounded bg-gray-100 text-gray-600 mt-0.5">
                              <FileText className="h-4 w-4" />
                            </div>
                            <div>
                              <p className="font-semibold text-gray-900 text-xs">{doc.original_filename}</p>
                              <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500 mt-0.5">
                                <Badge variant="outline" className="text-[10px] font-mono">
                                  {doc.document_type}
                                </Badge>
                                <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                                <span>• Uploaded on {new Date(doc.created_at).toLocaleDateString()}</span>
                                {doc.notes && <span className="text-gray-600 italic">Ref: {doc.notes}</span>}
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                            <Badge
                              variant={
                                doc.status === 'PRELIMINARILY_CHECKED'
                                  ? 'success'
                                  : doc.status === 'REQUIRES_ATTENTION'
                                  ? 'danger'
                                  : 'warning'
                              }
                              className="text-[10px]"
                            >
                              {doc.status}
                            </Badge>

                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => documentsApi.download(doc.id, doc.original_filename)}
                              className="text-xs h-7 px-2.5 flex items-center gap-1"
                            >
                              <Download className="h-3 w-3" /> Download
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: SITE VISITS */}
      {activeTab === 'visits' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-white p-4 rounded-lg border border-[var(--color-border-ui)]">
            <div>
              <h3 className="text-xs font-semibold text-gray-900 uppercase tracking-wider">Scheduled Site Inspections</h3>
              <p className="text-[11px] text-gray-500">Track client walkthroughs and feedback for this property</p>
            </div>
            <Button size="sm" onClick={() => setIsBookVisitModalOpen(true)} className="text-xs flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" /> Book Inspection
            </Button>
          </div>

          {visitsLoading ? (
            <div className="p-8 text-center text-xs text-gray-500">Loading site visits...</div>
          ) : visits.length === 0 ? (
            <div className="bg-white p-12 text-center rounded-lg border border-[var(--color-border-ui)]">
              <Calendar className="h-8 w-8 text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-500">No visits scheduled for this property.</p>
              <Button size="sm" onClick={() => setIsBookVisitModalOpen(true)} className="mt-3 text-xs">
                Schedule Site Visit
              </Button>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-[var(--color-border-ui)] overflow-hidden">
              <div className="divide-y divide-gray-100 text-xs">
                {visits.map((v) => (
                  <div key={v.id} className="p-4 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-gray-900">
                          {new Date(v.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })} at{' '}
                          {new Date(v.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <Badge variant="warning">{v.status}</Badge>
                      </div>
                      <p className="text-gray-600 mt-1">
                        Client: <span className="font-semibold text-gray-900">{v.client?.full_name || 'Client'}</span> ({v.client?.phone || 'N/A'})
                      </p>
                      {v.notes && <p className="text-gray-400 text-[11px] mt-0.5">{v.notes}</p>}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate('/site-visits')}
                      className="text-xs h-7"
                    >
                      Manage Visit
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODAL: EDIT PROPERTY */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Edit Property Listing"
        description="Update specifications, price, or location details."
      >
        <form onSubmit={handleEditSubmit} className="space-y-4 max-h-[75vh] overflow-y-auto px-1">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Title</label>
            <Input
              required
              value={editForm.title || ''}
              onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Price (₹ INR)</label>
              <Input
                type="number"
                required
                value={editForm.price || 0}
                onChange={(e) => setEditForm({ ...editForm, price: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Built-up Area (sq.ft)</label>
              <Input
                type="number"
                value={editForm.built_up_area || ''}
                onChange={(e) => setEditForm({ ...editForm, built_up_area: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Bedrooms</label>
              <Input
                type="number"
                value={editForm.bedrooms || ''}
                onChange={(e) => setEditForm({ ...editForm, bedrooms: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Bathrooms</label>
              <Input
                type="number"
                value={editForm.bathrooms || ''}
                onChange={(e) => setEditForm({ ...editForm, bathrooms: Number(e.target.value) })}
              />
            </div>
          </div>

          {/* Tamil Nadu Location Dropdowns */}
          <div className="border border-gray-200 rounded-lg p-3 bg-gray-50/50">
            <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
              Tamil Nadu Location Details
            </h4>
            <TnLocationSelector
              district={editForm.district || ''}
              taluk={editForm.taluk || ''}
              village={editForm.locality || ''}
              city={editForm.city || ''}
              onDistrictChange={(d) => setEditForm((prev) => ({ ...prev, district: d }))}
              onTalukChange={(t) => setEditForm((prev) => ({ ...prev, taluk: t }))}
              onVillageChange={(v) => setEditForm((prev) => ({ ...prev, locality: v }))}
              onCityChange={(c) => setEditForm((prev) => ({ ...prev, city: c }))}
              layout="grid-2"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Pincode</label>
              <Input
                value={editForm.pincode || ''}
                onChange={(e) => setEditForm({ ...editForm, pincode: e.target.value })}
                placeholder="e.g. 600020"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Street Address</label>
              <Input
                value={editForm.address || ''}
                onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                placeholder="Door No, Street name"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-red-500" />
                Location Link (Google Maps URL / Pin)
              </span>
              <span className="text-[10px] text-gray-400 font-normal">e.g. https://maps.app.goo.gl/...</span>
            </label>
            <Input
              value={editForm.google_maps_url || ''}
              onChange={(e) => setEditForm({ ...editForm, google_maps_url: e.target.value })}
              placeholder="https://maps.google.com/?q=... or https://maps.app.goo.gl/..."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Internal Notes</label>
            <Input
              value={editForm.internal_notes || ''}
              onChange={(e) => setEditForm({ ...editForm, internal_notes: e.target.value })}
              placeholder="Private consultant notes..."
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Save Changes
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: ADD IMAGE */}
      <Modal
        isOpen={isAddImageModalOpen}
        onClose={() => {
          setIsAddImageModalOpen(false);
          setImageFile(null);
          setImagePreview(null);
        }}
        title="Add Photo to Gallery"
        description="Upload photos directly from your computer or provide an external image URL."
      >
        <div className="flex border-b border-gray-200 mb-4">
          <button
            type="button"
            className={`pb-2 px-3 text-xs font-semibold border-b-2 transition-colors ${
              imageUploadMode === 'file'
                ? 'border-[var(--color-primary)] text-[var(--color-primary)]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setImageUploadMode('file')}
          >
            Upload from Computer
          </button>
          <button
            type="button"
            className={`pb-2 px-3 text-xs font-semibold border-b-2 transition-colors ${
              imageUploadMode === 'url'
                ? 'border-[var(--color-primary)] text-[var(--color-primary)]'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setImageUploadMode('url')}
          >
            External Image Link
          </button>
        </div>

        <form onSubmit={handleAddImage} className="space-y-4">
          {imageUploadMode === 'file' ? (
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-2">
                Choose Property Photo (.jpg, .png, .webp)
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-gray-400 transition-colors bg-gray-50">
                <input
                  type="file"
                  id="property-photo-input"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setImageFile(file);
                      setImagePreview(URL.createObjectURL(file));
                    }
                  }}
                />
                {imagePreview ? (
                  <div className="space-y-2">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="mx-auto h-40 max-w-full rounded object-contain border border-gray-200 bg-white"
                    />
                    <div className="text-xs text-gray-600 font-medium">
                      {imageFile?.name} ({(imageFile?.size ? imageFile.size / 1024 : 0).toFixed(1)} KB)
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const input = document.getElementById('property-photo-input') as HTMLInputElement;
                        if (input) input.click();
                      }}
                      className="text-xs"
                    >
                      Choose Different Photo
                    </Button>
                  </div>
                ) : (
                  <label
                    htmlFor="property-photo-input"
                    className="cursor-pointer flex flex-col items-center justify-center py-4 space-y-2"
                  >
                    <Upload className="h-8 w-8 text-gray-400" />
                    <span className="text-xs font-medium text-[var(--color-forest)]">
                      Click to browse photos from your computer
                    </span>
                    <span className="text-[11px] text-gray-500">
                      JPEG, PNG, or WEBP up to 15MB
                    </span>
                  </label>
                )}
              </div>

              <div className="flex items-center gap-2 mt-3">
                <input
                  type="checkbox"
                  id="image_is_primary"
                  checked={imageIsPrimary}
                  onChange={(e) => setImageIsPrimary(e.target.checked)}
                  className="rounded text-[var(--color-primary)]"
                />
                <label htmlFor="image_is_primary" className="text-xs text-gray-700">
                  Set as primary cover photo for listing
                </label>
              </div>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Image URL / Storage Key</label>
                <Input
                  required
                  placeholder="https://images.unsplash.com/photo-..."
                  value={newImage.storage_key}
                  onChange={(e) => setNewImage({ ...newImage, storage_key: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">Filename</label>
                <Input
                  required
                  placeholder="living_room.jpg"
                  value={newImage.original_filename}
                  onChange={(e) => setNewImage({ ...newImage, original_filename: e.target.value })}
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_primary_url"
                  checked={newImage.is_primary}
                  onChange={(e) => setNewImage({ ...newImage, is_primary: e.target.checked })}
                  className="rounded text-[var(--color-primary)]"
                />
                <label htmlFor="is_primary_url" className="text-xs text-gray-700">
                  Set as primary thumbnail for search results
                </label>
              </div>
            </>
          )}

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsAddImageModalOpen(false);
                setImageFile(null);
                setImagePreview(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              {imageUploadMode === 'file' ? 'Upload Photo' : 'Add Image'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: UPLOAD DOCUMENT */}
      <Modal
        isOpen={isUploadDocModalOpen}
        onClose={() => setIsUploadDocModalOpen(false)}
        title="Upload Property Document"
        description="Upload legal deeds, land records, or planning permissions (.pdf, .jpg, .png)."
      >
        <form onSubmit={handleUploadDocument} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Document Category</label>
            <Select value={docType} onChange={(e) => setDocType(e.target.value)}>
              <option value="EC">Encumbrance Certificate (EC)</option>
              <option value="PATTA">Patta / Chitta / TSLR</option>
              <option value="A_REGISTER">A-Register Extract</option>
              <option value="FMB">Field Measurement Book (FMB)</option>
              <option value="CERTIFIED_COPY">Certified Copy (Title Deed)</option>
              <option value="COMBINED_SKETCH">Combined Sketch</option>
              <option value="SALE_DEED">Sale Deed</option>
              <option value="PARENT_DOCUMENT">Parent / Link Document</option>
              <option value="CMDA_APPROVAL">CMDA Planning Approval</option>
              <option value="DTCP_APPROVAL">DTCP Layout Approval</option>
              <option value="TNRERA_REGISTRATION">TNRERA Registration</option>
              <option value="PROPERTY_TAX_RECEIPT">Property Tax Receipt</option>
              <option value="OTHER">Other Document</option>
            </Select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Select File</label>
            <Input
              type="file"
              required
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                }
              }}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Registration Notes</label>
            <Input
              placeholder="e.g. SRO Mylapore Doc # 2451/2018"
              value={docNotes}
              onChange={(e) => setDocNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsUploadDocModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading} disabled={!selectedFile}>
              Upload File
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: BOOK VISIT */}
      <Modal
        isOpen={isBookVisitModalOpen}
        onClose={() => setIsBookVisitModalOpen(false)}
        title="Book Property Inspection Visit"
        description="Schedule a prospective buyer visit for this property."
      >
        <form onSubmit={handleBookVisit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Client UUID</label>
            <Input
              required
              placeholder="Enter client UUID"
              value={visitClientId}
              onChange={(e) => setVisitClientId(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Inspection Timestamp</label>
            <Input
              type="datetime-local"
              required
              value={visitDate}
              onChange={(e) => setVisitDate(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Visit Instructions</label>
            <Input
              placeholder="e.g. Client requested evening lighting check"
              value={visitNotes}
              onChange={(e) => setVisitNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsBookVisitModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Schedule Visit
            </Button>
          </div>
        </form>
      </Modal>

      {/* TNGIS Property & Land Records Search Modal */}
      <TngisSearchModal
        isOpen={isTngisModalOpen}
        onClose={() => setIsTngisModalOpen(false)}
        initialPropertyId={id}
        initialDistrict={verifDistrict || property?.district || ''}
        initialTaluk={verifTaluk || property?.taluk || ''}
        initialVillage={verifVillage || property?.locality || ''}
        initialSurvey={surveyNum}
        initialSubdivision={subdivNum}
        onSaved={() => {
          loadProperty();
        }}
      />

      {/* TNREGINET Encumbrance Certificate (EC) Search & Downloader Modal */}
      <TnecModal
        isOpen={isTnecModalOpen}
        onClose={() => setIsTnecModalOpen(false)}
        propertyId={id}
        initialDistrict={verifDistrict || property?.district || ''}
        initialTaluk={verifTaluk || property?.taluk || ''}
        initialVillage={verifVillage || property?.locality || ''}
        initialSurveyNo={surveyNum}
        initialSubdivision={subdivNum}
        onDocumentAttached={() => {
          loadDocuments();
        }}
      />

    </div>
  );
}
