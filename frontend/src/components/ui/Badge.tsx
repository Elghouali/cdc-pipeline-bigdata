import { cn } from '@/lib/utils';

type Variant = 'success' | 'error' | 'warning' | 'info' | 'muted' | 'purple';

interface BadgeProps {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<Variant, string> = {
  success: 'bg-emerald-400/10 text-emerald-300 ring-emerald-400/30 shadow-[0_0_12px_rgba(16,255,170,0.15)]',
  error:   'bg-red-400/10 text-red-300 ring-red-400/30 shadow-[0_0_12px_rgba(244,63,94,0.15)]',
  warning: 'bg-amber-400/10 text-amber-300 ring-amber-400/30 shadow-[0_0_12px_rgba(251,191,36,0.12)]',
  info:    'bg-cyan-400/10 text-cyan-300 ring-cyan-400/30 shadow-[0_0_12px_rgba(0,229,255,0.18)]',
  muted:   'bg-white/[0.04] text-slate-400 ring-white/[0.08]',
  purple:  'bg-purple-400/10 text-purple-300 ring-purple-400/30 shadow-[0_0_12px_rgba(168,85,247,0.15)]',
};

export function Badge({ variant = 'muted', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider ring-1 ring-inset',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
