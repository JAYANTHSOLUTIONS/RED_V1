import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import {
  Bell,
  Check,
  RotateCcw,
  MessageSquare,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { notificationsApi } from '../api/notifications';
import { useNotifications } from '../context/NotificationContext';
import type { NotificationItem } from '../api/types';

export default function NotificationsPage() {
  const { refreshNotifications } = useNotifications();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [readFilter, setReadFilter] = useState<'all' | 'unread' | 'read'>('all');
  const [page, setPage] = useState(0);
  const limit = 15;

  // WhatsApp generator modal
  const [isWhatsAppModalOpen, setIsWhatsAppModalOpen] = useState(false);
  const [waPhone, setWaPhone] = useState('+91');
  const [waMessage, setWaMessage] = useState('Hello from RED Tamil Nadu Real Estate Consultancy.');
  const [generatedLink, setGeneratedLink] = useState('');
  const [waLoading, setWaLoading] = useState(false);

  const fetchList = useCallback(async () => {
    setIsLoading(true);
    try {
      const isReadParam = readFilter === 'all' ? undefined : readFilter === 'read';
      const res = await notificationsApi.list({
        is_read: isReadParam,
        limit,
        offset: page * limit,
      });
      setNotifications(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [readFilter, page]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markAsRead(id);
      fetchList();
      refreshNotifications();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleMarkUnread = async (id: string) => {
    try {
      await notificationsApi.markAsUnread(id);
      fetchList();
      refreshNotifications();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    }
  };

  const handleGenerateWhatsApp = async (e: React.FormEvent) => {
    e.preventDefault();
    setWaLoading(true);
    try {
      const res = await notificationsApi.generateWhatsAppLink({
        phone: waPhone,
        message: waMessage,
      });
      setGeneratedLink(res.whatsapp_url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Link generation failed');
    } finally {
      setWaLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Consultant Notification Feed
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Operational alerts, site visit requests, follow-up deadlines & document notifications
          </p>
        </div>
        <Button
          onClick={() => {
            setGeneratedLink('');
            setIsWhatsAppModalOpen(true);
          }}
          className="shrink-0 flex items-center gap-1.5"
        >
          <MessageSquare className="h-4 w-4" /> WhatsApp Link Creator
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border-ui)] pb-1 text-xs">
        {[
          { label: 'All Alerts', value: 'all' },
          { label: 'Unread Only', value: 'unread' },
          { label: 'Read Archive', value: 'read' },
        ].map((tab) => (
          <button
            key={tab.value}
            onClick={() => {
              setReadFilter(tab.value as any);
              setPage(0);
            }}
            className={`px-3 py-2 font-medium rounded-t-md transition-colors whitespace-nowrap ${
              readFilter === tab.value
                ? 'border-b-2 border-[var(--color-gold)] text-[var(--color-forest)] font-bold bg-amber-50/50'
                : 'text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading notifications...
        </div>
      ) : notifications.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <Bell className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No notifications</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">You are all caught up!</p>
        </div>
      ) : (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Notification</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Event Category</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Action</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {notifications.map((n) => (
                <TableRow key={n.id} className={n.is_read ? 'hover:bg-gray-50' : 'bg-amber-50/30 hover:bg-amber-50/50'}>
                  <TableCell className="text-xs max-w-[320px]">
                    <p className="font-semibold text-gray-900">{n.title}</p>
                    <p className="text-gray-600 line-clamp-2 mt-0.5">{n.message}</p>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">{n.channel}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="neutral" className="text-[10px]">{n.notification_type}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(n.created_at).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </TableCell>
                  <TableCell>
                    <Badge variant={n.is_read ? 'secondary' : 'warning'}>
                      {n.is_read ? 'Read' : 'Unread'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    {n.is_read ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleMarkUnread(n.id)}
                        className="text-[11px] h-7 px-2 text-gray-500"
                        title="Mark as unread"
                      >
                        <RotateCcw className="h-3 w-3 mr-1" /> Unread
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleMarkRead(n.id)}
                        className="text-[11px] h-7 px-2 text-emerald-700 hover:bg-emerald-50 border-emerald-300"
                        title="Mark as read"
                      >
                        <Check className="h-3 w-3 mr-1" /> Mark Read
                      </Button>
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
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} alerts
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

      {/* MODAL: WHATSAPP DEEP LINK */}
      <Modal
        isOpen={isWhatsAppModalOpen}
        onClose={() => setIsWhatsAppModalOpen(false)}
        title="WhatsApp Direct Communication Link"
        description="Generates compliant https://wa.me deep-links for immediate client messaging."
      >
        <form onSubmit={handleGenerateWhatsApp} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Phone Number (with Country Code)</label>
            <Input
              required
              placeholder="+91 98400 12345"
              value={waPhone}
              onChange={(e) => setWaPhone(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 mb-1">Message Content</label>
            <Input
              required
              value={waMessage}
              onChange={(e) => setWaMessage(e.target.value)}
            />
          </div>

          {generatedLink && (
            <div className="p-3 bg-emerald-50 rounded border border-emerald-200 text-xs">
              <span className="font-semibold text-emerald-900 block mb-1">Generated Link:</span>
              <a
                href={generatedLink}
                target="_blank"
                rel="noreferrer"
                className="text-emerald-700 underline break-all flex items-center gap-1 font-mono"
              >
                {generatedLink} <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-3 border-t border-gray-200">
            <Button type="button" variant="outline" onClick={() => setIsWhatsAppModalOpen(false)}>
              Close
            </Button>
            <Button type="submit" isLoading={waLoading}>
              Generate Link
            </Button>
            {generatedLink && (
              <Button
                type="button"
                className="bg-emerald-700 hover:bg-emerald-800 text-white"
                onClick={() => window.open(generatedLink, '_blank')}
              >
                Open in WhatsApp
              </Button>
            )}
          </div>
        </form>
      </Modal>
    </div>
  );
}
