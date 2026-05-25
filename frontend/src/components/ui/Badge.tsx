import { cn } from '@/lib/utils';
import type { ReactNode } from 'react';

type Variant = 'success' | 'error' | 'warning' | 'info' | 'muted' | 'purple' | 'orange' | 'bronze';

const VARIANTS: Record<Variant, string> = {
  success: 'bg-[#1a2e1f] text-[#3FB950] border-[#2d5a35]',
  error:   'bg-[#2e1a1a] text-[#F85149] border-[#5a2d2d]',
  warning: 'bg-[#2e2510] text-[#D29922] border-[#5a4a20]',
  info:    'bg-[#0d2230] text-[#00D4FF] border-[#1a4060]',
  muted:   'bg-[--bg-elevated] text-[--text-muted] border-[--border]',
  purple:  'bg-[#2a1a3e] text-[#BC8CFF] border-[#4a2d70]',
  orange:  'bg-[#2e1e0a] text-[#FFA657] border-[#5a3a14]',
  bronze:  'bg-[#2a1e10] text-[#B08050] border-[#4a3820]',
};

export function Badge({ variant = 'muted', children, className }: {
  variant?: Variant;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em]',
      VARIANTS[variant],
      className,
    )}>
      {children}
    </span>
  );
}
