import Link from 'next/link';
import type { ReactNode } from 'react';

/* ------------------------------------------------------------------ layout */

export function Section({
  children,
  className = '',
  id,
}: {
  children: ReactNode;
  className?: string;
  id?: string;
}) {
  return (
    <section id={id} className={`border-t border-line ${className}`}>
      <div className="mx-auto w-full max-w-content px-5 py-16 sm:px-8 sm:py-20">{children}</div>
    </section>
  );
}

export function SectionHead({
  index,
  title,
  lede,
}: {
  index: string;
  title: string;
  lede?: string;
}) {
  return (
    <div className="mb-10 max-w-3xl">
      <div className="mb-3 flex items-center gap-3">
        <span className="font-mono text-[11px] text-accent">/{index}</span>
        <span className="h-px flex-1 bg-line" aria-hidden />
      </div>
      <h2 className="text-pretty text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
      {lede ? <p className="lede mt-3">{lede}</p> : null}
    </div>
  );
}

export function PageHeader({
  kicker,
  title,
  lede,
}: {
  kicker: string;
  title: string;
  lede?: string;
}) {
  return (
    <header className="gridwash border-b border-line">
      <div className="mx-auto w-full max-w-content px-5 py-14 sm:px-8 sm:py-20">
        <p className="kicker mb-4">{kicker}</p>
        <h1 className="text-pretty text-3xl font-semibold tracking-tight sm:text-5xl">{title}</h1>
        {lede ? <p className="lede mt-5 max-w-2xl">{lede}</p> : null}
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------ atoms */

export function Badge({
  children,
  tone = 'neutral',
}: {
  children: ReactNode;
  tone?: 'neutral' | 'accent' | 'ok' | 'warn';
}) {
  const tones = {
    neutral: 'border-line bg-cardhi text-sub',
    accent: 'border-accent/30 bg-accent/10 text-accent',
    ok: 'border-ok/30 bg-ok/10 text-ok',
    warn: 'border-warn/30 bg-warn/10 text-warn',
  } as const;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

type BtnProps = {
  children: ReactNode;
  href: string;
  variant?: 'primary' | 'ghost';
  external?: boolean;
  className?: string;
};

export function Btn({
  children,
  href,
  variant = 'ghost',
  external = false,
  className = '',
}: BtnProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors';
  const styles =
    variant === 'primary'
      ? 'bg-accent text-[#04222a] hover:bg-[#67e8f9]'
      : 'border border-linehi bg-cardhi text-ink hover:border-accent/40 hover:bg-[#1a1f28]';
  const cls = `${base} ${styles} ${className}`;

  if (external) {
    return (
      <a href={href} className={cls} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={cls}>
      {children}
    </Link>
  );
}

export function Card({
  children,
  className = '',
  hover = false,
}: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
}) {
  return <div className={`card ${hover ? 'card-hover' : ''} ${className}`}>{children}</div>;
}

export function Callout({
  tone = 'note',
  title,
  children,
}: {
  tone?: 'note' | 'warn' | 'ok';
  title: string;
  children: ReactNode;
}) {
  const tones = {
    note: 'border-accent/25 bg-accent/[0.06]',
    warn: 'border-warn/25 bg-warn/[0.06]',
    ok: 'border-ok/25 bg-ok/[0.06]',
  } as const;
  const dots = { note: 'text-accent', warn: 'text-warn', ok: 'text-ok' } as const;
  return (
    <div className={`rounded-xl2 border p-5 ${tones[tone]}`}>
      <p className={`mb-2 font-mono text-[11px] uppercase tracking-[0.15em] ${dots[tone]}`}>
        {title}
      </p>
      <div className="space-y-3 text-sm leading-relaxed text-sub">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ prose */

export function Prose({ children }: { children: ReactNode }) {
  return <div className="max-w-3xl space-y-5 text-[15px] leading-relaxed text-sub">{children}</div>;
}

export function H2({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <h2 id={id} className="scroll-mt-24 pt-6 text-xl font-semibold tracking-tight text-ink">
      {children}
    </h2>
  );
}

export function H3({ children, id }: { children: ReactNode; id?: string }) {
  return (
    <h3 id={id} className="scroll-mt-24 pt-2 text-base font-semibold tracking-tight text-ink">
      {children}
    </h3>
  );
}

export function Code({ children }: { children: ReactNode }) {
  return (
    <code className="rounded border border-line bg-cardhi px-1.5 py-0.5 font-mono text-[13px] text-accent">
      {children}
    </code>
  );
}

export function Pre({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto rounded-xl2 border border-line bg-[#07090c] p-4 font-mono text-[12.5px] leading-relaxed text-[#c3ccd8]">
      <code>{children}</code>
    </pre>
  );
}

export function Ul({ children }: { children: ReactNode }) {
  return <ul className="list-disc space-y-2 pl-5 marker:text-faint">{children}</ul>;
}

export function Ol({ children }: { children: ReactNode }) {
  return <ol className="list-decimal space-y-2 pl-5 marker:font-mono marker:text-faint">{children}</ol>;
}

/* ------------------------------------------------------------------ table */

export function SpecTable({ rows }: { rows: readonly (readonly [string, string])[] }) {
  return (
    <div className="overflow-hidden rounded-xl2 border border-line">
      <table className="w-full text-left text-sm">
        <tbody>
          {rows.map(([k, v], i) => (
            <tr key={k} className={i % 2 ? 'bg-card' : 'bg-[#0c0f13]'}>
              <th scope="row" className="w-1/3 border-b border-line px-4 py-3 font-normal text-sub">
                {k}
              </th>
              <td className="border-b border-line px-4 py-3 font-mono text-[13px] text-ink">{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
