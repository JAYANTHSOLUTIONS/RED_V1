import * as React from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn';

export interface SpinnerProps extends React.SVGAttributes<SVGSVGElement> {}

export function Spinner({ className, ...props }: SpinnerProps) {
  return (
    <Loader2 className={cn('animate-spin text-[var(--color-forest)]', className)} {...props} />
  );
}
