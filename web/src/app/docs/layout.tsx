import Link from 'next/link';
import { docsNav } from '@/lib/site';

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-content px-5 sm:px-8">
      <div className="gap-12 lg:grid lg:grid-cols-[210px_1fr]">
        <aside className="hidden py-12 lg:block">
          <nav aria-label="Documentation" className="sticky top-24">
            <p className="kicker mb-3">Documentation</p>
            <ul className="space-y-1 border-l border-line">
              {docsNav.map((d) => (
                <li key={d.href}>
                  <Link
                    href={d.href}
                    className="-ml-px block border-l border-transparent py-1.5 pl-4 text-sm text-sub transition-colors hover:border-linehi hover:text-ink"
                  >
                    {d.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </aside>
        <div className="min-w-0 py-12">{children}</div>
      </div>
    </div>
  );
}
