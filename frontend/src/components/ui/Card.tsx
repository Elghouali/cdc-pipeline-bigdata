import { cn } from '@/lib/utils';
import type { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'inset';
}

export function Card({ variant = 'default', className, children, ...rest }: CardProps) {
  return (
    <div
      {...rest}
      className={cn(
        'rounded-lg border p-5',
        variant === 'default' && 'border-[--border] bg-[--bg-surface]',
        variant === 'glass'   && 'border-[--border] bg-[--bg-elevated]',
        variant === 'inset'   && 'border-[--border-subtle] bg-[--bg-base]',
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('mb-3 flex items-center justify-between', className)} {...rest}>
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3 className={cn('text-[11px] font-semibold uppercase tracking-[0.08em] text-[--text-muted]', className)} {...rest}>
      {children}
    </h3>
  );
}
