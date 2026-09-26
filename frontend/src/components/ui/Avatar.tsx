import * as React from 'react';
import { cn } from '../../utils/cn';
import { User } from 'lucide-react';

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  fallback?: string;
}

export function Avatar({ className, src, alt, fallback, ...props }: AvatarProps) {
  const [imageError, setImageError] = React.useState(false);

  return (
    <div
      className={cn(
        'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full bg-[var(--color-parchment)]',
        className
      )}
      {...props}
    >
      {src && !imageError ? (
        <img
          src={src}
          alt={alt || 'Avatar'}
          className="aspect-square h-full w-full object-cover"
          onError={() => setImageError(true)}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-[var(--color-ink-muted)] bg-[var(--color-forest-8)]">
          {fallback ? (
            <span className="text-sm font-medium uppercase">{fallback}</span>
          ) : (
            <User className="h-5 w-5" />
          )}
        </div>
      )}
    </div>
  );
}
