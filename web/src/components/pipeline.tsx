import { ChevronRight } from 'lucide-react';
import { pipeline } from '@/lib/site';

/**
 * The restoration pipeline, rendered as a horizontal chain on wide screens and
 * a vertical list on narrow ones. Static markup — no animation, no client JS.
 */
export function PipelineDiagram({ detailed = false }: { detailed?: boolean }) {
  return (
    <ol className="grid gap-3 lg:grid-cols-[repeat(5,1fr)] lg:gap-0">
      {pipeline.map((step, i) => (
        <li key={step.id} className="relative flex items-stretch">
          <div className="flex w-full flex-col rounded-xl2 border border-line bg-card p-4 transition-colors hover:border-linehi lg:rounded-none lg:border-r-0 lg:first:rounded-l-xl2 lg:last:rounded-r-xl2 lg:last:border-r">
            <span className="font-mono text-[11px] text-accent">/{step.id}</span>
            <span className="mt-2 text-sm font-medium leading-snug text-ink">{step.name}</span>
            {detailed ? (
              <span className="mt-2 text-[13px] leading-relaxed text-faint">{step.detail}</span>
            ) : null}
          </div>
          {i < pipeline.length - 1 ? (
            <ChevronRight
              size={14}
              aria-hidden
              className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 rotate-90 text-faint lg:bottom-auto lg:left-auto lg:right-0 lg:top-1/2 lg:-translate-y-1/2 lg:translate-x-1/2 lg:rotate-0"
            />
          ) : null}
        </li>
      ))}
    </ol>
  );
}
