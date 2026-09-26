import * as React from 'react';
import { cn } from '../../utils/cn';
import { X } from 'lucide-react';

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function Drawer({ isOpen, onClose, title, description, children, footer, className }: DrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-[#1C2422]/40 transition-opacity" 
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Drawer Panel */}
      <div 
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative z-50 flex h-full w-full max-w-md flex-col bg-white shadow-xl animate-in slide-in-from-right duration-200',
          className
        )}
      >
        <div className="flex items-center justify-between border-b border-[var(--color-border-ui)] px-6 py-4">
          <div>
            {title && <h2 className="text-lg font-semibold text-[var(--color-ink)]">{title}</h2>}
            {description && <p className="text-sm text-[var(--color-ink-secondary)]">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-[4px] p-1 text-[var(--color-ink-muted)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-ink)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-forest)]"
          >
            <X className="h-5 w-5" />
            <span className="sr-only">Close</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">{children}</div>

        {footer && (
          <div className="border-t border-[var(--color-border-ui)] p-6 bg-[var(--color-parchment)] flex justify-end space-x-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
