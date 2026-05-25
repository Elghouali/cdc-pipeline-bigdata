import { cn } from '@/lib/utils';
import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'ghost' | 'danger' | 'outline';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary:
    'border-0 bg-gradient-to-r from-cyan-500 to-purple-600 text-white shadow-[0_4px_20px_rgba(0,229,255,0.25)] hover:from-cyan-400 hover:to-purple-500 hover:shadow-[0_6px_28px_rgba(0,229,255,0.35)]',
  outline:
    'border border-[--border] text-[--text-secondary] hover:border-cyan-500/40 hover:bg-white/[0.03] hover:text-[--text-primary]',
  ghost:
    'text-[--text-secondary] hover:bg-white/[0.04] hover:text-[--text-primary]',
  danger:
    'border border-red-500/40 bg-red-500/15 text-red-300 hover:border-red-400/60 hover:bg-red-500/25',
};

const sizeStyles: Record<Size, string> = {
  sm: 'px-3 py-1 text-xs',
  md: 'px-4 py-1.5 text-sm',
  lg: 'px-5 py-2.5 text-base',
};

export function Button({
  variant = 'primary',
  size = 'md',
  isLoading,
  disabled,
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || isLoading}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-semibold tracking-tight transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-[--bg-base] disabled:pointer-events-none disabled:opacity-50',
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
    >
      {isLoading && (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}
