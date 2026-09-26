import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { Input } from '../components/ui/Input';
import {
  ChevronLeft,
  MapPin,
  Building,
  ShieldCheck,
  Calendar,
  Clock,
  CheckCircle,
} from 'lucide-react';
import { publicPropertiesApi } from '../api/publicProperties';
import { siteVisitsApi } from '../api/siteVisits';
import type { Property } from '../api/types';

export default function PublicPropertyDetailPage() {
  const { ref } = useParams<{ ref: string }>();

  const [property, setProperty] = useState<Property | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Request visit modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [clientId, setClientId] = useState('');
  const [visitDate, setVisitDate] = useState(new Date(Date.now() + 86400000).toISOString().slice(0, 16));
  const [notes, setNotes] = useState('');
  const [requestLoading, setRequestLoading] = useState(false);
  const [requestSuccess, setRequestSuccess] = useState(false);

  const loadProperty = useCallback(async () => {
    if (!ref) return;
    setIsLoading(true);
    try {
      const data = await publicPropertiesApi.get(ref);
      setProperty(data);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [ref]);

  useEffect(() => {
    loadProperty();
  }, [loadProperty]);

  const handleRequestVisit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!property || !clientId) return;
    setRequestLoading(true);
    try {
      await siteVisitsApi.requestPublicVisit({
        property_id: property.id,
        client_id: clientId,
        scheduled_at: new Date(visitDate).toISOString(),
        notes,
      });
      setRequestSuccess(true);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Visit request failed');
    } finally {
      setRequestLoading(false);
    }
  };

  const formatPrice = (price: number) => {
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  if (isLoading) {
    return <div className="p-16 text-center text-xs text-gray-500">Loading public property...</div>;
  }

  if (!property) {
    return (
      <div className="p-16 text-center">
        <p className="text-sm font-semibold text-gray-800">Property not found</p>
        <Link to="/public/properties" className="text-xs text-[var(--color-primary)] hover:underline mt-2 inline-block">
          Return to directory
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-parchment-warm)] pb-16">
      {/* Public Topbar */}
      <header className="sticky top-0 z-50 bg-white border-b border-[var(--color-border-ui)] px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <Link to="/public/properties" className="flex items-center text-xs text-gray-600 hover:text-gray-900">
            <ChevronLeft className="h-4 w-4 mr-1" /> Back to Listings
          </Link>
          <span className="text-gray-300">|</span>
          <span className="font-mono text-xs font-bold text-gray-900">{property.public_reference}</span>
        </div>
        <Link to="/login">
          <Button size="sm" variant="outline" className="text-xs">
            Consultant Portal
          </Button>
        </Link>
      </header>

      <div className="max-w-6xl mx-auto px-6 pt-8 space-y-8">
        {/* Images presentation */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 rounded-lg overflow-hidden border border-[var(--color-border-ui)] bg-white p-2 shadow-sm">
          <div className="md:col-span-2 h-80 sm:h-96 rounded overflow-hidden">
            {property.images && property.images[0] ? (
              <img src={property.images[0].storage_key} alt={property.title} className="h-full w-full object-cover" />
            ) : (
              <div className="h-full w-full flex items-center justify-center font-serif text-3xl text-gray-300">RED</div>
            )}
          </div>
          <div className="hidden md:flex flex-col gap-2 h-96">
            {property.images && property.images.slice(1, 3).map((img, i) => (
              <div key={i} className="flex-1 rounded overflow-hidden">
                <img src={img.storage_key} alt="" className="h-full w-full object-cover" />
              </div>
            ))}
            {(!property.images || property.images.length <= 1) && (
              <div className="h-full rounded bg-gray-50 flex items-center justify-center text-xs text-gray-400">
                Exterior Architecture
              </div>
            )}
          </div>
        </div>

        {/* Header Details */}
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6 bg-white p-6 rounded-lg border border-[var(--color-border-ui)] shadow-sm">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{property.property_type}</Badge>
              <Badge variant="outline">For {property.transaction_type}</Badge>
              <span className="font-mono text-xs text-gray-400">{property.public_reference}</span>
            </div>
            <h1 className="font-serif text-3xl font-bold text-[var(--color-ink)] leading-tight">
              {property.title}
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-xs text-gray-600">
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-gray-400" />
                {property.locality}, {property.city}
              </span>
              <span className="flex items-center gap-1">
                <Building className="h-3.5 w-3.5 text-gray-400" />
                {property.bedrooms ? `${property.bedrooms} BHK` : 'Plot'} • {property.built_up_area || property.plot_area || 0} sq.ft
              </span>
              <span className="flex items-center gap-1 text-emerald-700 font-semibold">
                <ShieldCheck className="h-3.5 w-3.5" /> Preliminary Legal Verified
              </span>
            </div>
            <p className="text-xs text-gray-700 leading-relaxed pt-2">
              {property.description || 'Premium real estate listing located in prime Tamil Nadu corridor. Full land records, approval credentials and legal chain reviewed.'}
            </p>
          </div>

          <div className="shrink-0 bg-[var(--color-parchment-warm)] p-6 rounded-lg border border-[var(--color-border-ui)] text-right lg:min-w-[240px]">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
              {property.transaction_type === 'SALE' ? 'Price' : 'Monthly Rent'}
            </span>
            <div className="font-serif text-3xl font-bold text-[var(--color-forest)] mt-1">
              {formatPrice(property.price)}
            </div>
            <Button
              onClick={() => {
                setRequestSuccess(false);
                setIsModalOpen(true);
              }}
              className="w-full mt-4 text-xs flex items-center justify-center gap-1.5"
            >
              <Calendar className="h-4 w-4" /> Request Site Inspection
            </Button>
          </div>
        </div>

        {/* Specifications */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-xs uppercase tracking-wider text-gray-600">Specifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Built-up Area</span>
                <span className="font-medium text-gray-900">{property.built_up_area || '-'} sq.ft</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Plot Area</span>
                <span className="font-medium text-gray-900">{property.plot_area || '-'} sq.ft</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Bedrooms</span>
                <span className="font-medium text-gray-900">{property.bedrooms || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Bathrooms</span>
                <span className="font-medium text-gray-900">{property.bathrooms || '-'}</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-xs uppercase tracking-wider text-gray-600">Location</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">District</span>
                <span className="font-medium text-gray-900">{property.district}</span>
              </div>
              <div className="flex justify-between border-b border-gray-100 pb-2">
                <span className="text-gray-500">Locality</span>
                <span className="font-medium text-gray-900">{property.locality}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">City / Pincode</span>
                <span className="font-medium text-gray-900">{property.city} - {property.pincode}</span>
              </div>
              {property.google_maps_url && (
                <div className="pt-2 border-t border-gray-100">
                  <a
                    href={property.google_maps_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center w-full gap-1.5 px-3 py-1.5 rounded text-xs font-semibold text-white bg-[var(--color-forest)] hover:opacity-90 transition-opacity shadow-sm"
                  >
                    <MapPin className="h-3.5 w-3.5 text-amber-300" /> View on Google Maps ↗
                  </a>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* MODAL: REQUEST SITE VISIT */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Request Property Site Visit"
        description={`Submit your visit request for ${property.public_reference}. A consultant will confirm schedule.`}
      >
        {requestSuccess ? (
          <div className="text-center py-6 space-y-3">
            <CheckCircle className="h-12 w-12 text-emerald-600 mx-auto" />
            <h3 className="font-bold text-sm text-gray-900">Visit Request Submitted!</h3>
            <p className="text-xs text-gray-600">
              Your visit request in status REQUESTED has been sent to our consulting team. We will review and confirm your slot.
            </p>
            <Button onClick={() => setIsModalOpen(false)} className="mt-2 text-xs">
              Done
            </Button>
          </div>
        ) : (
          <form onSubmit={handleRequestVisit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Your Registered Client ID</label>
              <Input
                required
                placeholder="Enter client UUID"
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Preferred Inspection Date & Time</label>
              <Input
                type="datetime-local"
                required
                value={visitDate}
                onChange={(e) => setVisitDate(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Special Timing Notes</label>
              <Input
                placeholder="e.g. Please arrange visit during daylight hours"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={requestLoading}>
                Submit Request
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
