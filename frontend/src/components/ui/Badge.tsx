import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';

const badgeVariants = cva(
  'inline-flex items-center rounded-[4px] border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--color-forest)] focus:ring-offset-2',
  {
    variants: {
      variant: {
        default:
          'border-transparent bg-[var(--color-forest)] text-white hover:bg-[var(--color-forest-dark)]',
        secondary:
          'border-transparent bg-[var(--color-parchment)] text-[var(--color-ink)] hover:bg-[var(--color-border-ui)]',
        outline: 'text-[var(--color-ink)] border-[var(--color-border-ui)]',
        success:
          'border-transparent bg-[var(--color-success-subtle)] text-[var(--color-success)]',
        warning:
          'border-transparent bg-[var(--color-warning-subtle)] text-[var(--color-warning)]',
        danger:
          'border-transparent bg-[var(--color-danger-subtle)] text-[var(--color-danger)]',
        info:
          'border-transparent bg-[var(--color-info-subtle)] text-[var(--color-info)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
