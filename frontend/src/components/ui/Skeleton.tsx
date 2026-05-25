import { cn } from '@/lib/utils';

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn('skeleton-shimmer rounded', className)} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-[--border] bg-[--bg-surface] p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-7 w-7 rounded-md" />
          <Skeleton className="h-4 w-24 rounded" />
        </div>
        <Skeleton className="h-5 w-12 rounded-full" />
      </div>
      <Skeleton className="mb-3 h-3 w-44 rounded" />
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-16 rounded" />
          <Skeleton className="h-3 w-12 rounded" />
        </div>
        <Skeleton className="h-1.5 w-full rounded-full" />
      </div>
    </div>
  );
}

export function SkeletonTableRow() {
  const widths = ['w-32', 'w-16', 'w-full', 'w-20', 'w-10'];
  return (
    <tr className="border-b border-[--border]">
      {widths.map((w, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className={cn('h-3 rounded', w)} />
        </td>
      ))}
    </tr>
  );
}
