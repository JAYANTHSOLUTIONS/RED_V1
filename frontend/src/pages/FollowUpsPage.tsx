import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import {
  Clock,
  Plus,
  CheckCircle2,
  AlertCircle,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { followUpsApi } from '../api/followUps';
import type { FollowUp, FollowUpCreatePayload } from '../api/types';

export default function FollowUpsPage() {
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('SCHEDULED');
  const [actionTypeFilter, setActionTypeFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
  const [isMissModalOpen, setIsMissModalOpen] = useState(false);
  const [activeFollowUpId, setActiveFollowUpId] = useState<string | null>(null);

  const [completionNotes, setCompletionNotes] = useState('');
  const [missNotes, setMissNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const [newFollowUp, setNewFollowUp] = useState<FollowUpCreatePayload>({
    client_id: '',
    lead_id: '',
    property_id: '',
    action_type: 'CALL',
    scheduled_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    notes: '',
  });

  const fetchFollowUps = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await followUpsApi.list({
        status: statusFilter || undefined,
        action_type: actionTypeFilter || undefined,
        limit,
        offset: page * limit,
      });
      setFollowUps(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, actionTypeFilter, page]);

  useEffect(() => {
    fetchFollowUps();
  }, [fetchFollowUps]);

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeFollowUpId) return;
    setActionLoading(true);
    try {
      await followUpsApi.complete(activeFollowUpId, { completion_notes: completionNotes });
      setIsCompleteModalOpen(false);
      setCompletionNotes('');
      setActiveFollowUpId(null);
      fetchFollowUps();
      alert('Follow-up marked completed.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleMissSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeFollowUpId) return;
    setActionLoading(true);
    try {
      await followUpsApi.markMissed(activeFollowUpId, { notes: missNotes });
      setIsMissModalOpen(false);
      setMissNotes('');
      setActiveFollowUpId(null);
      fetchFollowUps();
      alert('Follow-up marked missed.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFollowUp.client_id && !newFollowUp.lead_id) {
      alert('Must provide either client UUID or lead UUID.');
      return;
    }
    setActionLoading(true);
    try {
      await followUpsApi.create({
        ...newFollowUp,
        client_id: newFollowUp.client_id || undefined,
        lead_id: newFollowUp.lead_id || undefined,
        property_id: newFollowUp.property_id || undefined,
        scheduled_at: new Date(newFollowUp.scheduled_at).toISOString(),
      });
      setIsCreateModalOpen(false);
      fetchFollowUps();
      alert('Follow-up task scheduled.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Creation failed');
    } finally {
      setActionLoading(false);
    }
  };

  const statuses = [
    { label: 'Scheduled Queue', value: 'SCHEDULED' },
    { label: 'Completed', value: 'COMPLETED' },
    { label: 'Missed', value: 'MISSED' },
    { label: 'All Tasks', value: '' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Follow-up Operations
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Track consultant calls, document collection, owner negotiations & buyer check-ins
          </p>
        </div>
        <Button onClick={() => setIsCreateModalOpen(true)} className="shrink-0 flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Schedule Follow-up
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-[var(--color-border-ui)] pb-1">
        <div className="flex items-center gap-1 overflow-x-auto text-xs">
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

        <Select
          value={actionTypeFilter}
          onChange={(e) => {
            setActionTypeFilter(e.target.value);
            setPage(0);
          }}
          className="text-xs h-8 w-44 hidden sm:block"
        >
          <option value="">All Action Types</option>
          <option value="CALL">Phone Call</option>
          <option value="SEND_DOCS">Send Documents</option>
          <option value="ARRANGE_VISIT">Arrange Visit</option>
          <option value="OWNER_FOLLOW_UP">Owner Follow-up</option>
          <option value="MISSING_PAPERWORK">Missing Paperwork</option>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading follow-up tasks...
        </div>
      ) : followUps.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <Clock className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No follow-ups in this queue</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Schedule a task to stay aligned with clients.</p>
          <Button size="sm" onClick={() => setIsCreateModalOpen(true)} className="mt-4">
            Schedule Task
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Scheduled Date</TableHead>
                <TableHead>Target Client / Lead</TableHead>
                <TableHead>Action Category</TableHead>
                <TableHead>Task Notes</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {followUps.map((fu) => (
                <TableRow key={fu.id} className="hover:bg-[var(--color-parchment-warm)] transition-colors">
                  <TableCell className="font-semibold text-xs text-[var(--color-ink)] whitespace-nowrap">
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-gray-400" />
                      <span>{new Date(fu.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">
                    <span className="font-semibold text-gray-900">
                      {fu.client?.full_name || (fu.lead ? 'Lead Prospect' : 'Client Record')}
                    </span>
                    {fu.property && (
                      <span className="block text-[10px] text-gray-400">Re: {fu.property.title}</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">{fu.action_type}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-gray-600 max-w-[240px] truncate">
                    {fu.notes || (fu.completion_notes ? `Outcome: ${fu.completion_notes}` : '-')}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        fu.status === 'COMPLETED'
                          ? 'success'
                          : fu.status === 'MISSED'
                          ? 'danger'
                          : 'warning'
                      }
                    >
                      {fu.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    {fu.status === 'SCHEDULED' && (
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setActiveFollowUpId(fu.id);
                            setIsCompleteModalOpen(true);
                          }}
                          className="text-[11px] h-7 px-2 text-emerald-700 hover:bg-emerald-50 border-emerald-300 flex items-center gap-1"
                        >
                          <CheckCircle2 className="h-3 w-3" /> Done
                        </Button>

                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setActiveFollowUpId(fu.id);
                            setIsMissModalOpen(true);
                          }}
                          className="text-[11px] h-7 px-2 text-red-600 hover:bg-red-50"
                        >
                          Missed
                        </Button>
                      </div>
                    )}
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
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} follow-ups
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

      {/* MODAL: COMPLETE FOLLOW-UP */}
      <Modal
        isOpen={isCompleteModalOpen}
        onClose={() => setIsCompleteModalOpen(false)}
        title="Complete Follow-up Task"
        description="Record outcome or next steps from this client interaction."
      >
        <form onSubmit={handleCompleteSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Outcome / Notes</label>
            <Input
              required
              placeholder="e.g. Spoke to buyer, confirmed site visit for Saturday 11am"
              value={completionNotes}
              onChange={(e) => setCompletionNotes(e.target.value)}
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

      {/* MODAL: MARK MISSED */}
      <Modal
        isOpen={isMissModalOpen}
        onClose={() => setIsMissModalOpen(false)}
        title="Mark Follow-up as Missed"
        description="Records missed status with optional reason."
      >
        <form onSubmit={handleMissSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Reason / Notes</label>
            <Input
              placeholder="e.g. Client phone not reachable after 3 attempts"
              value={missNotes}
              onChange={(e) => setMissNotes(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsMissModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" isLoading={actionLoading}>
              Mark Missed
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: CREATE FOLLOW-UP */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Schedule Follow-up Task"
        description="Assign a reminder task targeting a client or lead."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Client UUID</label>
            <Input
              placeholder="Enter client UUID"
              value={newFollowUp.client_id || ''}
              onChange={(e) => setNewFollowUp({ ...newFollowUp, client_id: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Action Type</label>
              <Select
                value={newFollowUp.action_type}
                onChange={(e) => setNewFollowUp({ ...newFollowUp, action_type: e.target.value as any })}
              >
                <option value="CALL">Phone Call</option>
                <option value="SEND_DOCS">Send Documents</option>
                <option value="ARRANGE_VISIT">Arrange Visit</option>
                <option value="OWNER_FOLLOW_UP">Owner Follow-up</option>
                <option value="MISSING_PAPERWORK">Missing Paperwork</option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Scheduled Date & Time</label>
              <Input
                type="datetime-local"
                required
                value={newFollowUp.scheduled_at}
                onChange={(e) => setNewFollowUp({ ...newFollowUp, scheduled_at: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Task Instructions</label>
            <Input
              placeholder="e.g. Call owner to confirm encumbrance certificate date range"
              value={newFollowUp.notes || ''}
              onChange={(e) => setNewFollowUp({ ...newFollowUp, notes: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Schedule Task
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
