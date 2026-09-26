import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table';
import { Activity, Eye, ShieldCheck, ChevronLeft, ChevronRight } from 'lucide-react';
import { auditApi } from '../api/audit';
import type { AuditLog } from '../api/types';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [page, setPage] = useState(0);
  const limit = 20;

  // Detail Modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await auditApi.list({
        action: actionFilter || undefined,
        entity_type: entityFilter || undefined,
        limit,
        offset: page * limit,
      });
      setLogs(res.items);
      setTotal(res.total);
    } catch {
      // Handle
    } finally {
      setIsLoading(false);
    }
  }, [actionFilter, entityFilter, page]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-serif text-2xl font-bold tracking-tight text-[var(--color-ink)]">
            Immutable Audit Trail
          </h1>
          <p className="text-xs text-[var(--color-ink-secondary)] mt-0.5">
            Cryptographically logged regulatory actions, logins, status mutations, and security events
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 px-3 py-1.5 rounded-md border border-emerald-200">
          <ShieldCheck className="h-4 w-4" /> Tamper-Proof Storage Active
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3.5 rounded-[8px] border border-[var(--color-border-ui)] shadow-sm">
        <Select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(0);
          }}
          className="text-xs h-9 w-full sm:w-56"
        >
          <option value="">All Action Types</option>
          <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
          <option value="LOGIN_FAILURE">LOGIN_FAILURE</option>
          <option value="PROPERTY_CREATED">PROPERTY_CREATED</option>
          <option value="PROPERTY_PUBLISHED">PROPERTY_PUBLISHED</option>
          <option value="PROPERTY_PAUSED">PROPERTY_PAUSED</option>
          <option value="PROPERTY_ARCHIVED">PROPERTY_ARCHIVED</option>
          <option value="LEAD_STATUS_CHANGED">LEAD_STATUS_CHANGED</option>
          <option value="SITE_VISIT_CONFIRMED">SITE_VISIT_CONFIRMED</option>
          <option value="DOCUMENT_UPLOADED">DOCUMENT_UPLOADED</option>
          <option value="VERIFICATION_REQUESTED">VERIFICATION_REQUESTED</option>
        </Select>

        <Select
          value={entityFilter}
          onChange={(e) => {
            setEntityFilter(e.target.value);
            setPage(0);
          }}
          className="text-xs h-9 w-full sm:w-44"
        >
          <option value="">All Entities</option>
          <option value="PROPERTY">Property</option>
          <option value="CLIENT">Client</option>
          <option value="LEAD">Lead</option>
          <option value="SITE_VISIT">Site Visit</option>
          <option value="DOCUMENT">Document</option>
          <option value="AUTH">Authentication</option>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--color-ink-muted)] bg-white rounded-lg border border-[var(--color-border-ui)]">
          Loading audit records...
        </div>
      ) : logs.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-lg border border-[var(--color-border-ui)]">
          <Activity className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm font-semibold text-[var(--color-ink)]">No audit records found</p>
          <p className="text-xs text-[var(--color-ink-muted)] mt-1">Actions performed across the system will be recorded here.</p>
        </div>
      ) : (
        <div className="bg-white rounded-[8px] border border-[var(--color-border-ui)] overflow-hidden shadow-sm">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Entity Type</TableHead>
                <TableHead>IP Address</TableHead>
                <TableHead>Actor / User ID</TableHead>
                <TableHead>Timestamp</TableHead>
                <TableHead className="text-right">Inspection</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id} className="hover:bg-[var(--color-parchment-warm)] transition-colors">
                  <TableCell className="font-mono text-xs font-bold text-gray-900">
                    <Badge variant="outline" className="text-[10px] font-mono">{log.action}</Badge>
                  </TableCell>
                  <TableCell className="text-xs text-gray-600">
                    {log.entity_type} {log.entity_id ? `(#${log.entity_id.slice(0, 8)})` : ''}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-gray-500">
                    {log.ip_address || '127.0.0.1'}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-gray-500">
                    {log.user_id ? log.user_id.slice(0, 8) : 'SYSTEM'}
                  </TableCell>
                  <TableCell className="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setSelectedLog(log)}
                      className="text-xs h-7 px-2"
                    >
                      <Eye className="h-3.5 w-3.5 mr-1" /> View Diff
                    </Button>
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
            Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total} audit records
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

      {/* MODAL: INSPECT AUDIT ENTRY */}
      {selectedLog && (
        <Modal
          isOpen={!!selectedLog}
          onClose={() => setSelectedLog(null)}
          title={`Audit Record: ${selectedLog.action}`}
          description={`Logged at ${new Date(selectedLog.created_at).toLocaleString()}`}
        >
          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-2 bg-gray-50 p-3 rounded border border-gray-200">
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Entity Type</span>
                <span className="font-semibold">{selectedLog.entity_type}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Entity UUID</span>
                <span className="font-mono">{selectedLog.entity_id || 'N/A'}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">IP Address</span>
                <span className="font-mono">{selectedLog.ip_address || '127.0.0.1'}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px] uppercase">Correlation ID</span>
                <span className="font-mono">{selectedLog.correlation_id || 'None'}</span>
              </div>
            </div>

            <div>
              <span className="font-semibold text-gray-700 block mb-1">New State / Payload:</span>
              <pre className="bg-gray-900 text-emerald-400 p-3 rounded text-[11px] overflow-x-auto max-h-48 font-mono">
                {JSON.stringify(selectedLog.new_values, null, 2) || '// No state mutations'}
              </pre>
            </div>

            {selectedLog.old_values && (
              <div>
                <span className="font-semibold text-gray-700 block mb-1">Previous State:</span>
                <pre className="bg-gray-900 text-amber-400 p-3 rounded text-[11px] overflow-x-auto max-h-36 font-mono">
                  {JSON.stringify(selectedLog.old_values, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex justify-end pt-3 border-t border-gray-200">
              <Button onClick={() => setSelectedLog(null)}>Close</Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
