import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import {
  FileText,
  Upload,
  Download,
  CheckCircle2,
  AlertTriangle,
  Archive,
  ChevronLeft,
  ChevronRight,
  Plus,
  Layers,
  List,
  FolderCheck,
  ShieldCheck,
  Building,
  User as UserIcon,
} from 'lucide-react';
import { documentsApi } from '../api/documents';
import { clientsApi } from '../api/clients';
import { propertiesApi } from '../api/properties';
import type { DocumentItem, Client, Property } from '../api/types';
import {
  VAULT_SECTIONS,
  OTHER_VAULT_SECTION,
  groupDocumentsByVaultSection,
  VaultSectionDef,
} from '../utils/vaultSections';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Section tabs & view modes
  const [activeSectionId, setActiveSectionId] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'sections' | 'table'>('sections');

  // Filters
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [propertyFilter, setPropertyFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const limit = 100; // Increased limit so sections can categorize documents properly

  // Dropdown options
  const [clients, setClients] = useState<Client[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);

  // Lookup maps for fast name resolution
  const propertyMap = useMemo(() => {
    const map = new Map<string, Property>();
    properties.forEach((p) => map.set(p.id, p));
    return map;
  }, [properties]);

  const clientMap = useMemo(() => {
    const map = new Map<string, Client>();
    clients.forEach((c) => map.set(c.id, c));
    return map;
  }, [clients]);

  // Upload Modal
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docType, setDocType] = useState('EC');
  const [propertyId, setPropertyId] = useState('');
  const [clientId, setClientId] = useState('');
  const [notes, setNotes] = useState('');
  const [uploadLoading, setUploadLoading] = useState(false);

  useEffect(() => {
    clientsApi.list({ limit: 200 }).then((res) => setClients(res.items)).catch(() => {});
    propertiesApi.list({ limit: 200 }).then((res) => setProperties(res.items)).catch(() => {});
  }, []);

  // Review Modal
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState<'PRELIMINARILY_CHECKED' | 'REQUIRES_ATTENTION'>('PRELIMINARILY_CHECKED');
  const [reviewNotes, setReviewNotes] = useState('');

  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await documentsApi.list({
        document_type: typeFilter || undefined,
        status: statusFilter || undefined,
        property_id: propertyFilter || undefined,
        limit,
        offset: page * limit,
      });
      setDocuments(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [typeFilter, statusFilter, propertyFilter, page]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Client-side text search filter
  const filteredDocuments = useMemo(() => {
    if (!searchQuery.trim()) return documents;
    const q = searchQuery.toLowerCase();
    return documents.filter((doc) => {
      const matchName = doc.original_filename.toLowerCase().includes(q);
      const matchNotes = (doc.notes || '').toLowerCase().includes(q);
      const matchType = doc.document_type.toLowerCase().includes(q);
      const prop = doc.property_id ? propertyMap.get(doc.property_id) : undefined;
      const matchProp = prop ? `${prop.title} ${prop.public_reference}`.toLowerCase().includes(q) : false;
      return matchName || matchNotes || matchType || matchProp;
    });
  }, [documents, searchQuery, propertyMap]);

  // Group documents by the 6 core Tamil Nadu vault sections
  const groupedDocs = useMemo(() => {
    return groupDocumentsByVaultSection(filteredDocuments);
  }, [filteredDocuments]);

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    setUploadLoading(true);
    try {
      await documentsApi.upload(selectedFile, docType, {
        propertyId: propertyId || undefined,
        clientId: clientId || undefined,
        notes: notes || undefined,
      });
      setIsUploadModalOpen(false);
      setSelectedFile(null);
      setNotes('');
      fetchDocuments();
      alert('Document uploaded successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploadLoading(false);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeDocId) return;
    try {
      await documentsApi.review(activeDocId, reviewStatus, reviewNotes);
      setIsReviewModalOpen(false);
      setReviewNotes('');
      setActiveDocId(null);
      fetchDocuments();
      alert('Document status updated.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Review action failed');
    }
  };

  const handleArchive = async (id: string) => {
    if (!confirm('Archive this document?')) return;
    try {
      await documentsApi.archive(id);
      fetchDocuments();
      alert('Document archived.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Archive failed');
    }
  };

  const handleDownload = async (doc: DocumentItem) => {
    try {
      await documentsApi.download(doc.id, doc.original_filename);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Download failed');
    }
  };

  // Sections to display in the pills bar
  const visibleSections = useMemo(() => {
    const list = [...VAULT_SECTIONS];
    if ((groupedDocs[OTHER_VAULT_SECTION.id] || []).length > 0 || activeSectionId === OTHER_VAULT_SECTION.id) {
      list.push(OTHER_VAULT_SECTION);
    }
    return list;
  }, [groupedDocs, activeSectionId]);

  // Determine which sections to render in split-view
  const sectionsToRender = useMemo(() => {
    if (activeSectionId === 'all') {
      return visibleSections;
    }
    const found = visibleSections.find((s) => s.id === activeSectionId);
    return found ? [found] : visibleSections;
  }, [visibleSections, activeSectionId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
              Document Repository & Legal Vault
            </h1>
            <Badge variant="outline" className="text-xs bg-amber-50 text-amber-800 border-amber-200">
              Tamil Nadu Legal Due Diligence
            </Badge>
          </div>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-1">
            Dedicated legal verification vaults for EC, Patta, A-Register, FMB, Certified Copy, and Combined Sketches
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          <div className="inline-flex rounded-md border border-[var(--color-border-ui)] bg-white p-0.5 shadow-sm">
            <button
              type="button"
              onClick={() => setViewMode('sections')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                viewMode === 'sections'
                  ? 'bg-[var(--color-forest)] text-white font-bold'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <Layers className="h-3.5 w-3.5" /> Split Sections
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                viewMode === 'table'
                  ? 'bg-[var(--color-forest)] text-white font-bold'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <List className="h-3.5 w-3.5" /> All Documents
            </button>
          </div>

          <Button onClick={() => openUploadForSection('EC')} className="shrink-0 flex items-center gap-1.5">
            <Upload className="h-4 w-4" /> Upload Document
          </Button>
        </div>
      </div>

      {/* Category Section Filter Tabs / Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[var(--color-border-ui)] text-xs scrollbar-none">
        <button
          onClick={() => setActiveSectionId('all')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
            activeSectionId === 'all'
              ? 'bg-[var(--color-forest)] text-white font-bold shadow-sm'
              : 'bg-white text-[var(--color-ink)] hover:bg-gray-100 border border-[var(--color-border-ui)]'
          }`}
        >
          <span>All Sections</span>
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${
              activeSectionId === 'all' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            {filteredDocuments.length}
          </span>
        </button>

        {visibleSections.map((section) => {
          const count = (groupedDocs[section.id] || []).length;
          const isActive = activeSectionId === section.id;
          return (
            <button
              key={section.id}
              onClick={() => setActiveSectionId(section.id)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
                isActive
                  ? 'bg-[var(--color-forest)] text-white font-bold shadow-sm'
                  : 'bg-white text-[var(--color-ink)] hover:bg-gray-100 border border-[var(--color-border-ui)]'
              }`}
            >
              <span className="font-semibold">{section.shortName}</span>
              <span
                className={`px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : count > 0
                    ? `${section.badgeBg}`
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-[8px] border border-[var(--color-border-ui)] shadow-sm">
        <div className="w-full sm:w-72">
          <Input
            placeholder="Search by filename, notes, or property..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="text-xs h-9"
          />
        </div>

        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          {/* Property Filter */}
          <Select
            value={propertyFilter}
            onChange={(e) => {
              setPropertyFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs h-9 w-full sm:w-56"
          >
            <option value="">All Properties</option>
            {properties.map((p) => (
              <option key={p.id} value={p.id}>
                {p.public_reference} - {p.title.substring(0, 24)}...
              </option>
            ))}
          </Select>

          {/* Status Filter */}
          <Select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs h-9 w-full sm:w-44"
          >
            <option value="">All Verification Statuses</option>
            <option value="UPLOADED">Uploaded</option>
            <option value="PRELIMINARILY_CHECKED">Preliminarily Checked</option>
            <option value="REQUIRES_ATTENTION">Requires Attention</option>
            <option value="ARCHIVED">Archived</option>
          </Select>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading document repository...
        </div>
      ) : filteredDocuments.length === 0 && searchQuery ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <FileText className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No matching documents found</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Try refining your search query or filters.</p>
          <Button size="sm" variant="outline" onClick={() => setSearchQuery('')} className="mt-3">
            Clear Search
          </Button>
        </div>
      ) : viewMode === 'sections' ? (
        /* Split Sections View */
        <div className="space-y-6">
          {sectionsToRender.map((section) => {
            const sectionDocs = groupedDocs[section.id] || [];
            return (
              <div
                key={section.id}
                className="bg-white rounded-[10px] border border-[var(--color-border-ui)] shadow-sm overflow-hidden"
              >
                {/* Section Header Banner */}
                <div
                  className={`p-4 border-b ${section.borderColor} ${section.bgColor} flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3`}
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-white shadow-xs border border-gray-100 shrink-0">
                      <FolderCheck className={`h-5 w-5 ${section.color}`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold tracking-wide ${section.badgeBg}`}>
                          {section.shortName}
                        </span>
                        <h2 className="text-base font-serif font-bold text-[var(--color-ink)]">
                          {section.name}
                        </h2>
                      </div>
                      <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
                        {section.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    <span className="text-xs font-semibold px-2 py-1 rounded bg-white/80 border border-gray-200 text-gray-700">
                      {sectionDocs.length} {sectionDocs.length === 1 ? 'file' : 'files'}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openUploadForSection(section.defaultDocType)}
                      className="text-xs h-8 flex items-center gap-1.5 bg-white hover:bg-gray-50 border-gray-300"
                    >
                      <Plus className="h-3.5 w-3.5" /> Upload {section.shortName}
                    </Button>
                  </div>
                </div>

                {/* Section Content */}
                {sectionDocs.length === 0 ? (
                  <div className="p-8 text-center bg-gray-50/40">
                    <p className="text-xs font-semibold text-gray-700">
                      No {section.name} uploaded yet
                    </p>
                    <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
                      Upload the official {section.shortName} record to complete legal due diligence for registered properties.
                    </p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => openUploadForSection(section.defaultDocType)}
                      className="mt-3 text-xs"
                    >
                      <Plus className="h-3 w-3 mr-1" /> Add {section.shortName} Document
                    </Button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="bg-gray-50/75">
                          <TableHead className="w-[30%]">Document / File</TableHead>
                          <TableHead className="w-[20%]">Linked Property</TableHead>
                          <TableHead className="w-[15%]">Linked Client</TableHead>
                          <TableHead className="w-[10%]">File Size</TableHead>
                          <TableHead className="w-[10%]">Status</TableHead>
                          <TableHead className="w-[15%] text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {sectionDocs.map((doc) => {
                          const prop = doc.property_id ? propertyMap.get(doc.property_id) : undefined;
                          const client = doc.client_id ? clientMap.get(doc.client_id) : undefined;
                          return (
                            <TableRow
                              key={doc.id}
                              className="hover:bg-[var(--color-parchment-warm)] transition-colors"
                            >
                              <TableCell className="font-semibold text-xs text-[var(--color-ink)]">
                                <div className="flex items-start space-x-2">
                                  <div className="p-1.5 rounded bg-gray-100 text-gray-600 mt-0.5 shrink-0">
                                    <FileText className="h-4 w-4" />
                                  </div>
                                  <div className="min-w-0">
                                    <span className="truncate block max-w-[240px] font-medium text-gray-900" title={doc.original_filename}>
                                      {doc.original_filename}
                                    </span>
                                    {doc.notes && (
                                      <span className="text-[11px] text-gray-500 block truncate max-w-[240px] mt-0.5">
                                        Ref: {doc.notes}
                                      </span>
                                    )}
                                    <span className="text-[10px] text-gray-400 block mt-0.5">
                                      Uploaded {new Date(doc.created_at).toLocaleDateString()}
                                    </span>
                                  </div>
                                </div>
                              </TableCell>

                              <TableCell className="text-xs">
                                {prop ? (
                                  <div className="flex items-center gap-1.5">
                                    <Building className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                                    <span className="truncate max-w-[160px] font-medium text-gray-800" title={prop.title}>
                                      <span className="text-[10px] font-mono text-gray-500 mr-1">
                                        {prop.public_reference}
                                      </span>
                                      {prop.title}
                                    </span>
                                  </div>
                                ) : (
                                  <span className="text-gray-400 text-[11px] italic">General / Unlinked</span>
                                )}
                              </TableCell>

                              <TableCell className="text-xs">
                                {client ? (
                                  <div className="flex items-center gap-1.5">
                                    <UserIcon className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                                    <span className="truncate max-w-[130px] text-gray-700" title={client.full_name}>
                                      {client.full_name}
                                    </span>
                                  </div>
                                ) : (
                                  <span className="text-gray-400 text-[11px]">-</span>
                                )}
                              </TableCell>

                              <TableCell className="text-xs text-gray-500">
                                {(doc.file_size / 1024).toFixed(1)} KB
                              </TableCell>

                              <TableCell>
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
                                  {doc.status === 'PRELIMINARILY_CHECKED'
                                    ? 'CHECKED'
                                    : doc.status === 'REQUIRES_ATTENTION'
                                    ? 'FLAGGED'
                                    : 'UPLOADED'}
                                </Badge>
                              </TableCell>

                              <TableCell className="text-right whitespace-nowrap">
                                <div className="flex items-center justify-end gap-1.5">
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleDownload(doc)}
                                    className="text-[11px] h-7 px-2 flex items-center gap-1"
                                    title="Download file stream"
                                  >
                                    <Download className="h-3 w-3" /> Download
                                  </Button>

                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => {
                                      setActiveDocId(doc.id);
                                      setIsReviewModalOpen(true);
                                    }}
                                    className="text-[11px] h-7 px-2 text-gray-700 hover:bg-gray-100"
                                    title="Review status"
                                  >
                                    Review
                                  </Button>

                                  {!doc.is_archived && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => handleArchive(doc.id)}
                                      className="text-[11px] h-7 px-1.5 text-red-600 hover:bg-red-50"
                                      title="Archive"
                                    >
                                      <Archive className="h-3.5 w-3.5" />
                                    </Button>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* Flat Table View */
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Filename / File</TableHead>
                <TableHead>Section Category</TableHead>
                <TableHead>Linked Property</TableHead>
                <TableHead>File Size</TableHead>
                <TableHead>Verification Status</TableHead>
                <TableHead>Notes / Ref</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredDocuments.map((doc) => {
                const prop = doc.property_id ? propertyMap.get(doc.property_id) : undefined;
                return (
                  <TableRow key={doc.id} className="hover:bg-[var(--color-parchment-warm)] transition-colors">
                    <TableCell className="font-semibold text-xs text-[var(--color-ink)]">
                      <div className="flex items-center space-x-2">
                        <div className="p-1.5 rounded bg-gray-100 text-gray-600 shrink-0">
                          <FileText className="h-4 w-4" />
                        </div>
                        <span className="truncate max-w-[200px]">{doc.original_filename}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] font-mono">
                        {doc.document_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      {prop ? (
                        <span className="font-mono text-gray-700">{prop.public_reference}</span>
                      ) : (
                        <span className="text-gray-400 italic text-[11px]">Unlinked</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-gray-500">
                      {(doc.file_size / 1024).toFixed(1)} KB
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          doc.status === 'PRELIMINARILY_CHECKED'
                            ? 'success'
                            : doc.status === 'REQUIRES_ATTENTION'
                            ? 'danger'
                            : 'warning'
                        }
                      >
                        {doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-gray-500 max-w-[180px] truncate">
                      {doc.notes || '-'}
                    </TableCell>
                    <TableCell className="text-xs text-gray-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDownload(doc)}
                          className="text-[11px] h-7 px-2 flex items-center gap-1"
                          title="Download file stream"
                        >
                          <Download className="h-3 w-3" /> Download
                        </Button>

                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setActiveDocId(doc.id);
                            setIsReviewModalOpen(true);
                          }}
                          className="text-[11px] h-7 px-2 text-gray-700"
                          title="Review status"
                        >
                          Review
                        </Button>

                        {!doc.is_archived && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleArchive(doc.id)}
                            className="text-[11px] h-7 px-1.5 text-red-600 hover:bg-red-50"
                            title="Archive"
                          >
                            <Archive className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination Footer */}
      {total > limit && (
        <div className="flex items-center justify-between border-t border-[var(--color-border-ui)] pt-4 text-xs">
          <span className="text-[var(--color-ink-muted)]">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} documents
          </span>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="text-xs"
            >
              <ChevronLeft className="h-3 w-3 mr-1" /> Previous
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage((p) => p + 1)}
              className="text-xs"
            >
              Next <ChevronRight className="h-3 w-3 ml-1" />
            </Button>
          </div>
        </div>
      )}

      {/* MODAL: UPLOAD DOCUMENT */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title="Upload Document into Secure Storage"
        description="Upload PDF or image files with MIME and binary integrity validation."
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Document Category / Section
            </label>
            <Select value={docType} onChange={(e) => setDocType(e.target.value)}>
              <optgroup label="Core Tamil Nadu Land & Legal Vault Sections">
                <option value="EC">EC - ENCUMBRANCE CERTIFICATE</option>
                <option value="PATTA">PATTA - PATTA / CHITTA / TSLR</option>
                <option value="A_REGISTER">A-REGISTER - SETTLEMENT EXTRACT</option>
                <option value="FMB">FMB - FIELD MEASUREMENT BOOK</option>
                <option value="CERTIFIED_COPY">CERTIFIED COPY - SRO TITLE DEED</option>
                <option value="COMBINED_SKETCH">COMBINED SKETCH - TOWN / SURVEY SKETCH</option>
              </optgroup>
              <optgroup label="Other Legal & Regulatory Records">
                <option value="SALE_DEED">SALE DEED (ORIGINAL / COPY)</option>
                <option value="PARENT_DOCUMENT">PARENT / LINK DEED</option>
                <option value="CMDA_APPROVAL">CMDA PLANNING APPROVAL</option>
                <option value="DTCP_APPROVAL">DTCP LAYOUT APPROVAL</option>
                <option value="TNRERA_REGISTRATION">TNRERA REGISTRATION</option>
                <option value="PROPERTY_TAX_DOCUMENT">PROPERTY TAX DOCUMENT</option>
                <option value="OTHER">OTHER / MISCELLANEOUS</option>
              </optgroup>
            </Select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">File Picker (.pdf, .jpg, .png)</label>
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Link to Property (Optional)</label>
              {properties.length > 0 ? (
                <Select
                  value={propertyId}
                  onChange={(e) => setPropertyId(e.target.value)}
                >
                  <option value="">None / Unlinked</option>
                  {properties.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.public_reference} - {p.title}
                    </option>
                  ))}
                </Select>
              ) : (
                <Input
                  placeholder="Property UUID (optional)"
                  value={propertyId}
                  onChange={(e) => setPropertyId(e.target.value)}
                />
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Link to Client (Optional)</label>
              {clients.length > 0 ? (
                <Select
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                >
                  <option value="">None / Unlinked</option>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.full_name} ({c.phone || 'No phone'})
                    </option>
                  ))}
                </Select>
              ) : (
                <Input
                  placeholder="Client UUID (optional)"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                />
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Registration Reference / Notes</label>
            <Input
              placeholder="e.g. SRO T.Nagar Doc 3412/2021 or Patta No. 1204"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsUploadModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={uploadLoading} disabled={!selectedFile}>
              Upload File
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: REVIEW STATUS */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        title="Review Document Integrity"
        description="Verify or flag documentary evidence."
      >
        <form onSubmit={handleReviewSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Verification Status</label>
            <Select
              value={reviewStatus}
              onChange={(e) => setReviewStatus(e.target.value as any)}
            >
              <option value="PRELIMINARILY_CHECKED">PRELIMINARILY CHECKED (PASS)</option>
              <option value="REQUIRES_ATTENTION">REQUIRES ATTENTION (FLAG)</option>
            </Select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Reviewer Observations</label>
            <Input
              placeholder="e.g. Survey number 142/2B confirmed against revenue Patta"
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsReviewModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">
              Save Review Decision
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
