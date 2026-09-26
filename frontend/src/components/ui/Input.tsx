import * as React from 'react';
import { cn } from '../../utils/cn';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-[6px] border border-[var(--color-border-ui)] bg-white px-3 py-2 text-sm text-[var(--color-ink)] transition-default file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--color-ink-muted)] focus-visible:outline-none focus-visible:border-[var(--color-forest)] focus-visible:ring-1 focus-visible:ring-[var(--color-forest)] disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-[var(--color-danger)] focus-visible:border-[var(--color-danger)] focus-visible:ring-[var(--color-danger)]',
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = 'Input';

export { Input };
