'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Github, Menu, X, ShieldCheck } from 'lucide-react';
import { nav, site } from '@/lib/site';

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-base/85 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-content items-center gap-3 px-5 sm:px-8">
        <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
          <span aria-hidden className="text-accent">
            ◆
          </span>
          <span>RestoreForge</span>
          <span className="hidden font-mono text-[10px] font-normal text-faint sm:inline">
            v{site.version}
          </span>
        </Link>

        <nav aria-label="Main" className="ml-6 hidden items-center gap-1 md:flex">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                isActive(item.href) ? 'text-accent' : 'text-sub hover:text-ink'
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden items-center gap-1.5 font-mono text-[11px] text-faint lg:flex">
            <ShieldCheck size={13} aria-hidden /> runs on your machine
          </span>
          <a
            href={site.repo}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-md p-2 text-sub transition-colors hover:text-ink"
            aria-label="View the project on GitHub"
          >
            <Github size={17} aria-hidden />
          </a>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="rounded-md p-2 text-sub transition-colors hover:text-ink md:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? 'Close menu' : 'Open menu'}
          >
            {open ? <X size={18} aria-hidden /> : <Menu size={18} aria-hidden />}
          </button>
        </div>
      </div>

      {open ? (
        <nav
          id="mobile-nav"
          aria-label="Mobile"
          className="border-t border-line bg-panel md:hidden"
        >
          <div className="mx-auto max-w-content px-5 py-2 sm:px-8">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`block rounded-md px-2 py-2.5 text-sm ${
                  isActive(item.href) ? 'text-accent' : 'text-sub'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
      ) : null}
    </header>
  );
}

export function SiteFooter() {
  const groups = [
    {
      title: 'Product',
      links: [
        { href: '/features', label: 'Features' },
        { href: '/workflow', label: 'Workflow' },
        { href: '/requirements', label: 'Requirements' },
        { href: '/download', label: 'Download' },
      ],
    },
    {
      title: 'Documentation',
      links: [
        { href: '/docs', label: 'Overview' },
        { href: '/docs/getting-started', label: 'Getting started' },
        { href: '/docs/quality-guide', label: 'Quality guide' },
        { href: '/docs/troubleshooting', label: 'Troubleshooting' },
      ],
    },
    {
      title: 'Project',
      links: [
        { href: '/changelog', label: 'Changelog' },
        { href: '/privacy', label: 'Privacy' },
      ],
    },
  ];

  return (
    <footer className="border-t border-line bg-panel">
      <div className="mx-auto grid w-full max-w-content gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <div className="flex items-center gap-2.5 font-semibold tracking-tight">
            <span aria-hidden className="text-accent">
              ◆
            </span>
            RestoreForge AI
          </div>
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-faint">
            Local AI video restoration for Windows. Open source, GPU accelerated, and never
            uploads your footage.
          </p>
        </div>

        {groups.map((g) => (
          <div key={g.title}>
            <p className="kicker mb-3">{g.title}</p>
            <ul className="space-y-2 text-sm">
              {g.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sub transition-colors hover:text-ink">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-line">
        <div className="mx-auto flex w-full max-w-content flex-col gap-2 px-5 py-5 font-mono text-[11px] text-faint sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <span>MIT licensed · no telemetry · no accounts</span>
          <a
            href={site.repo}
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-sub"
          >
            source on github
          </a>
        </div>
      </div>
    </footer>
  );
}
