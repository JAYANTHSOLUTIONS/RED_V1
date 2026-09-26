import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Search, Plus, LayoutGrid, List, ChevronLeft, ChevronRight, Eye, MapPin, ExternalLink } from 'lucide-react';
import { propertiesApi } from '../api/properties';
import type { Property, PropertyCreatePayload } from '../api/types';
import { TnLocationSelector } from '../components/common/TnLocationSelector';
import { getTnDistricts } from '../utils/tnLocations';
import { TngisSearchModal } from '../components/tngis/TngisSearchModal';

export default function PropertiesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const [properties, setProperties] = useState<Property[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');

  // Filters
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [districtFilter, setDistrictFilter] = useState(searchParams.get('district') || '');
  const [typeFilter, setTypeFilter] = useState(searchParams.get('property_type') || '');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Add Property Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTngisModalOpen, setIsTngisModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newProp, setNewProp] = useState<PropertyCreatePayload>({
    title: '',
    description: '',
    property_type: 'Apartment',
    transaction_type: 'SALE',
    price: 6500000,
    built_up_area: 1250,
    plot_area: 0,
    area_unit: 'sq.ft',
    bedrooms: 3,
    bathrooms: 2,
    district: 'Chennai',
    city: 'Chennai',
    taluk: 'Mambalam',
    locality: 'T. Nagar',
    pincode: '600017',
    google_maps_url: '',
    owner_name: '',
    owner_phone: '',
    owner_email: '',
    advertisement_authorized: true,
  });

  const fetchProperties = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await propertiesApi.list({
        search: search || undefined,
        status: statusFilter || undefined,
        district: districtFilter || undefined,
        property_type: typeFilter || undefined,
        limit,
        offset: page * limit,
        sort_by: 'created_at',
        sort_order: 'desc',
      });
      setProperties(res.items);
      setTotal(res.total);
    } catch {
      // Offline fallback
    } finally {
      setIsLoading(false);
    }
  }, [search, statusFilter, districtFilter, typeFilter, page]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    setSearchParams((prev) => {
      if (search) prev.set('search', search);
      else prev.delete('search');
      return prev;
    });
    fetchProperties();
  };

  const handleStatusTab = (status: string) => {
    setStatusFilter(status);
    setPage(0);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const created = await propertiesApi.create(newProp);
      setIsModalOpen(false);
      navigate(`/properties/${created.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create listing');
    } finally {
      setCreateLoading(false);
    }
  };

  const formatPrice = (price: number) => {
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  const statusList = [
    { label: 'All Listings', value: '' },
    { label: 'Published', value: 'PUBLISHED' },
    { label: 'Draft', value: 'DRAFT' },
    { label: 'Paused', value: 'PAUSED' },
    { label: 'Sold', value: 'SOLD' },
    { label: 'Rented', value: 'RENTED' },
    { label: 'Archived', value: 'ARCHIVED' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Properties Inventory
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Verified Tamil Nadu residential, commercial & plotted land listings
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setIsTngisModalOpen(true)}
            className="shrink-0 flex items-center gap-1.5 border-[var(--color-forest)] text-[var(--color-forest)] font-bold hover:bg-emerald-50"
          >
            <Search className="h-4 w-4" /> TNGIS Land & Revenue Search
          </Button>
          <Button onClick={() => setIsModalOpen(true)} className="shrink-0 flex items-center gap-1.5">
            <Plus className="h-4 w-4" /> Add Property Listing
          </Button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border-ui)] overflow-x-auto pb-1 text-xs">
        {statusList.map((st) => (
          <button
            key={st.value}
            onClick={() => handleStatusTab(st.value)}
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

      {/* Search & Secondary Filter Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-[8px] border border-[var(--color-border-ui)] shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex flex-1 items-center space-x-2 w-full">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-ink-muted)]" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reference, title, locality, taluk... (Press Enter)"
              className="pl-9 text-xs h-9"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm" className="shrink-0 text-xs">
            Search
          </Button>
        </form>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <Select
            value={districtFilter}
            onChange={(e) => {
              setDistrictFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs h-9 w-40"
          >
            <option value="">All Districts (38)</option>
            {getTnDistricts().map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>

          <Select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(0);
            }}
            className="text-xs h-9 w-32"
          >
            <option value="">All Types</option>
            <option value="Apartment">Apartment</option>
            <option value="Villa">Villa</option>
            <option value="Plot">Plot</option>
            <option value="Commercial">Commercial</option>
          </Select>

          <div className="flex items-center space-x-1 shrink-0 bg-[var(--color-parchment)] p-1 rounded-[6px]">
            <button
              className={`p-1.5 rounded-[4px] transition-colors ${
                viewMode === 'table'
                  ? 'bg-white shadow-sm text-[var(--color-ink)]'
                  : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
              }`}
              onClick={() => setViewMode('table')}
              title="Table view"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              className={`p-1.5 rounded-[4px] transition-colors ${
                viewMode === 'grid'
                  ? 'bg-white shadow-sm text-[var(--color-ink)]'
                  : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
              }`}
              onClick={() => setViewMode('grid')}
              title="Grid view"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading properties directory...
        </div>
      ) : properties.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <p className="text-sm font-semibold text-[var(--color-ink)]">No properties found</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Try resetting search filters or register a new property listing.</p>
          <Button size="sm" onClick={() => setIsModalOpen(true)} className="mt-4">
            Register Property
          </Button>
        </div>
      ) : viewMode === 'table' ? (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[120px]">Reference</TableHead>
                <TableHead>Property</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Price</TableHead>
                <TableHead>Location</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Specifications</TableHead>
                <TableHead className="w-[60px]"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {properties.map((prop) => (
                <TableRow
                  key={prop.id}
                  onClick={() => navigate(`/properties/${prop.id}`)}
                  className="cursor-pointer hover:bg-[var(--color-parchment-warm)] transition-colors"
                >
                  <TableCell className="font-mono text-xs font-semibold text-[var(--color-ink)]">
                    {prop.public_reference}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      <div className="h-10 w-12 shrink-0 rounded bg-[var(--color-parchment)] overflow-hidden border border-[var(--color-border-ui)]">
                        {prop.images && prop.images[0] ? (
                          <img
                            src={prop.images[0].storage_key}
                            alt=""
                            className="object-cover w-full h-full"
                          />
                        ) : (
                          <div className="h-full w-full flex items-center justify-center text-[10px] text-gray-400 font-bold">
                            RED
                          </div>
                        )}
                      </div>
                      <div>
                        <div className="font-semibold text-xs text-[var(--color-ink)] line-clamp-1">{prop.title}</div>
                        <div className="text-[11px] text-[var(--color-ink-muted)] line-clamp-1">
                          {prop.transaction_type} • {prop.locality}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">{prop.property_type}</TableCell>
                  <TableCell className="text-xs font-bold text-[var(--color-ink)]">
                    {formatPrice(prop.price)}
                  </TableCell>
                  <TableCell className="text-xs text-[var(--color-ink-secondary)]">
                    <div className="font-medium text-gray-800">{prop.locality}, {prop.city}</div>
                    {prop.google_maps_url && (
                      <a
                        href={prop.google_maps_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-800 hover:underline mt-0.5 font-medium"
                      >
                        <MapPin className="h-3 w-3 text-red-500" /> Location Link ↗
                      </a>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        prop.status === 'PUBLISHED'
                          ? 'success'
                          : prop.status === 'DRAFT'
                          ? 'neutral'
                          : prop.status === 'PAUSED'
                          ? 'warning'
                          : 'secondary'
                      }
                    >
                      {prop.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-[11px] text-[var(--color-ink-muted)]">
                    {prop.bedrooms ? `${prop.bedrooms} BHK • ` : ''}
                    {prop.built_up_area ? `${prop.built_up_area} sq.ft` : prop.plot_area ? `${prop.plot_area} sq.ft` : '-'}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => navigate(`/properties/${prop.id}`)}
                      className="h-8 w-8 p-0"
                    >
                      <Eye className="h-4 w-4 text-[var(--color-ink-muted)]" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : (
        /* Grid View */
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {properties.map((prop) => (
            <div
              key={prop.id}
              onClick={() => navigate(`/properties/${prop.id}`)}
              className="group bg-white rounded-lg border border-[var(--color-border-ui)] overflow-hidden hover:border-[var(--color-gold)] transition-all cursor-pointer shadow-sm hover:shadow"
            >
              <div className="relative h-44 bg-gray-100 overflow-hidden">
                {prop.images && prop.images[0] ? (
                  <img
                    src={prop.images[0].storage_key}
                    alt={prop.title}
                    className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                ) : (
                  <div className="h-full w-full flex items-center justify-center font-serif text-lg font-bold text-gray-300">
                    RED_V1
                  </div>
                )}
                <div className="absolute top-2 left-2 flex gap-1.5">
                  <Badge variant="neutral" className="bg-black/70 text-white border-0 backdrop-blur-sm text-[10px]">
                    {prop.public_reference}
                  </Badge>
                </div>
                <div className="absolute top-2 right-2">
                  <Badge
                    variant={
                      prop.status === 'PUBLISHED'
                        ? 'success'
                        : prop.status === 'DRAFT'
                        ? 'neutral'
                        : 'warning'
                    }
                  >
                    {prop.status}
                  </Badge>
                </div>
              </div>

              <div className="p-4">
                <div className="flex items-center justify-between text-xs text-[var(--color-ink-muted)] mb-1">
                  <span>{prop.property_type} • For {prop.transaction_type}</span>
                  <span className="flex items-center gap-1">
                    {prop.locality}
                    {prop.google_maps_url && (
                      <a
                        href={prop.google_maps_url}
                        target="_blank"
                        rel="noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title="Open Map Location Link"
                        className="text-blue-600 hover:text-blue-800 ml-0.5"
                      >
                        <MapPin className="h-3 w-3 text-red-500 inline" />
                      </a>
                    )}
                  </span>
                </div>
                <h3 className="font-semibold text-sm text-[var(--color-ink)] line-clamp-1 group-hover:text-[var(--color-forest)] transition-colors">
                  {prop.title}
                </h3>
                <p className="mt-2 text-base font-bold text-[var(--color-forest)]">
                  {formatPrice(prop.price)}
                </p>
                <div className="mt-3 pt-3 border-t border-[var(--color-border-ui)] flex items-center justify-between text-[11px] text-[var(--color-ink-muted)]">
                  <span>{prop.bedrooms ? `${prop.bedrooms} Bedrooms` : 'Plotted Area'}</span>
                  <span>{prop.built_up_area || prop.plot_area || 0} sq.ft</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Footer */}
      {total > limit && (
        <div className="flex items-center justify-between border-t border-[var(--color-border-ui)] pt-4 text-xs">
          <span className="text-[var(--color-ink-muted)]">
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} listings
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

      {/* MODAL: ADD PROPERTY */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register Property in Tamil Nadu Workspace"
        description="Creates private inventory listing. Set specifications, owner contact, and legal locality details."
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4 max-h-[75vh] overflow-y-auto px-1">
          <div>
            <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Listing Title</label>
            <Input
              required
              value={newProp.title}
              onChange={(e) => setNewProp({ ...newProp, title: e.target.value })}
              placeholder="e.g. 3 BHK Luxury Apartment near Anna Nagar Tower"
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
                value={newProp.built_up_area || ''}
                onChange={(e) => setNewProp({ ...newProp, built_up_area: Number(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[var(--color-ink)] mb-1">Bedrooms</label>
              <Input
                type="number"
                value={newProp.bedrooms || ''}
                onChange={(e) => setNewProp({ ...newProp, bedrooms: Number(e.target.value) })}
              />
            </div>
          </div>

          {/* Tamil Nadu Revenue Location */}
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

          <div className="border-t border-[var(--color-border-ui)] pt-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-ink-muted)] mb-2">
              Private Owner Information (Strictly Internal)
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-[var(--color-ink)] mb-1">Owner Name</label>
                <Input
                  value={newProp.owner_name || ''}
                  onChange={(e) => setNewProp({ ...newProp, owner_name: e.target.value })}
                  placeholder="K. Subramanian"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-ink)] mb-1">Owner Contact Phone</label>
                <Input
                  value={newProp.owner_phone || ''}
                  onChange={(e) => setNewProp({ ...newProp, owner_phone: e.target.value })}
                  placeholder="+91 94440 00000"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-[var(--color-border-ui)]">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createLoading}>
              Save Property
            </Button>
          </div>
        </form>
      </Modal>

      {/* TNGIS Property & Land Records Search Modal */}
      <TngisSearchModal
        isOpen={isTngisModalOpen}
        onClose={() => setIsTngisModalOpen(false)}
        onSaved={() => {
          fetchProperties();
        }}
      />
    </div>
  );
}
