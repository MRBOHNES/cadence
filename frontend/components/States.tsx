/** Loading, empty and error states. Skeleton blocks are static (no pulsing). */

function Block({ className }: { className: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function DashboardSkeleton() {
  return (
    <div role="status" aria-label="Loading status data" className="flex flex-col gap-[14px]">
      <div className="panel grid grid-cols-2 gap-px bg-line desk:grid-cols-6">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="bg-panel p-3.5">
            <Block className="mb-2 h-[3px] w-6" />
            <Block className="h-3 w-16" />
            <Block className="mt-2 h-9 w-24" />
            <Block className="mt-2 h-3 w-28" />
          </div>
        ))}
      </div>
      <div className="grid gap-[14px] desk:grid-cols-12">
        <div className="grid gap-[14px] desk:col-span-8 desk:grid-cols-2">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="panel p-3">
              <Block className="h-4 w-32" />
              <Block className="mt-2 h-[140px] w-full" />
            </div>
          ))}
        </div>
        <div className="panel p-3 desk:col-span-4">
          <Block className="h-4 w-28" />
          <Block className="mt-3 h-[300px] w-full" />
        </div>
      </div>
      <div className="panel p-3">
        <Block className="h-4 w-56" />
        <Block className="mt-3 h-[200px] w-full" />
      </div>
      <div className="grid grid-cols-2 gap-[14px] desk:grid-cols-5">
        {Array.from({ length: 5 }, (_, i) => (
          <Block key={i} className="h-[150px]" />
        ))}
      </div>
    </div>
  );
}

export function EmptyState() {
  return (
    <section className="panel p-6">
      <p>No checks yet. First results after the next sweep, within 5 minutes.</p>
    </section>
  );
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <section role="alert" className="panel flex flex-col items-start gap-3 p-6">
      <p>Couldn&apos;t reach the status API. It may be waking up, which can take up to a minute.</p>
      <button
        type="button"
        onClick={onRetry}
        className="min-h-[44px] border border-ink bg-hl px-4 font-medium text-[var(--hl-ink)]"
      >
        Try again
      </button>
    </section>
  );
}
