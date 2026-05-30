import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type Variant = 'success' | 'error' | 'warning' | 'info' | 'muted' | 'purple' | 'orange' | 'bronze';

const VARIANTS: Record<Variant, string> = {
  success: 'bg-green-50  text-green-700  border-green-200',
  error:   'bg-red-50    text-red-700    border-red-200',
  warning: 'bg-amber-50  text-amber-700  border-amber-200',
  info:    'bg-blue-50   text-blue-700   border-blue-200',
  muted:   'bg-stone-100 text-stone-600  border-stone-200',
  purple:  'bg-violet-50 text-violet-700 border-violet-200',
  orange:  'bg-orange-50 text-orange-700 border-orange-200',
  bronze:  'bg-amber-50  text-amber-800  border-amber-200',
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
