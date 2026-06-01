import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type Variant = 'success' | 'error' | 'warning' | 'info' | 'muted' | 'purple' | 'orange' | 'bronze';

const VARIANTS: Record<Variant, string> = {
  success: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25',
  error:   'bg-red-500/10     text-red-400     border-red-500/25',
  warning: 'bg-amber-500/10   text-amber-400   border-amber-500/25',
  info:    'bg-blue-500/10    text-blue-400    border-blue-500/25',
  muted:   'bg-white/5        text-[#878787]   border-white/10',
  purple:  'bg-violet-500/10  text-violet-400  border-violet-500/25',
  orange:  'bg-orange-500/10  text-orange-400  border-orange-500/25',
  bronze:  'bg-amber-500/10   text-amber-400   border-amber-500/25',
};

export function Badge({ variant = 'muted', children, className }: {
  variant?: Variant;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
      VARIANTS[variant],
      className,
    )}>
      {children}
    </span>
  );
}
