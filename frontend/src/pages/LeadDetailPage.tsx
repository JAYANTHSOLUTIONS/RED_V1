import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import {
  ChevronLeft,
  Phone,
  Mail,
  Building,
  Target,
  CheckCircle,
  XCircle,
  ArrowRight,
  MessageSquare,
  Calendar,
  Clock,
} from 'lucide-react';
import { leadsApi, siteVisitsApi, notificationsApi } from '../api';
import type { Lead } from '../api/types';

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [lead, setLead] = useState<Lead | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isLostModalOpen, setIsLostModalOpen] = useState(false);
  const [lostReason, setLostReason] = useState('');
  const [isVisitModalOpen, setIsVisitModalOpen] = useState(false);
  const [visitDate, setVisitDate] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
  const [visitNotes, setVisitNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const loadLead = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await leadsApi.get(id);
      setLead(data);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadLead();
  }, [loadLead]);

  // Stage Transitions
  const handleContact = async () => {
    if (!id) return;
    try {
      const updated = await leadsApi.contact(id);
      setLead(updated);
      alert('Lead moved to CONTACTED stage.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Transition failed');
    }
  };

  const handleMarkInterested = async () => {
    if (!id) return;
    try {
      const updated = await leadsApi.markInterested(id);
      setLead(updated);
      alert('Lead moved to INTERESTED stage.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Transition failed');
    }
  };

  const handleSiteVisitStage = async () => {
    if (!id) return;
    try {
      const updated = await leadsApi.scheduleSiteVisitStage(id);
      setLead(updated);
      alert('Lead moved to SITE_VISIT stage.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Transition failed');
    }
  };

  const handleNegotiation = async () => {
    if (!id) return;
    try {
      const updated = await leadsApi.moveToNegotiation(id);
      setLead(updated);
      alert('Lead moved to NEGOTIATION stage.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Transition failed');
    }
  };

  const handleConvert = async () => {
    if (!id) return;
    if (!confirm('Mark this lead as CONVERTED deal? This is a terminal success state.')) return;
    try {
      const updated = await leadsApi.convert(id);
      setLead(updated);
      alert('Congratulations! Lead marked as CONVERTED.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Conversion failed');
    }
  };

  const handleMarkLost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !lostReason.trim()) return;
    setActionLoading(true);
    try {
      const updated = await leadsApi.markLost(id, lostReason.trim());
      setLead(updated);
      setIsLostModalOpen(false);
      setLostReason('');
      alert('Lead marked as LOST.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleBookVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lead || !lead.property_id) {
      alert('This lead must be linked to a specific property to schedule a visit.');
      return;
    }
    setActionLoading(true);
    try {
      await siteVisitsApi.create({
        client_id: lead.client_id,
        property_id: lead.property_id,
        lead_id: lead.id,
        scheduled_at: new Date(visitDate).toISOString(),
        status: 'CONFIRMED',
        notes: visitNotes,
      });
      setIsVisitModalOpen(false);
      alert('Site visit booked successfully.');
      navigate('/site-visits');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Booking failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleWhatsApp = async () => {
    if (!lead?.client?.phone) return;
    try {
      const link = await notificationsApi.generateWhatsAppLink({
        phone: lead.client.phone,
        message: `Hello ${lead.client.full_name}, regarding your real estate inquiry with RED Consultancy:`,
      });
      window.open(link.whatsapp_url, '_blank');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'WhatsApp link failed');
    }
  };

  if (isLoading) {
    return <div className="p-12 text-center text-xs text-gray-500">Loading sales lead...</div>;
  }

  if (!lead) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm font-semibold text-gray-900">Lead record not found</p>
        <Link to="/leads" className="text-xs text-[var(--color-primary)] hover:underline mt-2 inline-block">
          Return to leads
        </Link>
      </div>
    );
  }

  const isTerminal = lead.status === 'CONVERTED' || lead.status === 'LOST';

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--color-border-ui)] pb-4">
        <div className="flex items-center space-x-2">
          <Link
            to="/leads"
            className="inline-flex items-center text-xs font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-ink)]"
          >
            <ChevronLeft className="mr-1 h-4 w-4" /> Leads
          </Link>
          <span className="text-gray-300">/</span>
          <span className="font-mono text-xs font-bold text-[var(--color-ink)]">LEAD-{lead.id.slice(0, 8)}</span>
        </div>

        <div className="flex items-center gap-2">
          {lead.client?.phone && (
            <Button
              size="sm"
              variant="outline"
              onClick={handleWhatsApp}
              className="text-xs text-emerald-700 hover:bg-emerald-50 border-emerald-300 flex items-center gap-1"
            >
              <MessageSquare className="h-3.5 w-3.5" /> WhatsApp
            </Button>
          )}

          {lead.property_id && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setIsVisitModalOpen(true)}
              className="text-xs flex items-center gap-1"
            >
              <Calendar className="h-3.5 w-3.5" /> Book Inspection
            </Button>
          )}
        </div>
      </div>

      {/* Hero Header */}
      <div className="bg-white rounded-lg border border-[var(--color-border-ui)] p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif text-2xl font-bold text-[var(--color-ink)]">
                Sales Inquiry #{lead.id.slice(0, 8)}
              </span>
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
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500 mt-1">
              <span>Source: <strong className="text-gray-900">{lead.source}</strong></span>
              <span>• Registered on: {new Date(lead.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Lifecycle Action Progression Buttons */}
          {!isTerminal && (
            <div className="flex flex-wrap items-center gap-2">
              {lead.status === 'NEW' && (
                <Button size="sm" onClick={handleContact} className="text-xs">
                  Mark Contacted &rarr;
                </Button>
              )}

              {lead.status === 'CONTACTED' && (
                <Button size="sm" onClick={handleMarkInterested} className="text-xs">
                  Mark Interested &rarr;
                </Button>
              )}

              {lead.status === 'INTERESTED' && (
                <Button size="sm" onClick={handleSiteVisitStage} className="text-xs">
                  Move to Site Visit Stage &rarr;
                </Button>
              )}

              {lead.status === 'SITE_VISIT' && (
                <Button size="sm" onClick={handleNegotiation} className="text-xs">
                  Move to Negotiation &rarr;
                </Button>
              )}

              {lead.status === 'NEGOTIATION' && (
                <Button size="sm" onClick={handleConvert} className="text-xs bg-emerald-700 hover:bg-emerald-800 text-white flex items-center gap-1">
                  <CheckCircle className="h-3.5 w-3.5" /> Convert Deal
                </Button>
              )}

              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsLostModalOpen(true)}
                className="text-xs text-red-600 hover:bg-red-50 border-red-200 flex items-center gap-1"
              >
                <XCircle className="h-3.5 w-3.5" /> Mark Lost
              </Button>
            </div>
          )}
        </div>

        {lead.status === 'LOST' && lead.lost_reason && (
          <div className="mt-4 p-3 bg-red-50 rounded border border-red-200 text-xs text-red-800">
            <strong>Lost Reason:</strong> {lead.lost_reason}
          </div>
        )}
      </div>

      {/* Grid: Client info & Property info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Client Card */}
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs uppercase tracking-wider text-[var(--color-ink-muted)]">
              Client Profile
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {lead.client ? (
              <>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Full Name</span>
                  <Link to={`/clients/${lead.client.id}`} className="font-semibold text-[var(--color-forest)] hover:underline">
                    {lead.client.full_name}
                  </Link>
                </div>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Phone</span>
                  <span className="font-mono text-gray-900">{lead.client.phone}</span>
                </div>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Classification</span>
                  <Badge variant="outline" className="text-[10px]">{lead.client.classification}</Badge>
                </div>
                <div className="pt-2">
                  <Link to={`/clients/${lead.client.id}`}>
                    <Button variant="secondary" size="sm" className="w-full text-xs">
                      View Client Dossier
                    </Button>
                  </Link>
                </div>
              </>
            ) : (
              <p className="text-gray-400">Client ID: {lead.client_id}</p>
            )}
          </CardContent>
        </Card>

        {/* Property Card */}
        <Card>
          <CardHeader className="py-3 px-4">
            <CardTitle className="text-xs uppercase tracking-wider text-[var(--color-ink-muted)]">
              Target Property
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            {lead.property ? (
              <>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Listing</span>
                  <Link to={`/properties/${lead.property.id}`} className="font-semibold text-[var(--color-forest)] hover:underline truncate max-w-[200px]">
                    {lead.property.title}
                  </Link>
                </div>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Public Ref</span>
                  <span className="font-mono text-gray-900">{lead.property.public_reference}</span>
                </div>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Location</span>
                  <span className="text-gray-900">{lead.property.locality}, {lead.property.city}</span>
                </div>
                <div className="flex justify-between border-b border-gray-100 pb-2">
                  <span className="text-gray-500">Price</span>
                  <span className="font-bold text-gray-900">₹ {lead.property.price.toLocaleString('en-IN')}</span>
                </div>
                <div className="pt-2">
                  <Link to={`/properties/${lead.property.id}`}>
                    <Button variant="secondary" size="sm" className="w-full text-xs">
                      View Property Listing
                    </Button>
                  </Link>
                </div>
              </>
            ) : (
              <div className="text-center py-6 text-gray-400">
                <p>No specific property attached to this lead.</p>
                <span className="text-[11px]">General buyer or tenant requirement.</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Notes & History */}
      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-xs uppercase tracking-wider text-[var(--color-ink-muted)]">
            Consultant Notes & Follow-up Log
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs">
          <p className="text-gray-700 bg-gray-50 p-3 rounded border border-gray-200">
            {lead.notes || 'No notes entered for this sales lead.'}
          </p>
        </CardContent>
      </Card>

      {/* MODAL: MARK LOST */}
      <Modal
        isOpen={isLostModalOpen}
        onClose={() => setIsLostModalOpen(false)}
        title="Mark Lead as Lost"
        description="A clear and mandatory loss reason must be recorded for pipeline compliance."
      >
        <form onSubmit={handleMarkLost} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Reason for Loss (Mandatory)
            </label>
            <Input
              required
              placeholder="e.g. Buyer purchased another property in OMR / Budget constrained"
              value={lostReason}
              onChange={(e) => setLostReason(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsLostModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" isLoading={actionLoading}>
              Confirm Loss
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: BOOK SITE VISIT */}
      <Modal
        isOpen={isVisitModalOpen}
        onClose={() => setIsVisitModalOpen(false)}
        title="Schedule Site Visit for this Lead"
        description="Pre-populates the client and property references."
      >
        <form onSubmit={handleBookVisit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Date & Time</label>
            <Input
              type="datetime-local"
              required
              value={visitDate}
              onChange={(e) => setVisitDate(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Operational Instructions</label>
            <Input
              placeholder="e.g. Buyer wants to inspect car parking and terrace"
              value={visitNotes}
              onChange={(e) => setVisitNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsVisitModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Confirm Inspection
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
