import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Search, Plus, Phone, Mail, ChevronLeft, ChevronRight, User } from 'lucide-react';
import { clientsApi } from '../api/clients';
import type { Client, ClientCreatePayload } from '../api/types';

export default function ClientsPage() {
  const navigate = useNavigate();

  const [clients, setClients] = useState<Client[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [classificationFilter, setClassificationFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 15;

  // Add Client Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [newClient, setNewClient] = useState<ClientCreatePayload>({
    full_name: '',
    phone: '',
    email: '',
    preferred_contact_method: 'CALL',
    classification: 'BUYER',
    source: 'WEBSITE',
    notes: '',
  });

  const fetchClients = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await clientsApi.list({
        search: search || undefined,
        classification: classificationFilter || undefined,
        limit,
        offset: page * limit,
      });
      setClients(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [search, classificationFilter, page]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchClients();
  };

  const handleCreateClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateLoading(true);
    try {
      const created = await clientsApi.create(newClient);
      setIsModalOpen(false);
      setNewClient({
        full_name: '',
        phone: '',
        email: '',
        preferred_contact_method: 'CALL',
        classification: 'BUYER',
        source: 'WEBSITE',
        notes: '',
      });
      fetchClients();
      navigate(`/clients/${created.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to register client');
    } finally {
      setCreateLoading(false);
    }
  };

  const classifications = [
    { label: 'All Clients', value: '' },
    { label: 'Buyers', value: 'BUYER' },
    { label: 'Sellers', value: 'SELLER' },
    { label: 'Tenants', value: 'TENANT' },
    { label: 'Landlords', value: 'LANDLORD' },
    { label: 'Investors', value: 'INVESTOR' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Client Directory
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Buyer, seller, landlord & investor profiles and communication preferences
          </p>
        </div>
        <Button onClick={() => setIsModalOpen(true)} className="shrink-0 flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Add Client Profile
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border-ui)] overflow-x-auto pb-1 text-xs">
        {classifications.map((c) => (
          <button
            key={c.value}
            onClick={() => {
              setClassificationFilter(c.value);
              setPage(0);
            }}
            className={`px-3 py-2 font-medium rounded-t-md transition-colors whitespace-nowrap ${
              classificationFilter === c.value
                ? 'border-b-2 border-[var(--color-gold)] text-[var(--color-forest)] font-bold bg-amber-50/50'
                : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Search Bar */}
      <div className="bg-white p-3.5 rounded-[8px] border border-[var(--color-border-ui)] shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-ink-muted)]" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by client name, phone number, email... (Press Enter)"
              className="pl-9 text-xs h-9"
            />
          </div>
          <Button type="submit" variant="secondary" size="sm" className="shrink-0 text-xs">
            Search
          </Button>
        </form>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading client profiles...
        </div>
      ) : clients.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <User className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No clients found</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Register a client to manage leads and requirements.</p>
          <Button size="sm" onClick={() => setIsModalOpen(true)} className="mt-4">
            Register Client
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client Name</TableHead>
                <TableHead>Classification</TableHead>
                <TableHead>Phone / Contact</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Preferred Channel</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Registered Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {clients.map((client) => (
                <TableRow
                  key={client.id}
                  onClick={() => navigate(`/clients/${client.id}`)}
                  className="cursor-pointer hover:bg-[var(--color-parchment-warm)] transition-colors"
                >
                  <TableCell className="font-semibold text-xs text-[var(--color-ink)]">
                    <div className="flex items-center space-x-2">
                      <div className="h-7 w-7 rounded-full bg-[var(--color-forest)] text-white flex items-center justify-center font-bold text-[10px]">
                        {client.full_name.slice(0, 2).toUpperCase()}
                      </div>
                      <span>{client.full_name}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">{client.classification}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-[var(--color-ink)]">
                    <div className="flex items-center gap-1.5">
                      <Phone className="h-3 w-3 text-gray-400" />
                      {client.phone}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-[var(--color-ink-muted)]">
                    {client.email ? (
                      <div className="flex items-center gap-1.5">
                        <Mail className="h-3 w-3 text-gray-400" />
                        {client.email}
                      </div>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant="neutral" className="text-[10px]">{client.preferred_contact_method}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={client.is_archived ? 'secondary' : 'success'}>
                      {client.is_archived ? 'ARCHIVED' : client.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-[var(--color-ink-muted)]">
                    {new Date(client.created_at).toLocaleDateString()}
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
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} clients
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

      {/* MODAL: ADD CLIENT */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register New Client Profile"
        description="Add client to CRM database with contact methods and classification."
      >
        <form onSubmit={handleCreateClient} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Full Legal Name</label>
            <Input
              required
              placeholder="e.g. S. Meenakshi"
              value={newClient.full_name}
              onChange={(e) => setNewClient({ ...newClient, full_name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Phone Number</label>
              <Input
                required
                placeholder="+91 98401 23456"
                value={newClient.phone}
                onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Email (Optional)</label>
              <Input
                type="email"
                placeholder="meenakshi@gmail.com"
                value={newClient.email || ''}
                onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">Classification</label>
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
              <label className="block text-xs font-semibold text-gray-700 mb-1">Preferred Contact</label>
              <Select
                value={newClient.preferred_contact_method}
                onChange={(e) => setNewClient({ ...newClient, preferred_contact_method: e.target.value as any })}
              >
                <option value="CALL">CALL</option>
                <option value="WHATSAPP">WHATSAPP</option>
                <option value="EMAIL">EMAIL</option>
                <option value="SMS">SMS</option>
              </Select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Internal Notes</label>
            <Input
              placeholder="e.g. Looking for 3 BHK in Adyar / Besant Nagar budget under 2.5 Cr"
              value={newClient.notes || ''}
              onChange={(e) => setNewClient({ ...newClient, notes: e.target.value })}
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={createLoading}>
              Save Client
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
