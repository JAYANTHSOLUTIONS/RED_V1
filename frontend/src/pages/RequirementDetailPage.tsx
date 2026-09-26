import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import {
  ChevronLeft,
  CheckCircle2,
  XCircle,
  Archive,
  Calendar,
  Sparkles,
  MapPin,
  Building,
} from 'lucide-react';
import { requirementsApi, siteVisitsApi } from '../api';
import type { PropertyRequirement, PropertyMatchItem } from '../api/types';

export default function RequirementDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [requirement, setRequirement] = useState<PropertyRequirement | null>(null);
  const [matches, setMatches] = useState<PropertyMatchItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [matchesLoading, setMatchesLoading] = useState(false);
  const [minScore, setMinScore] = useState(50);

  // Visit modal
  const [isVisitModalOpen, setIsVisitModalOpen] = useState(false);
  const [selectedPropertyId, setSelectedPropertyId] = useState('');
  const [visitDate, setVisitDate] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
  const [visitNotes, setVisitNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const loadRequirement = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await requirementsApi.get(id);
      setRequirement(data);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  const loadMatches = useCallback(async () => {
    if (!id) return;
    setMatchesLoading(true);
    try {
      const res = await requirementsApi.findMatches(id, { min_score: minScore });
      setMatches(res.items);
    } catch {
      // Handle
    } finally {
      setMatchesLoading(false);
    }
  }, [id, minScore]);

  useEffect(() => {
    loadRequirement();
    loadMatches();
  }, [loadRequirement, loadMatches]);

  // Lifecycle transitions
  const handleFulfill = async () => {
    if (!id) return;
    try {
      const updated = await requirementsApi.fulfill(id);
      setRequirement(updated);
      alert('Requirement marked as FULFILLED.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleCancel = async () => {
    if (!id) return;
    try {
      const updated = await requirementsApi.cancel(id);
      setRequirement(updated);
      alert('Requirement marked as CANCELLED.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleArchive = async () => {
    if (!id) return;
    if (!confirm('Archive this requirement?')) return;
    try {
      const updated = await requirementsApi.archive(id);
      setRequirement(updated);
      alert('Requirement archived.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleScheduleVisitForMatch = (propId: string) => {
    setSelectedPropertyId(propId);
    setIsVisitModalOpen(true);
  };

  const handleBookVisitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!requirement || !selectedPropertyId) return;
    setActionLoading(true);
    try {
      await siteVisitsApi.create({
        client_id: requirement.client_id,
        property_id: selectedPropertyId,
        scheduled_at: new Date(visitDate).toISOString(),
        status: 'CONFIRMED',
        notes: visitNotes,
      });
      setIsVisitModalOpen(false);
      alert('Site visit confirmed for matched property.');
      navigate('/site-visits');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Booking failed');
    } finally {
      setActionLoading(false);
    }
  };

  const formatPrice = (price?: number | null) => {
    if (!price) return '-';
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  if (isLoading) {
    return <div className="p-12 text-center text-xs text-gray-500">Loading requirement...</div>;
  }

  if (!requirement) {
    return (
      <div className="p-12 text-center">
        <p className="text-sm font-semibold text-gray-900">Requirement not found</p>
        <Link to="/requirements" className="text-xs text-[var(--color-primary)] hover:underline mt-2 inline-block">
          Return to requirements
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
            to="/requirements"
            className="inline-flex items-center text-xs font-medium text-[var(--color-ink-secondary)] hover:text-[var(--color-ink)]"
          >
            <ChevronLeft className="mr-1 h-4 w-4" /> Requirements
          </Link>
          <span className="text-gray-300">/</span>
          <span className="font-mono text-xs font-bold text-[var(--color-ink)]">REQ-{requirement.id.slice(0, 8)}</span>
        </div>

        <div className="flex items-center gap-2">
          {requirement.status === 'ACTIVE' && (
            <>
              <Button size="sm" onClick={handleFulfill} className="text-xs bg-emerald-700 hover:bg-emerald-800 text-white flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Fulfill
              </Button>
              <Button size="sm" variant="outline" onClick={handleCancel} className="text-xs text-red-600 hover:bg-red-50 border-red-200 flex items-center gap-1">
                <XCircle className="h-3.5 w-3.5" /> Cancel
              </Button>
            </>
          )}

          {requirement.status !== 'ARCHIVED' && (
            <Button size="sm" variant="ghost" onClick={handleArchive} className="text-xs text-gray-500 hover:bg-gray-100">
              <Archive className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Hero Requirement Card */}
      <div className="bg-white rounded-lg border border-[var(--color-border-ui)] p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif text-2xl font-bold text-[var(--color-ink)]">
                {requirement.transaction_type} Requirement: {requirement.property_types || 'Property'}
              </span>
              <Badge
                variant={
                  requirement.status === 'ACTIVE'
                    ? 'success'
                    : requirement.status === 'FULFILLED'
                    ? 'info'
                    : 'neutral'
                }
              >
                {requirement.status}
              </Badge>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Client:{' '}
              <Link to={`/clients/${requirement.client_id}`} className="font-semibold text-gray-900 hover:underline">
                {requirement.client?.full_name || 'Client Record'}
              </Link>{' '}
              ({requirement.client?.phone || 'N/A'})
            </p>
          </div>

          <div className="bg-[var(--color-parchment-warm)] p-3.5 rounded border border-[var(--color-border-ui)] text-right">
            <span className="text-[10px] uppercase font-semibold text-gray-500">Target Budget</span>
            <div className="text-base font-bold text-[var(--color-forest)]">
              {formatPrice(requirement.min_budget)} – {formatPrice(requirement.max_budget)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-4 border-t border-gray-100 text-xs">
          <div>
            <span className="text-gray-400 block text-[10px] uppercase">Preferred Areas</span>
            <span className="font-medium text-gray-800">{requirement.target_locations || 'Any Tamil Nadu'}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px] uppercase">Bedrooms</span>
            <span className="font-medium text-gray-800">{requirement.bedrooms ? `${requirement.bedrooms} BHK` : 'Any'}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px] uppercase">Area Bounds</span>
            <span className="font-medium text-gray-800">
              {requirement.min_area || 0} – {requirement.max_area || 'Max'} sq.ft
            </span>
          </div>
          <div>
            <span className="text-gray-400 block text-[10px] uppercase">Facing</span>
            <span className="font-medium text-gray-800">{requirement.facing || 'Flexible'}</span>
          </div>
        </div>
      </div>

      {/* Matching Results Section */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-4 rounded-lg border border-[var(--color-border-ui)]">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-[var(--color-gold)]" />
            <div>
              <h3 className="text-sm font-bold text-gray-900">Deterministic Inventory Matching</h3>
              <p className="text-xs text-gray-500">Evaluates budget, location, bedroom count, and area tolerances.</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label className="text-xs text-gray-600 font-medium whitespace-nowrap">Min Score:</label>
            <Select
              value={String(minScore)}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="text-xs h-8 w-24"
            >
              <option value="40">40%</option>
              <option value="50">50%</option>
              <option value="60">60%</option>
              <option value="75">75%</option>
              <option value="90">90%</option>
            </Select>
            <Button size="sm" variant="secondary" onClick={loadMatches} isLoading={matchesLoading} className="text-xs h-8">
              Re-run Match
            </Button>
          </div>
        </div>

        {matchesLoading ? (
          <div className="p-12 text-center text-xs text-gray-500 bg-white rounded-lg border border-[var(--color-border-ui)]">
            Evaluating matching properties...
          </div>
        ) : matches.length === 0 ? (
          <div className="bg-white p-12 text-center rounded-lg border border-[var(--color-border-ui)]">
            <p className="text-xs text-gray-500">
              No properties matched with score &ge; {minScore}%. Try lowering the minimum match threshold.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {matches.map((item) => (
              <Card key={item.property.id} className="hover:border-[var(--color-gold)] transition-colors">
                <CardContent className="p-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge
                        variant={item.match_grade === 'EXACT_MATCH' ? 'success' : 'warning'}
                        className="text-[10px] font-bold"
                      >
                        {item.score}% Match ({item.match_grade})
                      </Badge>
                      <span className="font-mono text-xs text-gray-400">{item.property.public_reference}</span>
                      <span className="text-xs font-semibold text-gray-900">{item.property.title}</span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600">
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5 text-gray-400" />
                        {item.property.locality}, {item.property.city}
                      </span>
                      <span className="flex items-center gap-1">
                        <Building className="h-3.5 w-3.5 text-gray-400" />
                        {item.property.bedrooms ? `${item.property.bedrooms} BHK` : item.property.property_type}
                      </span>
                      <span className="font-bold text-[var(--color-forest)]">
                        {formatPrice(item.property.price)}
                      </span>
                    </div>

                    {/* Criteria chips */}
                    <div className="flex flex-wrap items-center gap-1 pt-1">
                      {item.matched_criteria.map((c, i) => (
                        <span key={i} className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-800 font-medium">
                          ✓ {c}
                        </span>
                      ))}
                      {item.unmatched_criteria.map((uc, i) => (
                        <span key={i} className="rounded bg-amber-50 px-2 py-0.5 text-[10px] text-amber-800 font-medium">
                          ✗ {uc}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/properties/${item.property.id}`)}
                      className="text-xs h-8"
                    >
                      View Property
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleScheduleVisitForMatch(item.property.id)}
                      className="text-xs h-8 flex items-center gap-1"
                    >
                      <Calendar className="h-3.5 w-3.5" /> Book Inspection
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* MODAL: BOOK VISIT */}
      <Modal
        isOpen={isVisitModalOpen}
        onClose={() => setIsVisitModalOpen(false)}
        title="Schedule Inspection for Matched Property"
        description="Coordinates site visit between this client and the selected property."
      >
        <form onSubmit={handleBookVisitSubmit} className="space-y-4">
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
            <label className="block text-xs font-semibold text-gray-700 mb-1">Consultant Notes</label>
            <Input
              placeholder="e.g. Matched via automated scoring engine"
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
