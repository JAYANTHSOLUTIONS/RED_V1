import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Search, Plus, Target, ChevronLeft, ChevronRight } from 'lucide-react';
import { leadsApi } from '../api/leads';
import { clientsApi } from '../api/clients';
import { propertiesApi } from '../api/properties';
import type { Lead, LeadCreatePayload, Client, Property } from '../api/types';

export default function LeadsPage() {
  const navigate = useNavigate();

  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Dropdown options
  const [clients, setClients] = useState<Client[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);

  // Create Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newLead, setNewLead] = useState<LeadCreatePayload>({
    client_id: '',
    property_id: '',
    source: 'WEBSITE',
    notes: '',
  });

  useEffect(() => {
    clientsApi.list({ limit: 100 }).then((res) => {
      setClients(res.items);
      if (res.items.length > 0) {
        setNewLead((prev) => (prev.client_id ? prev : { ...prev, client_id: res.items[0].id }));
      }
    }).catch(() => {});

    propertiesApi.list({ limit: 100 }).then((res) => {
      setProperties(res.items);
    }).catch(() => {});
  }, []);

  const fetchLeads = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await leadsApi.list({
        search: search || undefined,
        status: statusFilter || undefined,
        source: sourceFilter || undefined,
        limit,
        offset: page * limit,
      });
      setLeads(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter, sourceFilter, page]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchLeads();
  };

  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const created = await leadsApi.create({
        ...newLead,
        property_id: newLead.property_id || undefined,
      });
      setIsModalOpen(false);
      navigate(`/leads/${created.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to register lead');
    } finally {
      setCreateLoading(false);
    }
  };

  const stages = [
    { label: 'All Stages', value: '' },
    { label: 'New', value: 'NEW' },
    { label: 'Contacted', value: 'CONTACTED' },
    { label: 'Interested', value: 'INTERESTED' },
    { label: 'Site Visit', value: 'SITE_VISIT' },
    { label: 'Negotiation', value: 'NEGOTIATION' },
    { label: 'Converted', value: 'CONVERTED' },
    { label: 'Lost', value: 'LOST' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Sales Pipeline Leads
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Track inquiries, lifecycle transitions, and client-property matchmaking
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="shrink-0 flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Create Sales Lead
        </Button>
      </div>

      {/* Stage Tabs */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border-ui)] overflow-x-auto pb-1 text-xs">
        {stages.map((st) => (
          <button
            key={st.value}
            onClick={() => {
              setStatusFilter(st.value);
              setPage(0);
            }}
            className={`px-3 py-2 font-medium rounded-t-md transition-colors whitespace-nowrap ${
              statusFilter === st.value
                ? 'border-b-2 border-[var(--color-gold)] text-[var(--color-forest)] font-bold bg-amber-50/50'
                : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
            }`}
          >
            {st.label}
          </button>
        ))}
      </div>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-[8px] border border-[var(--color-border-ui)] shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex flex-1 items-center space-x-2 w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-ink-muted)]" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by notes, lost reason... (Press Enter)"
              className="pl-9 text-xs h-9"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm" className="shrink-0 text-xs">
            Search
          </Button>
        </form>

        <div className="w-full sm:w-auto">
          <Select
            value={sourceFilter}
            onChange={(e) => {
              setSourceFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs h-9 w-full sm:w-44"
          >
            <option value="">All Sources</option>
            <option value="DIRECT_CALL">Direct Phone Call</option>
            <option value="WHATSAPP">WhatsApp Inquiry</option>
            <option value="WEBSITE">Website Form</option>
            <option value="REFERRAL">Referral</option>
            <option value="WALK_IN">Walk-in</option>
          </Select>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading sales leads...
        </div>
      ) : leads.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <Target className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No leads found</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Create a sales lead to manage inquiries.</p>
          <Button size="sm" onClick={() => setIsModalOpen(true)} className="mt-4">
            Create Lead
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead>Target Property</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Pipeline Stage</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {leads.map((lead) => (
                <TableRow
                  key={lead.id}
                  onClick={() => navigate(`/leads/${lead.id}`)}
                  className="cursor-pointer hover:bg-[var(--color-parchment-warm)] transition-colors"
                >
                  <TableCell className="font-semibold text-xs text-[var(--color-ink)]">
                    <div>
                      <span className="text-gray-900 font-bold">{lead.client?.full_name || 'Client Record'}</span>
                      <span className="block text-[10px] text-gray-400 font-normal">{lead.client?.phone || 'No phone'}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">
                    {lead.property ? (
                      <div>
                        <span className="font-semibold text-gray-900">{lead.property.title}</span>
                        <span className="block font-mono text-[10px] text-gray-400">{lead.property.public_reference}</span>
                      </div>
                    ) : (
                      <span className="text-gray-400 italic">General Inquiry</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">{lead.source}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        lead.status === 'CONVERTED'
                          ? 'success'
                          : lead.status === 'NEW'
                          ? 'info'
                          : lead.status === 'LOST'
                          ? 'danger'
                          : 'warning'
                      }
                    >
                      {lead.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-gray-500 max-w-[200px] truncate">
                    {lead.notes || (lead.lost_reason ? `Reason: ${lead.lost_reason}` : '-')}
                  </TableCell>
                  <TableCell className="text-xs text-gray-400">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Pagination Footer */}
      {total > limit && (
        <div className="flex items-center justify-between border-t border-[var(--color-border-ui)] pt-4 text-xs">
          <span className="text-[var(--color-ink-muted)]">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} leads
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

      {/* MODAL: CREATE LEAD */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register Sales Pipeline Lead"
        description="Attach lead to a client and optional target property."
      >
        <form onSubmit={handleCreateLead} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Select Client <span className="text-red-500">*</span>
            </label>
            {clients.length > 0 ? (
              <Select
                required
                value={newLead.client_id}
                onChange={(e) => setNewLead({ ...newLead, client_id: e.target.value })}
              >
                <option value="">Select a Client ({clients.length} Registered)</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} ({c.phone || c.email || 'No contact info'})
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                required
                placeholder="e.g. 11111111-..."
                value={newLead.client_id}
                onChange={(e) => setNewLead({ ...newLead, client_id: e.target.value })}
              />
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Target Property (Optional)</label>
            {properties.length > 0 ? (
              <Select
                value={newLead.property_id || ''}
                onChange={(e) => setNewLead({ ...newLead, property_id: e.target.value })}
              >
                <option value="">None / General Inquiry</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.public_reference} - {p.title} ({p.locality}, {p.district})
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                placeholder="e.g. 22222222-..."
                value={newLead.property_id || ''}
                onChange={(e) => setNewLead({ ...newLead, property_id: e.target.value })}
              />
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Lead Source</label>
            <Select
              value={newLead.source}
              onChange={(e) => setNewLead({ ...newLead, source: e.target.value })}
            >
              <option value="WEBSITE">Website Form</option>
              <option value="DIRECT_CALL">Direct Phone Call</option>
              <option value="WHATSAPP">WhatsApp Inquiry</option>
              <option value="REFERRAL">Referral</option>
              <option value="WALK_IN">Office Walk-in</option>
            </Select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Initial Notes</label>
            <Input
              placeholder="e.g. Buyer interested in immediate purchase"
              value={newLead.notes || ''}
              onChange={(e) => setNewLead({ ...newLead, notes: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createLoading}>
              Register Lead
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
