import * as React from 'react';
import { cn } from '../../utils/cn';
import { X } from 'lucide-react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

export function Modal({ isOpen, onClose, title, description, children, footer, className }: ModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-[#1C2422]/40 transition-opacity" 
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Modal Dialog */}
      <div 
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative z-50 w-full max-w-lg rounded-[8px] bg-white p-6 shadow-lg sm:mx-4 animate-in fade-in zoom-in-95 duration-150',
          className
        )}
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-[4px] p-1 text-[var(--color-ink-muted)] hover:bg-[var(--color-parchment)] hover:text-[var(--color-ink)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-forest)]"
        >
          <X className="h-5 w-5" />
          <span className="sr-only">Close</span>
        </button>

        {title && (
          <div className="mb-4 pr-6">
            <h2 className="text-lg font-semibold text-[var(--color-ink)]">{title}</h2>
            {description && <p className="mt-1 text-sm text-[var(--color-ink-secondary)]">{description}</p>}
          </div>
        )}

        <div className="py-2">{children}</div>

        {footer && <div className="mt-6 flex justify-end space-x-3">{footer}</div>}
      </div>
    </div>
  );
}
