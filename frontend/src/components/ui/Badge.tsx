import { cn } from '@/lib/utils';

type Variant = 'success' | 'error' | 'warning' | 'info' | 'muted' | 'purple';

interface BadgeProps {
  variant?: Variant;
  children: React.ReactNode;
  className?: string;
}

const variantStyles: Record<Variant, string> = {
  success: 'bg-emerald-400/10 text-emerald-400 ring-emerald-400/20',
  error:   'bg-red-400/10 text-red-400 ring-red-400/20',
  warning: 'bg-amber-400/10 text-amber-400 ring-amber-400/20',
  info:    'bg-cyan-400/10 text-cyan-400 ring-cyan-400/20',
  muted:   'bg-slate-700/40 text-slate-400 ring-slate-700/40',
  purple:  'bg-purple-400/10 text-purple-400 ring-purple-400/20',
};

export function Badge({ variant = 'muted', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        variantStyles[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
