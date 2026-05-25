import { cn } from '@/lib/utils';
import type { HTMLAttributes } from 'react';

type Variant = 'default' | 'glass' | 'gradient';
type Glow = 'cyan' | 'emerald' | 'purple' | 'none';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: Variant;
  glow?: Glow;
  interactive?: boolean;
}

export function Card({
  variant = 'default',
  glow = 'none',
  interactive = false,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      {...rest}
      className={cn(
        'relative rounded-xl p-4',
        variant === 'default' &&
          'border border-[--border] bg-[--bg-surface] shadow-[0_4px_32px_rgba(0,0,0,0.5),inset_0_1px_0_rgba(255,255,255,0.03)]',
        variant === 'glass' &&
          'border border-white/[0.06] bg-[--bg-glass] backdrop-blur-xl shadow-[0_8px_40px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.04)]',
        variant === 'gradient' &&
          'border border-[--border] bg-[--bg-surface] shadow-[--shadow-card]',
        glow === 'cyan' && 'shadow-[--glow-cyan]',
        glow === 'emerald' && 'shadow-[--glow-emerald]',
        glow === 'purple' && 'shadow-[--glow-purple]',
        interactive &&
          'cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-[--border-focus] hover:shadow-[0_8px_40px_rgba(0,229,255,0.10)]',
        className,
      )}
    >
      {variant === 'gradient' && (
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px rounded-t-xl bg-gradient-to-r from-transparent via-cyan-400/80 to-purple-500/60" />
      )}
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
      className={cn(
        'text-[10px] font-semibold uppercase tracking-[0.18em] text-[--text-muted]',
        className,
      )}
      {...rest}
    >
      {children}
    </h3>
  );
}
