import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import {
  Calendar,
  Plus,
  CheckCircle2,
  Clock,
  XCircle,
  RotateCcw,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { siteVisitsApi } from '../api/siteVisits';
import { clientsApi } from '../api/clients';
import { propertiesApi } from '../api/properties';
import type { SiteVisit, SiteVisitCreatePayload, Client, Property } from '../api/types';

export default function SiteVisitsPage() {
  const [visits, setVisits] = useState<SiteVisit[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Dropdown options
  const [clients, setClients] = useState<Client[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);

  // Create Modal
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newVisit, setNewVisit] = useState<SiteVisitCreatePayload>({
    client_id: '',
    property_id: '',
    scheduled_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    status: 'CONFIRMED',
    notes: '',
  });

  useEffect(() => {
    clientsApi.list({ limit: 100 }).then((res) => {
      setClients(res.items);
      if (res.items.length > 0) {
        setNewVisit((prev) => (prev.client_id ? prev : { ...prev, client_id: res.items[0].id }));
      }
    }).catch(() => {});

    propertiesApi.list({ limit: 100 }).then((res) => {
      setProperties(res.items);
      if (res.items.length > 0) {
        setNewVisit((prev) => (prev.property_id ? prev : { ...prev, property_id: res.items[0].id }));
      }
    }).catch(() => {});
  }, []);

  // Action Modals
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
  const [isCancelModalOpen, setIsCancelModalOpen] = useState(false);
  const [isRescheduleModalOpen, setIsRescheduleModalOpen] = useState(false);
  const [activeVisitId, setActiveVisitId] = useState<string | null>(null);

  const [completeFeedback, setCompleteFeedback] = useState('');
  const [cancelReason, setCancelReason] = useState('');
  const [rescheduleDate, setRescheduleDate] = useState(new Date(Date.now() + 172800000).toISOString().slice(0, 16));
  const [rescheduleReason, setRescheduleReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchVisits = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await siteVisitsApi.list({
        status: statusFilter || undefined,
        limit,
        offset: page * limit,
      });
      setVisits(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    fetchVisits();
  }, [fetchVisits]);

  // Actions
  const handleConfirm = async (visitId: string) => {
    try {
      await siteVisitsApi.confirm(visitId);
      fetchVisits();
      alert('Visit confirmed.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Confirmation failed');
    }
  };

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeVisitId) return;
    setActionLoading(true);
    try {
      await siteVisitsApi.complete(activeVisitId, { feedback: completeFeedback });
      setIsCompleteModalOpen(false);
      setCompleteFeedback('');
      setActiveVisitId(null);
      fetchVisits();
      alert('Site visit marked as COMPLETED.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeVisitId || !cancelReason.trim()) return;
    setActionLoading(true);
    try {
      await siteVisitsApi.cancel(activeVisitId, { cancellation_reason: cancelReason.trim() });
      setIsCancelModalOpen(false);
      setCancelReason('');
      setActiveVisitId(null);
      fetchVisits();
      alert('Site visit cancelled.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Cancellation failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeVisitId) return;
    setActionLoading(true);
    try {
      await siteVisitsApi.reschedule(activeVisitId, {
        new_scheduled_at: new Date(rescheduleDate).toISOString(),
        reason: rescheduleReason,
      });
      setIsRescheduleModalOpen(false);
      setRescheduleReason('');
      setActiveVisitId(null);
      fetchVisits();
      alert('Site visit rescheduled with newly linked record.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Reschedule failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await siteVisitsApi.create({
        ...newVisit,
        scheduled_at: new Date(newVisit.scheduled_at).toISOString(),
      });
      setIsCreateModalOpen(false);
      fetchVisits();
      alert('Site visit scheduled.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to schedule');
    } finally {
      setActionLoading(false);
    }
  };

  const statuses = [
    { label: 'All Inspections', value: '' },
    { label: 'Requested', value: 'REQUESTED' },
    { label: 'Confirmed', value: 'CONFIRMED' },
    { label: 'Completed', value: 'COMPLETED' },
    { label: 'Cancelled', value: 'CANCELLED' },
    { label: 'Rescheduled', value: 'RESCHEDULED' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Site Visit Coordination
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Client walkthroughs, conflict-checked schedules & buyer feedback collection
          </p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)} className="shrink-0 flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Book Inspection
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border-ui)] overflow-x-auto pb-1 text-xs">
        {statuses.map((st) => (
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

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading site visit records...
        </div>
      ) : visits.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <Calendar className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No site visits found</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Book an inspection for a prospective buyer.</p>
          <Button size="sm" onClick={() => setIsCreateModalOpen(true)} className="mt-4">
            Book Inspection
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date & Time</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Property</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Feedback / Notes</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visits.map((visit) => (
                <TableRow key={visit.id} className="hover:bg-[var(--color-parchment-warm)] transition-colors">
                  <TableCell className="font-semibold text-xs text-[var(--color-ink)] whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-gray-400" />
                      <div>
                        <span>{new Date(visit.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                        <span className="block text-[10px] text-gray-400 font-normal">
                          {new Date(visit.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">
                    <span className="font-semibold text-gray-900">{visit.client?.full_name || 'Client'}</span>
                    <span className="block text-[10px] text-gray-400">{visit.client?.phone || ''}</span>
                  </TableCell>
                  <TableCell className="text-xs max-w-[200px] truncate">
                    <span className="font-medium text-gray-900">{visit.property?.title || 'Property'}</span>
                    <span className="block font-mono text-[10px] text-gray-400">{visit.property?.public_reference || ''}</span>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        visit.status === 'CONFIRMED'
                          ? 'warning'
                          : visit.status === 'COMPLETED'
                          ? 'success'
                          : visit.status === 'CANCELLED'
                          ? 'danger'
                          : 'neutral'
                      }
                    >
                      {visit.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-gray-500 max-w-[180px] truncate">
                    {visit.feedback || visit.notes || (visit.cancellation_reason ? `Cancelled: ${visit.cancellation_reason}` : '-')}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1.5">
                      {visit.status === 'REQUESTED' && (
                        <Button
                          size="sm"
                          onClick={() => handleConfirm(visit.id)}
                          className="text-[11px] h-7 px-2"
                        >
                          Confirm
                        </Button>
                      )}

                      {visit.status === 'CONFIRMED' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setActiveVisitId(visit.id);
                            setIsCompleteModalOpen(true);
                          }}
                          className="text-[11px] h-7 px-2 text-emerald-700 hover:bg-emerald-50 border-emerald-300 flex items-center gap-1"
                        >
                          <CheckCircle2 className="h-3 w-3" /> Complete
                        </Button>
                      )}

                      {(visit.status === 'CONFIRMED' || visit.status === 'REQUESTED') && (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setActiveVisitId(visit.id);
                              setIsRescheduleModalOpen(true);
                            }}
                            className="text-[11px] h-7 px-1.5"
                            title="Reschedule"
                          >
                            <RotateCcw className="h-3.5 w-3.5" />
                          </Button>

                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              setActiveVisitId(visit.id);
                              setIsCancelModalOpen(true);
                            }}
                            className="text-[11px] h-7 px-1.5 text-red-600 hover:bg-red-50"
                            title="Cancel"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      )}
                    </div>
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
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} visits
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

      {/* MODAL: COMPLETE VISIT */}
      <Modal
        isOpen={isCompleteModalOpen}
        onClose={() => setIsCompleteModalOpen(false)}
        title="Record Visit Completion & Feedback"
        description="Transitions site visit to COMPLETED and stores client feedback."
      >
        <form onSubmit={handleCompleteSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Client Feedback / Outcome
            </label>
            <Input
              required
              placeholder="e.g. Buyer loved the terrace view, requested price negotiation"
              value={completeFeedback}
              onChange={(e) => setCompleteFeedback(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsCompleteModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Save Completion
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: CANCEL VISIT */}
      <Modal
        isOpen={isCancelModalOpen}
        onClose={() => setIsCancelModalOpen(false)}
        title="Cancel Scheduled Visit"
        description="Preserves historical audit log with mandatory cancellation reason."
      >
        <form onSubmit={handleCancelSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Cancellation Reason (Mandatory)
            </label>
            <Input
              required
              placeholder="e.g. Client requested cancellation due to travel"
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsCancelModalOpen(false)}>
              Back
            </Button>
            <Button type="submit" variant="destructive" isLoading={actionLoading}>
              Confirm Cancellation
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: RESCHEDULE VISIT */}
      <Modal
        isOpen={isRescheduleModalOpen}
        onClose={() => setIsRescheduleModalOpen(false)}
        title="Reschedule Site Visit"
        description="Creates a newly linked confirmed visit record and marks the current as RESCHEDULED."
      >
        <form onSubmit={handleRescheduleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">New Inspection Timestamp</label>
            <Input
              type="datetime-local"
              required
              value={rescheduleDate}
              onChange={(e) => setRescheduleDate(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Reason for Rescheduling</label>
            <Input
              placeholder="e.g. Weather delay / owner unavailable"
              value={rescheduleReason}
              onChange={(e) => setRescheduleReason(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsRescheduleModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Reschedule Visit
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: CREATE VISIT */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Book New Site Visit"
        description="Coordinates client and property inspection with conflict checking."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Select Client <span className="text-red-500">*</span>
            </label>
            {clients.length > 0 ? (
              <Select
                required
                value={newVisit.client_id}
                onChange={(e) => setNewVisit({ ...newVisit, client_id: e.target.value })}
              >
                <option value="">Select a Client ({clients.length} Registered)</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.full_name} ({c.phone || c.email || 'No contact'})
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                required
                placeholder="Enter client UUID"
                value={newVisit.client_id}
                onChange={(e) => setNewVisit({ ...newVisit, client_id: e.target.value })}
              />
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Select Property <span className="text-red-500">*</span>
            </label>
            {properties.length > 0 ? (
              <Select
                required
                value={newVisit.property_id}
                onChange={(e) => setNewVisit({ ...newVisit, property_id: e.target.value })}
              >
                <option value="">Select Property ({properties.length} Available)</option>
                {properties.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.public_reference} - {p.title} ({p.locality}, {p.district})
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                required
                placeholder="Enter property UUID"
                value={newVisit.property_id}
                onChange={(e) => setNewVisit({ ...newVisit, property_id: e.target.value })}
              />
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Inspection Timestamp</label>
            <Input
              type="datetime-local"
              required
              value={newVisit.scheduled_at}
              onChange={(e) => setNewVisit({ ...newVisit, scheduled_at: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Consultant Notes</label>
            <Input
              placeholder="e.g. Key collection at association office"
              value={newVisit.notes || ''}
              onChange={(e) => setNewVisit({ ...newVisit, notes: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Schedule Visit
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
