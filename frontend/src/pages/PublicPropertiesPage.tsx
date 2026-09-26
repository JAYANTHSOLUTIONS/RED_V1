import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Search, MapPin, Building, ShieldCheck, ArrowRight, Home } from 'lucide-react';
import { publicPropertiesApi } from '../api/publicProperties';
import type { Property } from '../api/types';
import { getTnDistricts } from '../utils/tnLocations';

export default function PublicPropertiesPage() {
  const navigate = useNavigate();

  const [properties, setProperties] = useState<Property[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [district, setDistrict] = useState('');
  const [propType, setPropType] = useState('');
  const [txType, setTxType] = useState('');

  const fetchPublic = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await publicPropertiesApi.list({
        search: search || undefined,
        district: district || undefined,
        property_type: propType || undefined,
        transaction_type: txType || undefined,
        limit: 20,
      });
      setProperties(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [search, district, propType, txType]);

  useEffect(() => {
    fetchPublic();
  }, [fetchPublic]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPublic();
  };

  const formatPrice = (price: number) => {
    if (price >= 10000000) return `₹ ${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹ ${(price / 100000).toFixed(2)} L`;
    return `₹ ${price.toLocaleString('en-IN')}`;
  };

  return (
    <div className="min-h-screen bg-[var(--color-parchment-warm)] text-[var(--color-ink)]">
      {/* Public Header */}
      <header className="sticky top-0 z-50 bg-white border-b border-[var(--color-border-ui)] px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <Link to="/" className="flex items-center">
            <span className="font-serif text-2xl font-bold tracking-tight text-[var(--color-forest)]">RED</span>
            <span className="ml-2 rounded bg-[var(--color-parchment)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--color-ink-secondary)]">
              DISCOVERY
            </span>
          </Link>
          <span className="text-gray-300">|</span>
          <span className="text-xs text-gray-500 hidden sm:inline">Tamil Nadu Verified Property Listings</span>
        </div>

        <div className="flex items-center gap-3">
          <Link to="/login">
            <Button size="sm" variant="outline" className="text-xs">
              Consultant Login
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero Search Section */}
      <div className="bg-[var(--color-forest)] text-white px-6 py-12 md:py-16 text-center">
        <div className="max-w-3xl mx-auto space-y-4">
          <Badge variant="outline" className="text-white border-white/30 text-[11px]">
            TAMIL NADU REAL ESTATE PORTAL
          </Badge>
          <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight">
            Verified Tamil Nadu Properties
          </h1>
          <p className="text-gray-200 text-xs sm:text-sm max-w-xl mx-auto">
            Explore preliminary verified residential & commercial properties with transparent survey boundaries across Chennai, Coimbatore & Madurai.
          </p>

          <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2 max-w-2xl mx-auto pt-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by locality, title, or reference..."
                className="pl-9 bg-white text-gray-900 text-xs h-10"
              />
            </div>
            <Button type="submit" className="bg-[var(--color-gold)] hover:bg-[#9a7b4c] text-white text-xs h-10 px-6 font-semibold">
              Search
            </Button>
          </form>
        </div>
      </div>

      {/* Filters & Results */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4 bg-white p-4 rounded-lg border border-[var(--color-border-ui)] shadow-sm">
          <div className="text-xs font-semibold text-gray-700">
            Available Properties: <span className="text-[var(--color-forest)]">{total} Listings</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={district}
              onChange={(e) => setDistrict(e.target.value)}
              className="text-xs h-8 w-40"
            >
              <option value="">All Districts (38)</option>
              {getTnDistricts().map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </Select>

            <Select
              value={propType}
              onChange={(e) => setPropType(e.target.value)}
              className="text-xs h-8 w-32"
            >
              <option value="">All Types</option>
              <option value="Apartment">Apartment</option>
              <option value="Villa">Villa</option>
              <option value="Plot">Plot</option>
              <option value="Commercial">Commercial</option>
            </Select>

            <Select
              value={txType}
              onChange={(e) => setTxType(e.target.value)}
              className="text-xs h-8 w-32"
            >
              <option value="">All Listings</option>
              <option value="SALE">For Sale</option>
              <option value="RENT">For Rent</option>
              <option value="LEASE">For Lease</option>
            </Select>
          </div>
        </div>

        {/* Listings Grid */}
        {isLoading ? (
          <div className="p-16 text-center text-xs text-gray-500">Discovering published properties...</div>
        ) : properties.length === 0 ? (
          <div className="bg-white p-16 text-center rounded-lg border border-[var(--color-border-ui)]">
            <Home className="h-10 w-10 text-gray-300 mx-auto mb-2" />
            <h3 className="font-semibold text-sm text-gray-800">No properties available</h3>
            <p className="text-xs text-gray-500 mt-1">Try broadening your search filters.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {properties.map((prop) => (
              <div
                key={prop.id}
                onClick={() => navigate(`/public/properties/${prop.public_reference}`)}
                className="group bg-white rounded-lg border border-[var(--color-border-ui)] overflow-hidden shadow-sm hover:shadow-md hover:border-[var(--color-gold)] transition-all cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <div className="relative h-48 bg-gray-100 overflow-hidden">
                    {prop.images && prop.images[0] ? (
                      <img
                        src={prop.images[0].storage_key}
                        alt={prop.title}
                        className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center font-serif text-xl font-bold text-gray-300">
                        RED
                      </div>
                    )}
                    <div className="absolute top-2 left-2">
                      <span className="font-mono text-[10px] bg-black/70 text-white px-2 py-0.5 rounded backdrop-blur-sm">
                        {prop.public_reference}
                      </span>
                    </div>
                    <div className="absolute top-2 right-2">
                      <span className="text-[10px] font-semibold bg-emerald-700 text-white px-2 py-0.5 rounded shadow">
                        For {prop.transaction_type}
                      </span>
                    </div>
                  </div>

                  <div className="p-4 space-y-2">
                    <div className="flex items-center gap-1 text-[11px] text-gray-500">
                      <MapPin className="h-3 w-3 text-gray-400" />
                      <span>{prop.locality}, {prop.city}</span>
                    </div>
                    <h3 className="font-semibold text-sm text-gray-900 group-hover:text-[var(--color-forest)] transition-colors line-clamp-1">
                      {prop.title}
                    </h3>
                    <p className="text-base font-bold text-[var(--color-forest)] pt-1">
                      {formatPrice(prop.price)}
                    </p>
                  </div>
                </div>

                <div className="px-4 py-3 border-t border-gray-100 bg-gray-50 flex items-center justify-between text-xs text-gray-600">
                  <span>
                    {prop.bedrooms ? `${prop.bedrooms} Bedrooms • ` : ''}
                    {prop.built_up_area || prop.plot_area || 0} sq.ft
                  </span>
                  <span className="font-semibold text-[var(--color-primary)] flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                    Inspect <ArrowRight className="h-3 w-3" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
