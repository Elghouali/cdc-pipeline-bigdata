import { cn } from '@/lib/utils';
import type { HTMLAttributes } from 'react';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  glow?: 'cyan' | 'emerald' | 'none';
}

export function Card({ glow = 'none', className, children, ...rest }: CardProps) {
  return (
    <div
      {...rest}
      className={cn(
        'rounded-lg border bg-[--bg-surface] p-4',
        'border-[--border]',
        glow === 'cyan' && 'shadow-[--shadow-glow-cyan]',
        glow === 'emerald' && 'shadow-[--shadow-glow-emerald]',
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
    <h3
      className={cn('text-xs font-semibold uppercase tracking-wider text-[--text-secondary]', className)}
      {...rest}
    >
      {children}
    </h3>
  );
}
