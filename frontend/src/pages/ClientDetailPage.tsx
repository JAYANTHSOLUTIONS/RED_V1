import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import {
  ChevronLeft,
  Phone,
  Mail,
  Edit,
  Archive,
  Plus,
  Target,
  FileCheck,
  Calendar,
  MessageSquare,
} from 'lucide-react';
import { clientsApi, leadsApi, requirementsApi, notificationsApi } from '../api';
import type { ClientWithLeads, PropertyRequirementCreatePayload } from '../api/types';

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [client, setClient] = useState<ClientWithLeads | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isLeadModalOpen, setIsLeadModalOpen] = useState(false);
  const [isReqModalOpen, setIsReqModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Forms
  const [editForm, setEditForm] = useState({
    full_name: '',
    phone: '',
    email: '',
    classification: 'BUYER',
    preferred_contact_method: 'CALL',
    notes: '',
  });

  const [newLeadSource, setNewLeadSource] = useState('DIRECT_CALL');
  const [newLeadNotes, setNewLeadNotes] = useState('');

  const [newReq, setNewReq] = useState<Omit<PropertyRequirementCreatePayload, 'client_id'>>({
    transaction_type: 'BUY',
    property_types: 'Apartment',
    target_locations: 'Chennai',
    min_budget: 5000000,
    max_budget: 15000000,
    area_unit: 'sq.ft',
    bedrooms: 3,
  });

  const loadClient = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await clientsApi.get(id);
      setClient(data);
      setEditForm({
        full_name: data.full_name,
        phone: data.phone,
        email: data.email || '',
        classification: data.classification,
        preferred_contact_method: data.preferred_contact_method,
        notes: data.notes || '',
      });
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadClient();
  }, [loadClient]);

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setActionLoading(true);
    try {
      const updated = await clientsApi.update(id, editForm as any);
      setClient(updated);
      setIsEditModalOpen(false);
      alert('Client details updated.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleArchive = async () => {
    if (!id) return;
    if (!confirm('Archive this client profile?')) return;
    try {
      const updated = await clientsApi.archive(id);
      setClient(updated);
      alert('Client profile archived.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Archive failed');
    }
  };

  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setActionLoading(true);
    try {
      await leadsApi.create({
        client_id: id,
        source: newLeadSource,
        notes: newLeadNotes,
      });
      setIsLeadModalOpen(false);
      setNewLeadNotes('');
      loadClient();
      alert('Sales lead created.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create lead');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setActionLoading(true);
    try {
      await requirementsApi.create({
        ...newReq,
        client_id: id,
      });
      setIsReqModalOpen(false);
      alert('Property requirement recorded.');
      navigate('/requirements');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create requirement');
    } finally {
      setActionLoading(false);
    }
  };

  const handleWhatsApp = async () => {
    if (!client) return;
    try {
      const link = await notificationsApi.generateWhatsAppLink({
        phone: client.phone,
        message: `Hello ${client.full_name}, greeting from RED Tamil Nadu Real Estate Consultancy.`,
      });
      window.open(link.whatsapp_url, '_blank');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'WhatsApp link generation failed');
    }
  };

  if (isLoading) {
    return <div className="p-12 text-center text-xs text-gray-500">Loading client profile...</div>;
  }

  if (!client) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm font-semibold text-gray-900">Client profile not found</p>
        <Link to="/clients" className="text-xs text-[var(--color-primary)] hover:underline mt-2 inline-block">
          Return to clients
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--color-border-ui)] pb-4">
        <div className="flex items-center space-x-2">
          <Link
            to="/clients"
            className="inline-flex items-center text-xs font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-ink)]"
          >
            <ChevronLeft className="mr-1 h-4 w-4" /> Clients
          </Link>
          <span className="text-gray-300">/</span>
          <span className="text-xs font-bold text-[var(--color-ink)]">{client.full_name}</span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleWhatsApp}
            className="text-xs text-emerald-700 hover:bg-emerald-50 border-emerald-300 flex items-center gap-1"
          >
            <MessageSquare className="h-3.5 w-3.5" /> WhatsApp Message
          </Button>

          <Button size="sm" variant="secondary" onClick={() => setIsEditModalOpen(true)} className="text-xs flex items-center gap-1">
            <Edit className="h-3.5 w-3.5" /> Edit Profile
          </Button>

          {!client.is_archived && (
            <Button size="sm" variant="ghost" onClick={handleArchive} className="text-xs text-red-600 hover:bg-red-50">
              <Archive className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Hero Card */}
      <div className="bg-white rounded-lg border border-[var(--color-border-ui)] p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="h-14 w-14 rounded-full bg-[var(--color-forest)] text-white flex items-center justify-center font-bold text-xl">
              {client.full_name.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-serif text-2xl font-bold text-[var(--color-ink)]">{client.full_name}</h1>
                <Badge variant={client.is_archived ? 'secondary' : 'success'}>
                  {client.is_archived ? 'ARCHIVED' : client.status}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 mt-1">
                <span className="flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5 text-gray-400" />
                  {client.phone}
                </span>
                {client.email && (
                  <span className="flex items-center gap-1">
                    <Mail className="h-3.5 w-3.5 text-gray-400" />
                    {client.email}
                  </span>
                )}
                <Badge variant="outline" className="text-[10px]">{client.classification}</Badge>
                <Badge variant="neutral" className="text-[10px]">Prefers: {client.preferred_contact_method}</Badge>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setIsLeadModalOpen(true)} className="text-xs flex items-center gap-1">
              <Plus className="h-3.5 w-3.5" /> Add Sales Lead
            </Button>
            <Button size="sm" variant="outline" onClick={() => setIsReqModalOpen(true)} className="text-xs flex items-center gap-1">
              <Plus className="h-3.5 w-3.5" /> Add Requirement
            </Button>
          </div>
        </div>

        {client.notes && (
          <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200 text-xs text-gray-700">
            <strong className="block text-[11px] uppercase tracking-wider text-gray-400 mb-0.5">Consultant Notes:</strong>
            {client.notes}
          </div>
        )}
      </div>

      {/* Associated Leads Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-gray-700 flex items-center gap-2">
            <Target className="h-4 w-4 text-[var(--color-forest)]" />
            Associated Sales Pipeline Leads ({client.leads?.length || 0})
          </h2>
          <Button size="sm" variant="outline" onClick={() => setIsLeadModalOpen(true)} className="text-xs">
            <Plus className="h-3 w-3 mr-1" /> New Lead
          </Button>
        </div>

        {client.leads && client.leads.length > 0 ? (
          <div className="bg-white rounded-lg border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
            <div className="divide-y divide-gray-100 text-xs">
              {client.leads.map((lead) => (
                <div
                  key={lead.id}
                  onClick={() => navigate(`/leads/${lead.id}`)}
                  className="p-4 flex items-center justify-between hover:bg-[var(--color-parchment-warm)] cursor-pointer transition-colors"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-gray-900">Lead #{lead.id.slice(0, 8)}</span>
                      <Badge
                        variant={
                          lead.status === 'CONVERTED'
                            ? 'success'
                            : lead.status === 'LOST'
                            ? 'danger'
                            : 'warning'
                        }
                      >
                        {lead.status}
                      </Badge>
                      <span className="text-gray-400">• Source: {lead.source}</span>
                    </div>
                    {lead.property && (
                      <p className="text-gray-600 mt-1">
                        Inquiring for: <span className="font-semibold text-gray-900">{lead.property.title}</span> ({lead.property.public_reference})
                      </p>
                    )}
                    {lead.notes && <p className="text-gray-400 text-[11px] mt-0.5">{lead.notes}</p>}
                  </div>

                  <span className="text-[11px] text-[var(--color-primary)] font-medium">Manage Lead &rarr;</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="bg-white p-8 text-center rounded-lg border border-[var(--color-border-ui)] text-xs text-gray-500">
            No active sales leads for this client.
          </div>
        )}
      </div>

      {/* MODAL: EDIT CLIENT */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Edit Client Profile"
        description="Update contact information and preferences."
      >
        <form onSubmit={handleEditSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Full Legal Name</label>
            <Input
              required
              value={editForm.full_name}
              onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Phone</label>
              <Input
                required
                value={editForm.phone}
                onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Email</label>
              <Input
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Classification</label>
              <Select
                value={editForm.classification}
                onChange={(e) => setEditForm({ ...editForm, classification: e.target.value })}
              >
                <option value="BUYER">BUYER</option>
                <option value="SELLER">SELLER</option>
                <option value="TENANT">TENANT</option>
                <option value="LANDLORD">LANDLORD</option>
                <option value="INVESTOR">INVESTOR</option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Contact Method</label>
              <Select
                value={editForm.preferred_contact_method}
                onChange={(e) => setEditForm({ ...editForm, preferred_contact_method: e.target.value })}
              >
                <option value="CALL">CALL</option>
                <option value="WHATSAPP">WHATSAPP</option>
                <option value="EMAIL">EMAIL</option>
              </Select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Notes</label>
            <Input
              value={editForm.notes}
              onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
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

      {/* MODAL: ADD SALES LEAD */}
      <Modal
        isOpen={isLeadModalOpen}
        onClose={() => setIsLeadModalOpen(false)}
        title="Create Sales Pipeline Lead"
        description="Creates a new lead for this client in NEW status."
      >
        <form onSubmit={handleCreateLead} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Lead Source</label>
            <Select value={newLeadSource} onChange={(e) => setNewLeadSource(e.target.value)}>
              <option value="DIRECT_CALL">Direct Phone Call</option>
              <option value="WHATSAPP">WhatsApp Inquiry</option>
              <option value="WEBSITE">Website Form</option>
              <option value="REFERRAL">Referral</option>
              <option value="WALK_IN">Office Walk-in</option>
            </Select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Inquiry Details / Notes</label>
            <Input
              placeholder="e.g. Inquiring about 3 BHK in Velachery or Madipakkam"
              value={newLeadNotes}
              onChange={(e) => setNewLeadNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsLeadModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Create Lead
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: ADD REQUIREMENT */}
      <Modal
        isOpen={isReqModalOpen}
        onClose={() => setIsReqModalOpen(false)}
        title="Record Property Requirement"
        description="Specify buyer/tenant parameters for automated property matching."
      >
        <form onSubmit={handleCreateRequirement} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Transaction</label>
              <Select
                value={newReq.transaction_type}
                onChange={(e) => setNewReq({ ...newReq, transaction_type: e.target.value as any })}
              >
                <option value="BUY">BUY</option>
                <option value="RENT">RENT</option>
                <option value="LEASE">LEASE</option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Property Type</label>
              <Input
                placeholder="Apartment, Villa"
                value={newReq.property_types || ''}
                onChange={(e) => setNewReq({ ...newReq, property_types: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Min Budget (₹)</label>
              <Input
                type="number"
                value={newReq.min_budget || 0}
                onChange={(e) => setNewReq({ ...newReq, min_budget: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Max Budget (₹)</label>
              <Input
                type="number"
                value={newReq.max_budget || 0}
                onChange={(e) => setNewReq({ ...newReq, max_budget: Number(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Target Localities</label>
            <Input
              placeholder="e.g. Adyar, Thiruvanmiyur, Besant Nagar"
              value={newReq.target_locations || ''}
              onChange={(e) => setNewReq({ ...newReq, target_locations: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsReqModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Save Requirement
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
