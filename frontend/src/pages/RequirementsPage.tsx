import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Search, Plus, FileCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { requirementsApi } from '../api/requirements';
import { clientsApi } from '../api/clients';
import type { PropertyRequirement, PropertyRequirementCreatePayload, Client } from '../api/types';
import { getTnDistricts, getTnTaluks, getTnVillages } from '../utils/tnLocations';

export default function RequirementsPage() {
  const navigate = useNavigate();

  const [requirements, setRequirements] = useState<PropertyRequirement[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [txTypeFilter, setTxTypeFilter] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Add Requirement Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [targetDistrict, setTargetDistrict] = useState('Chennai');
  const [targetTaluk, setTargetTaluk] = useState('');
  const [targetVillage, setTargetVillage] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  const [newReq, setNewReq] = useState<PropertyRequirementCreatePayload>({
    client_id: '',
    transaction_type: 'BUY',
    property_types: 'Apartment',
    target_locations: 'Chennai',
    min_budget: 6000000,
    max_budget: 12000000,
    min_area: 1100,
    max_area: 1600,
    area_unit: 'sq.ft',
    bedrooms: 3,
    notes: '',
  });

  const fetchRequirements = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await requirementsApi.list({
        status: statusFilter || undefined,
        transaction_type: txTypeFilter || undefined,
        search: search || undefined,
        limit,
        offset: page * limit,
      });
      setRequirements(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, txTypeFilter, search, page]);

  useEffect(() => {
    fetchRequirements();
  }, [fetchRequirements]);

  // Load registered clients for dropdown selection (reduces manual UUID typing)
  useEffect(() => {
    clientsApi
      .list({ limit: 100 })
      .then((res) => {
        setClients(res.items);
        if (res.items.length > 0) {
          setNewReq((prev) => (prev.client_id ? prev : { ...prev, client_id: res.items[0].id }));
        }
      })
      .catch(() => {});
  }, []);

  const addLocationChip = (locationName: string) => {
    if (!locationName.trim()) return;
    const current = newReq.target_locations
      ? newReq.target_locations.split(',').map((s) => s.trim()).filter(Boolean)
      : [];
    if (!current.includes(locationName.trim())) {
      const updated = [...current, locationName.trim()].join(', ');
      setNewReq((prev) => ({ ...prev, target_locations: updated }));
    }
  };

  const removeLocationChip = (locationName: string) => {
    const current = newReq.target_locations
      ? newReq.target_locations.split(',').map((s) => s.trim()).filter(Boolean)
      : [];
    const updated = current.filter((s) => s !== locationName).join(', ');
    setNewReq((prev) => ({ ...prev, target_locations: updated }));
  };

  const selectedLocationsList = newReq.target_locations
    ? newReq.target_locations.split(',').map((s) => s.trim()).filter(Boolean)
    : [];

  const villagesForTaluk = targetDistrict && targetTaluk ? getTnVillages(targetDistrict, targetTaluk) : [];

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchRequirements();
  };

  const handleCreateRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const created = await requirementsApi.create(newReq);
      setIsModalOpen(false);
      navigate(`/requirements/${created.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to record requirement');
    } finally {
      setCreateLoading(false);
    }
  };

  const formatPrice = (price?: number | null) => {
    if (!price) return '-';
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  const statuses = [
    { label: 'All', value: '' },
    { label: 'Active', value: 'ACTIVE' },
    { label: 'Fulfilled', value: 'FULFILLED' },
    { label: 'Cancelled', value: 'CANCELLED' },
    { label: 'Archived', value: 'ARCHIVED' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Client Property Requirements
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Buyer & tenant parameters powering automated, deterministic inventory matching
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="shrink-0 flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Add Requirement
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

      {/* Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-[8px] border border-[var(--color-border-ui)] shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex flex-1 items-center space-x-2 w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-ink-muted)]" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search target locations, localities, notes... (Press Enter)"
              className="pl-9 text-xs h-9"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm" className="shrink-0 text-xs">
            Search
          </Button>
        </form>

        <Select
          value={txTypeFilter}
          onChange={(e) => {
            setTxTypeFilter(e.target.value);
            setPage(0);
          }}
          className="text-xs h-9 w-full sm:w-36"
        >
          <option value="">All Transactions</option>
          <option value="BUY">BUY</option>
          <option value="RENT">RENT</option>
          <option value="LEASE">LEASE</option>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading requirements...
        </div>
      ) : requirements.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <FileCheck className="mx-auto h-9 w-9 text-[var(--color-ink-muted)] mb-2" />
          <h3 className="text-sm font-semibold text-[var(--color-ink)]">No requirements registered</h3>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1 mb-4">
            Record buyer and tenant parameters to trigger deterministic property matches.
          </p>
          <Button onClick={() => setIsModalOpen(true)} size="sm">
            <Plus className="h-4 w-4 mr-1" /> Add First Requirement
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-[var(--color-border-ui)] shadow-sm overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Client</TableHead>
                  <TableHead className="text-xs">Type & Specs</TableHead>
                  <TableHead className="text-xs">Budget Range</TableHead>
                  <TableHead className="text-xs">Area Range</TableHead>
                  <TableHead className="text-xs">Target Locations</TableHead>
                  <TableHead className="text-xs">Status</TableHead>
                  <TableHead className="text-xs text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requirements.map((req) => (
                  <TableRow
                    key={req.id}
                    className="hover:bg-amber-50/20 cursor-pointer"
                    onClick={() => navigate(`/requirements/${req.id}`)}
                  >
                    <TableCell className="font-medium text-xs">
                      <div>
                        <span className="font-semibold text-gray-900">
                          {req.client?.full_name || 'Client #' + req.client_id.slice(0, 8)}
                        </span>
                        {req.client?.phone && (
                          <div className="text-[11px] text-gray-500">{req.client.phone}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs">
                      <div className="font-medium text-gray-800">
                        {req.transaction_type} • {req.property_types || 'Any Property'}
                      </div>
                      <div className="text-[11px] text-gray-500">
                        {req.bedrooms ? `${req.bedrooms} BHK` : 'Any BHK'}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs font-semibold text-[var(--color-forest)]">
                      {formatPrice(req.min_budget)} - {formatPrice(req.max_budget)}
                    </TableCell>
                    <TableCell className="text-xs text-gray-600">
                      {req.min_area || req.max_area
                        ? `${req.min_area || 0} - ${req.max_area || '∞'} ${req.area_unit || 'sq.ft'}`
                        : '-'}
                    </TableCell>
                    <TableCell className="text-xs max-w-xs truncate text-gray-700">
                      {req.target_locations || 'Any in Tamil Nadu'}
                    </TableCell>
                    <TableCell className="text-xs">
                      <Badge
                        variant={
                          req.status === 'ACTIVE'
                            ? 'success'
                            : req.status === 'FULFILLED'
                            ? 'info'
                            : 'neutral'
                        }
                      >
                        {req.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-right">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/requirements/${req.id}`);
                        }}
                      >
                        View Matches
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-gray-600 px-1">
            <span>
              Showing {requirements.length > 0 ? page * limit + 1 : 0} to{' '}
              {Math.min((page + 1) * limit, total)} of {total} requirements
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                className="text-xs"
              >
                <ChevronLeft className="h-3 w-3 mr-1" /> Prev
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
        </div>
      )}

      {/* MODAL: ADD REQUIREMENT */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Record Client Property Requirement"
        description="Select client parameters and locations to automatically trigger deterministic scoring."
      >
        <form onSubmit={handleCreateRequirement} className="space-y-4 max-h-[75vh] overflow-y-auto px-1">
          {/* Client Selection Dropdown - Zero typing needed */}
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">
              Select Client <span className="text-red-500">*</span>
            </label>
            {clients.length > 0 ? (
              <Select
                required
                value={newReq.client_id}
                onChange={(e) => setNewReq({ ...newReq, client_id: e.target.value })}
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
                placeholder="Enter client UUID"
                value={newReq.client_id}
                onChange={(e) => setNewReq({ ...newReq, client_id: e.target.value })}
              />
            )}
          </div>

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
              <Select
                value={newReq.property_types || 'Apartment'}
                onChange={(e) => setNewReq({ ...newReq, property_types: e.target.value })}
              >
                <option value="Apartment">Apartment</option>
                <option value="Independent House / Villa">Independent House / Villa</option>
                <option value="Residential Plot">Residential Plot</option>
                <option value="Commercial Office">Commercial Office</option>
                <option value="Commercial Land">Commercial Land</option>
                <option value="Agricultural Land">Agricultural Land</option>
                <option value="Industrial / Warehouse">Industrial / Warehouse</option>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Min Budget (₹)</label>
              <Input
                type="number"
                step="50000"
                value={newReq.min_budget || 0}
                onChange={(e) => setNewReq({ ...newReq, min_budget: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Max Budget (₹)</label>
              <Input
                type="number"
                step="50000"
                value={newReq.max_budget || 0}
                onChange={(e) => setNewReq({ ...newReq, max_budget: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Bedrooms</label>
              <Select
                value={String(newReq.bedrooms || 3)}
                onChange={(e) => setNewReq({ ...newReq, bedrooms: Number(e.target.value) })}
              >
                <option value="1">1 BHK</option>
                <option value="2">2 BHK</option>
                <option value="3">3 BHK</option>
                <option value="4">4 BHK</option>
                <option value="5">5+ BHK</option>
              </Select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Min Area</label>
              <Input
                type="number"
                value={newReq.min_area || ''}
                onChange={(e) => setNewReq({ ...newReq, min_area: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Max Area</label>
              <Input
                type="number"
                value={newReq.max_area || ''}
                onChange={(e) => setNewReq({ ...newReq, max_area: Number(e.target.value) })}
              />
            </div>
          </div>

          {/* Tamil Nadu Location Dropdowns: District, Taluk, Revenue Village */}
          <div className="border border-gray-200 rounded-lg p-3 bg-gray-50/70 space-y-2.5">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wider">
                Tamil Nadu Location & Revenue Village Dropdowns
              </h4>
              <span className="text-[10px] text-gray-500 font-medium">17,237+ villages database</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label className="block text-[11px] font-semibold text-gray-700 mb-1">1. District</label>
                <Select
                  value={targetDistrict}
                  onChange={(e) => {
                    const d = e.target.value;
                    setTargetDistrict(d);
                    setTargetTaluk('');
                    setTargetVillage('');
                    if (d) addLocationChip(d);
                  }}
                >
                  <option value="">All Districts (38)</option>
                  {getTnDistricts().map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-700 mb-1">2. Taluk</label>
                <Select
                  value={targetTaluk}
                  onChange={(e) => {
                    const t = e.target.value;
                    setTargetTaluk(t);
                    setTargetVillage('');
                    if (t) addLocationChip(t);
                  }}
                  disabled={!targetDistrict}
                >
                  <option value="">{!targetDistrict ? 'Select District first' : 'All Taluks'}</option>
                  {getTnTaluks(targetDistrict).map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-gray-700 mb-1">
                  3. Revenue Village {villagesForTaluk.length > 0 && `(${villagesForTaluk.length})`}
                </label>
                <Select
                  value={targetVillage}
                  onChange={(e) => {
                    const v = e.target.value;
                    setTargetVillage(v);
                    if (v) addLocationChip(v);
                  }}
                  disabled={!targetTaluk || villagesForTaluk.length === 0}
                >
                  <option value="">
                    {!targetTaluk
                      ? 'Select Taluk first'
                      : villagesForTaluk.length === 0
                      ? 'No villages found'
                      : 'Select Village'}
                  </option>
                  {villagesForTaluk.map((v) => (
                    <option key={v} value={v}>
                      {v}
                    </option>
                  ))}
                </Select>
              </div>
            </div>

            {/* Selected Locations Tags - Click to Remove */}
            <div>
              <label className="block text-[11px] text-gray-600 mb-1">
                Selected Target Locations (Click &times; to remove, or pick from dropdowns above):
              </label>
              <div className="flex flex-wrap items-center gap-1.5 min-h-[36px] p-2 bg-white rounded border border-gray-200">
                {selectedLocationsList.length === 0 ? (
                  <span className="text-xs text-gray-400">
                    No location selected yet. Choose a District, Taluk, or Village above.
                  </span>
                ) : (
                  selectedLocationsList.map((loc) => (
                    <span
                      key={loc}
                      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-900 border border-amber-200"
                    >
                      {loc}
                      <button
                        type="button"
                        onClick={() => removeLocationChip(loc)}
                        className="text-amber-700 hover:text-red-600 font-bold ml-0.5 text-sm leading-none"
                        title="Remove location"
                      >
                        &times;
                      </button>
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createLoading}>
              Save Requirement
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
