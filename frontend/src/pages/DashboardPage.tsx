import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Building, Users, Target, Calendar, Plus, CheckCircle2, Clock, ArrowRight, MapPin } from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import {
  propertiesApi,
  clientsApi,
  leadsApi,
  siteVisitsApi,
  followUpsApi,
} from '../api';
import type {
  Property,
  SiteVisit,
  FollowUp,
  Lead,
} from '../api/types';
import { TnLocationSelector } from '../components/common/TnLocationSelector';

export default function DashboardPage() {
  const navigate = useNavigate();

  // Metrics state
  const [propertyCount, setPropertyCount] = useState<number>(0);
  const [clientCount, setClientCount] = useState<number>(0);
  const [leadCount, setLeadCount] = useState<number>(0);
  const [visitCount, setVisitCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);

  // Lists state
  const [recentProperties, setRecentProperties] = useState<Property[]>([]);
  const [upcomingVisits, setUpcomingVisits] = useState<SiteVisit[]>([]);
  const [pendingFollowUps, setPendingFollowUps] = useState<FollowUp[]>([]);
  const [recentLeads, setRecentLeads] = useState<Lead[]>([]);

  // Modals state
  const [isPropertyModalOpen, setIsPropertyModalOpen] = useState(false);
  const [isClientModalOpen, setIsClientModalOpen] = useState(false);
  const [isLeadModalOpen, setIsLeadModalOpen] = useState(false);
  const [isVisitModalOpen, setIsVisitModalOpen] = useState(false);

  // Form states
  const [newProp, setNewProp] = useState({
    title: '',
    property_type: 'Apartment',
    transaction_type: 'SALE' as 'SALE' | 'RENT' | 'LEASE',
    price: 7500000,
    district: 'Chennai',
    city: 'Chennai',
    locality: 'Velachery',
    pincode: '600042',
    bedrooms: 3,
    built_up_area: 1450,
    address: '',
    google_maps_url: '',
  });

  const [newClient, setNewClient] = useState({
    full_name: '',
    phone: '',
    email: '',
    classification: 'BUYER' as const,
    preferred_contact_method: 'CALL' as const,
  });

  const [newLead, setNewLead] = useState({
    client_id: '',
    source: 'WEBSITE',
    notes: '',
  });

  const [newVisit, setNewVisit] = useState({
    client_id: '',
    property_id: '',
    scheduled_at: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    notes: '',
  });

  const [actionLoading, setActionLoading] = useState(false);

  const loadDashboardData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [propsRes, clientsRes, leadsRes, visitsRes, followUpsRes] = await Promise.allSettled([
        propertiesApi.list({ limit: 4 }),
        clientsApi.list({ limit: 1 }),
        leadsApi.list({ limit: 4 }),
        siteVisitsApi.list({ limit: 4, status: 'CONFIRMED' }),
        followUpsApi.list({ limit: 4, status: 'SCHEDULED' }),
      ]);

      if (propsRes.status === 'fulfilled') {
        setPropertyCount(propsRes.value.total);
        setRecentProperties(propsRes.value.items);
      }
      if (clientsRes.status === 'fulfilled') {
        setClientCount(clientsRes.value.total);
      }
      if (leadsRes.status === 'fulfilled') {
        setLeadCount(leadsRes.value.total);
        setRecentLeads(leadsRes.value.items);
      }
      if (visitsRes.status === 'fulfilled') {
        setVisitCount(visitsRes.value.total);
        setUpcomingVisits(visitsRes.value.items);
      }
      if (followUpsRes.status === 'fulfilled') {
        setPendingFollowUps(followUpsRes.value.items);
      }
    } catch {
      // Handled
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Handler to create property
  const handleCreateProperty = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      const created = await propertiesApi.create({
        ...newProp,
        area_unit: 'sq.ft',
        advertisement_authorized: true,
      });
      setIsPropertyModalOpen(false);
      navigate(`/properties/${created.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create property');
    } finally {
      setActionLoading(false);
    }
  };

  // Handler to create client
  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await clientsApi.create(newClient);
      setIsClientModalOpen(false);
      loadDashboardData();
      alert('Client created successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create client');
    } finally {
      setActionLoading(false);
    }
  };

  // Handler to create lead
  const handleCreateLead = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await leadsApi.create(newLead);
      setIsLeadModalOpen(false);
      loadDashboardData();
      alert('Lead registered successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create lead');
    } finally {
      setActionLoading(false);
    }
  };

  // Handler to schedule visit
  const handleCreateVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await siteVisitsApi.create({
        client_id: newVisit.client_id,
        property_id: newVisit.property_id,
        scheduled_at: new Date(newVisit.scheduled_at).toISOString(),
        status: 'CONFIRMED',
        notes: newVisit.notes,
      });
      setIsVisitModalOpen(false);
      loadDashboardData();
      alert('Site visit scheduled successfully.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to schedule site visit');
    } finally {
      setActionLoading(false);
    }
  };

  // Handler to complete follow-up
  const handleCompleteFollowUp = async (id: string) => {
    try {
      await followUpsApi.complete(id, { completion_notes: 'Completed via Dashboard rapid action' });
      setPendingFollowUps((prev) => prev.filter((f) => f.id !== id));
      alert('Follow-up marked completed.');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to complete follow-up');
    }
  };

  const formatPrice = (price: number) => {
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  return (
    <div className="space-y-6">
      {/* Top Banner with Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--color-border-ui)] pb-5">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Brokerage Operations Command
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Tamil Nadu real-estate inventory, legal preliminary status & client pipelines
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            onClick={() => setIsPropertyModalOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> New Property
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIsClientModalOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Add Client
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIsVisitModalOpen(true)}
            className="flex items-center gap-1.5"
          >
            <Calendar className="h-3.5 w-3.5" /> Book Visit
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="hover:border-[var(--color-gold)] transition-colors cursor-pointer" onClick={() => navigate('/properties')}>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-ink-muted)]">Active Inventory</p>
              <h2 className="mt-1 text-2xl font-bold text-[var(--color-ink)]">{isLoading ? '...' : propertyCount}</h2>
              <span className="text-[11px] text-[var(--color-primary)] hover:underline mt-1 inline-block">Manage listings &rarr;</span>
            </div>
            <div className="rounded-[6px] p-3 bg-teal-50">
              <Building className="h-5 w-5 text-teal-800" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-[var(--color-gold)] transition-colors cursor-pointer" onClick={() => navigate('/clients')}>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-ink-muted)]">Total Clients</p>
              <h2 className="mt-1 text-2xl font-bold text-[var(--color-ink)]">{isLoading ? '...' : clientCount}</h2>
              <span className="text-[11px] text-[var(--color-primary)] hover:underline mt-1 inline-block">View directory &rarr;</span>
            </div>
            <div className="rounded-[6px] p-3 bg-[var(--color-parchment)]">
              <Users className="h-5 w-5 text-[var(--color-forest)]" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-[var(--color-gold)] transition-colors cursor-pointer" onClick={() => navigate('/leads')}>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-ink-muted)]">Pipeline Leads</p>
              <h2 className="mt-1 text-2xl font-bold text-[var(--color-ink)]">{isLoading ? '...' : leadCount}</h2>
              <span className="text-[11px] text-[var(--color-primary)] hover:underline mt-1 inline-block">Pipeline stages &rarr;</span>
            </div>
            <div className="rounded-[6px] p-3 bg-amber-50">
              <Target className="h-5 w-5 text-amber-800" />
            </div>
          </CardContent>
        </Card>

        <Card className="hover:border-[var(--color-gold)] transition-colors cursor-pointer" onClick={() => navigate('/site-visits')}>
          <CardContent className="p-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-ink-muted)]">Site Visits</p>
              <h2 className="mt-1 text-2xl font-bold text-[var(--color-ink)]">{isLoading ? '...' : visitCount}</h2>
              <span className="text-[11px] text-[var(--color-primary)] hover:underline mt-1 inline-block">Visit schedule &rarr;</span>
            </div>
            <div className="rounded-[6px] p-3 bg-blue-50">
              <Calendar className="h-5 w-5 text-blue-800" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid: Properties & Visits */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Properties */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-[var(--color-ink)]">
              Recent Tamil Nadu Properties
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/properties')} className="text-xs">
              View all <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </CardHeader>
          <CardContent className="px-4 pb-4 pt-0">
            <div className="divide-y divide-[var(--color-border-ui)]">
              {recentProperties.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--color-ink-muted)]">
                  No properties found in backend. Click "New Property" above to create one.
                </div>
              ) : (
                recentProperties.map((prop) => (
                  <div
                    key={prop.id}
                    onClick={() => navigate(`/properties/${prop.id}`)}
                    className="flex items-center justify-between py-3 hover:bg-[var(--color-parchment-warm)] px-2 rounded cursor-pointer transition-colors"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <div className="h-11 w-11 shrink-0 overflow-hidden rounded bg-[var(--color-parchment)] border border-[var(--color-border-ui)]">
                        {prop.images && prop.images[0] ? (
                          <img
                            src={prop.images[0].storage_key}
                            alt={prop.title}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-[10px] font-bold text-gray-400">
                            RED
                          </div>
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-xs font-semibold text-[var(--color-ink)]">{prop.title}</p>
                        <p className="truncate text-[11px] text-[var(--color-ink-secondary)]">
                          {formatPrice(prop.price)} • {prop.property_type} • {prop.locality}, {prop.city}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-mono text-[10px] text-gray-500 hidden sm:inline">{prop.public_reference}</span>
                      <Badge
                        variant={
                          prop.status === 'PUBLISHED'
                            ? 'success'
                            : prop.status === 'DRAFT'
                            ? 'neutral'
                            : prop.status === 'PAUSED'
                            ? 'warning'
                            : 'neutral'
                        }
                      >
                        {prop.status}
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Upcoming Site Visits */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-[var(--color-ink)]">
              Upcoming Site Visits
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/site-visits')} className="text-xs">
              View all <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </CardHeader>
          <CardContent className="px-4 pb-4 pt-0">
            <div className="divide-y divide-[var(--color-border-ui)]">
              {upcomingVisits.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--color-ink-muted)]">
                  No upcoming confirmed visits. Use "Book Visit" to schedule one.
                </div>
              ) : (
                upcomingVisits.map((visit) => (
                  <div key={visit.id} className="py-3 px-2 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-[var(--color-ink)]">
                          {new Date(visit.scheduled_at).toLocaleDateString([], {
                            month: 'short',
                            day: 'numeric',
                          })}{' '}
                          •{' '}
                          {new Date(visit.scheduled_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        <Badge variant="warning">{visit.status}</Badge>
                      </div>
                      <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
                        Client: <span className="font-medium text-[var(--color-ink)]">{visit.client?.full_name || 'Client'}</span> ({visit.client?.phone || 'N/A'})
                      </p>
                      <p className="text-[11px] text-gray-500">
                        Property: {visit.property?.title || 'Selected property'}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate('/site-visits')}
                      className="text-xs h-7"
                    >
                      Manage
                    </Button>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Secondary Grid: Follow-ups & Active Leads */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Today's Scheduled Follow-ups */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-[var(--color-ink)]">
              Follow-up Priority Queue
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/follow-ups')} className="text-xs">
              View all <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </CardHeader>
          <CardContent className="px-4 pb-4 pt-0">
            <div className="divide-y divide-[var(--color-border-ui)]">
              {pendingFollowUps.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--color-ink-muted)]">
                  All scheduled follow-up tasks are completed!
                </div>
              ) : (
                pendingFollowUps.map((fu) => (
                  <div key={fu.id} className="py-3 px-2 flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{fu.action_type}</Badge>
                        <span className="text-xs text-gray-500 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(fu.scheduled_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-[var(--color-ink)] mt-1">
                        {fu.client?.full_name || (fu.lead ? 'Lead Follow-up' : 'General')}
                      </p>
                      {fu.notes && <p className="text-[11px] text-gray-500 line-clamp-1">{fu.notes}</p>}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleCompleteFollowUp(fu.id)}
                      className="text-xs h-7 text-emerald-700 hover:bg-emerald-50 border-emerald-300 flex items-center gap-1"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" /> Done
                    </Button>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pipeline Leads */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between py-4">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-[var(--color-ink)]">
              Active Sales Pipeline
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate('/leads')} className="text-xs">
              View all <ArrowRight className="h-3 w-3 ml-1" />
            </Button>
          </CardHeader>
          <CardContent className="px-4 pb-4 pt-0">
            <div className="divide-y divide-[var(--color-border-ui)]">
              {recentLeads.length === 0 ? (
                <div className="py-8 text-center text-xs text-[var(--color-ink-muted)]">
                  No active sales leads.
                </div>
              ) : (
                recentLeads.map((lead) => (
                  <div
                    key={lead.id}
                    onClick={() => navigate('/leads')}
                    className="py-3 px-2 flex items-center justify-between hover:bg-[var(--color-parchment-warm)] rounded cursor-pointer"
                  >
                    <div>
                      <p className="text-xs font-semibold text-[var(--color-ink)]">
                        {lead.client?.full_name || 'Prospect Client'}
                      </p>
                      <p className="text-[11px] text-[var(--color-ink-secondary)]">
                        Source: {lead.source} • {lead.property ? lead.property.title : 'General Requirement'}
                      </p>
                    </div>
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
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* MODAL: CREATE PROPERTY */}
      <Modal
        isOpen={isPropertyModalOpen}
        onClose={() => setIsPropertyModalOpen(false)}
        title="Register New Tamil Nadu Property"
        description="Enter property identity, location specifications, and pricing. Listing defaults to DRAFT."
      >
        <form onSubmit={handleCreateProperty} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Property Title</label>
            <Input
              required
              value={newProp.title}
              onChange={(e) => setNewProp({ ...newProp, title: e.target.value })}
              placeholder="e.g. 3 BHK Luxury Flat in Velachery"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Property Type</label>
              <Select
                value={newProp.property_type}
                onChange={(e) => setNewProp({ ...newProp, property_type: e.target.value })}
              >
                <option value="Apartment">Apartment</option>
                <option value="Villa">Villa</option>
                <option value="Plot">Plot</option>
                <option value="Commercial">Commercial</option>
                <option value="Agricultural">Agricultural</option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Transaction</label>
              <Select
                value={newProp.transaction_type}
                onChange={(e) => setNewProp({ ...newProp, transaction_type: e.target.value as any })}
              >
                <option value="SALE">SALE</option>
                <option value="RENT">RENT</option>
                <option value="LEASE">LEASE</option>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Price (₹ INR)</label>
              <Input
                type="number"
                required
                value={newProp.price}
                onChange={(e) => setNewProp({ ...newProp, price: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Built-up Area (sq.ft)</label>
              <Input
                type="number"
                value={newProp.built_up_area}
                onChange={(e) => setNewProp({ ...newProp, built_up_area: Number(e.target.value) })}
              />
            </div>
          </div>

          {/* Tamil Nadu Location Dropdowns */}
          <div className="border border-gray-200 rounded-lg p-3 bg-gray-50/50">
            <h4 className="text-xs font-semibold text-[var(--color-ink)] uppercase tracking-wider mb-2">
              Tamil Nadu Location Details
            </h4>
            <TnLocationSelector
              district={newProp.district}
              taluk={newProp.taluk || ''}
              village={newProp.locality}
              city={newProp.city}
              onDistrictChange={(d) => setNewProp((prev) => ({ ...prev, district: d }))}
              onTalukChange={(t) => setNewProp((prev) => ({ ...prev, taluk: t }))}
              onVillageChange={(v) => setNewProp((prev) => ({ ...prev, locality: v }))}
              onCityChange={(c) => setNewProp((prev) => ({ ...prev, city: c }))}
              layout="grid-2"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Pincode</label>
              <Input
                required
                value={newProp.pincode}
                onChange={(e) => setNewProp({ ...newProp, pincode: e.target.value })}
                placeholder="e.g. 600017"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Street Address</label>
              <Input
                value={newProp.address || ''}
                onChange={(e) => setNewProp({ ...newProp, address: e.target.value })}
                placeholder="Door No, Street name"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-red-500" />
                Location Link (Google Maps / Map Pin URL)
              </span>
              <span className="text-[10px] text-gray-400 font-normal">e.g. https://maps.app.goo.gl/...</span>
            </label>
            <Input
              value={newProp.google_maps_url || ''}
              onChange={(e) => setNewProp({ ...newProp, google_maps_url: e.target.value })}
              placeholder="https://maps.google.com/?q=... or https://maps.app.goo.gl/..."
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[var(--color-border-ui)]">
            <Button type="button" variant="outline" onClick={() => setIsPropertyModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Save Property Listing
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: CREATE CLIENT */}
      <Modal
        isOpen={isClientModalOpen}
        onClose={() => setIsClientModalOpen(false)}
        title="Add New Client Profile"
        description="Register a buyer, seller, or landlord in the brokerage directory."
      >
        <form onSubmit={handleCreateClient} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Full Legal / Display Name</label>
            <Input
              required
              value={newClient.full_name}
              onChange={(e) => setNewClient({ ...newClient, full_name: e.target.value })}
              placeholder="e.g. R. Sundaram"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Phone Number</label>
              <Input
                required
                value={newClient.phone}
                onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                placeholder="+91 98410 00000"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Email Address</label>
              <Input
                type="email"
                value={newClient.email}
                onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                placeholder="sundaram@gmail.com"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Classification</label>
              <Select
                value={newClient.classification}
                onChange={(e) => setNewClient({ ...newClient, classification: e.target.value as any })}
              >
                <option value="BUYER">BUYER</option>
                <option value="SELLER">SELLER</option>
                <option value="TENANT">TENANT</option>
                <option value="LANDLORD">LANDLORD</option>
                <option value="INVESTOR">INVESTOR</option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Contact Method</label>
              <Select
                value={newClient.preferred_contact_method}
                onChange={(e) => setNewClient({ ...newClient, preferred_contact_method: e.target.value as any })}
              >
                <option value="CALL">CALL</option>
                <option value="WHATSAPP">WHATSAPP</option>
                <option value="EMAIL">EMAIL</option>
              </Select>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[var(--color-border-ui)]">
            <Button type="button" variant="outline" onClick={() => setIsClientModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Save Client Profile
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: BOOK VISIT */}
      <Modal
        isOpen={isVisitModalOpen}
        onClose={() => setIsVisitModalOpen(false)}
        title="Schedule Property Site Visit"
        description="Coordinates client property inspection with conflict checking."
      >
        <form onSubmit={handleCreateVisit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Client</label>
            <Input
              required
              placeholder="Enter Client UUID"
              value={newVisit.client_id}
              onChange={(e) => setNewVisit({ ...newVisit, client_id: e.target.value })}
            />
            <p className="text-[10px] text-gray-400 mt-1">Copy client ID from Clients section or client page</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Property</label>
            <Input
              required
              placeholder="Enter Property UUID"
              value={newVisit.property_id}
              onChange={(e) => setNewVisit({ ...newVisit, property_id: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Date & Time</label>
            <Input
              type="datetime-local"
              required
              value={newVisit.scheduled_at}
              onChange={(e) => setNewVisit({ ...newVisit, scheduled_at: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Operational Notes</label>
            <Input
              value={newVisit.notes}
              onChange={(e) => setNewVisit({ ...newVisit, notes: e.target.value })}
              placeholder="Key handover at site gate"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[var(--color-border-ui)]">
            <Button type="button" variant="outline" onClick={() => setIsVisitModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={actionLoading}>
              Confirm Schedule
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
