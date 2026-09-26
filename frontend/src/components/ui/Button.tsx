import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';
import { Loader2 } from 'lucide-react';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-[6px] text-sm font-medium transition-default focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-forest)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default:
          'bg-[var(--color-forest)] text-white hover:bg-[var(--color-forest-dark)]',
        secondary:
          'bg-white text-[var(--color-forest)] border border-[var(--color-border-ui)] hover:bg-[var(--color-parchment)]',
        ghost: 'hover:bg-[var(--color-forest-8)] text-[var(--color-forest)]',
        danger:
          'bg-[var(--color-danger)] text-white hover:bg-[#8A3131]',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 rounded-[6px] px-3 text-xs',
        lg: 'h-12 rounded-[8px] px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, children, disabled, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
