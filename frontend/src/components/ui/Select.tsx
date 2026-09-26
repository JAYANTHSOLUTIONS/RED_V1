import * as React from 'react';
import { cn } from '../../utils/cn';
import { ChevronDown } from 'lucide-react';

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: boolean;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, error, children, ...props }, ref) => {
    return (
      <div className="relative w-full">
        <select
          className={cn(
            'flex h-10 w-full appearance-none rounded-[6px] border border-[var(--color-border-ui)] bg-white px-3 py-2 pr-8 text-sm text-[var(--color-ink)] transition-default focus-visible:outline-none focus-visible:border-[var(--color-forest)] focus-visible:ring-1 focus-visible:ring-[var(--color-forest)] disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-[var(--color-danger)] focus-visible:border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]',
            className
          )}
          ref={ref}
          {...props}
        >
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-ink-muted)]" />
      </div>
    );
  }
);
Select.displayName = 'Select';
