import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, BookOpen, LifeBuoy, Sparkles } from 'lucide-react';
import { Callout } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Documentation',
  description:
    'Installation, first run, quality guidance and troubleshooting for RestoreForge AI.',
};

const cards = [
  { href: '/docs/getting-started', icon: BookOpen, title: 'Getting started',
    body: 'Install the prerequisites, run setup, verify your GPU and complete a first test restoration.' },
  { href: '/docs/quality-guide', icon: Sparkles, title: 'Quality guide',
    body: '2x versus 4x, denoise strength, encoder quality, and a realistic account of what AI upscaling can and cannot do.' },
  { href: '/docs/troubleshooting', icon: LifeBuoy, title: 'Troubleshooting',
    body: 'Kernel image errors, incomplete setup, missing FFmpeg, NVENC rejections, failed model downloads and interrupted jobs.' },
];

export default function DocsPage() {
  return (
    <>
      <p className="kicker mb-4">Documentation</p>
      <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
        Everything you need to run it
      </h1>
      <p className="lede mt-4 max-w-2xl">
        RestoreForge AI is a Windows desktop application. These pages cover installation, the
        first run, choosing settings, and fixing the problems that actually come up.
      </p>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {cards.map((c) => (
          <Link key={c.href} href={c.href} className="card card-hover group block p-5">
            <c.icon size={18} aria-hidden className="text-accent" />
            <h2 className="mt-3.5 flex items-center gap-1.5 text-sm font-medium text-ink">
              {c.title}
              <ArrowRight
                size={14}
                aria-hidden
                className="opacity-0 transition-opacity group-hover:opacity-100"
              />
            </h2>
            <p className="mt-2 text-[13px] leading-relaxed text-faint">{c.body}</p>
          </Link>
        ))}
      </div>

      <div className="mt-10 space-y-4">
        <Callout tone="note" title="Support disclaimer">
          <p>
            This is open-source software provided as is. There is no guarantee that any
            particular damaged source can be made pristine — AI restoration improves footage,
            it does not reconstruct information that was never captured. Results vary
            considerably with the nature and severity of the original damage.
          </p>
          <p>
            A full end-to-end restoration of a feature-length source has not yet been completed
            and published. The pipeline, resume behaviour and encoder validation are covered by
            automated tests, and every stage has run against real footage.
          </p>
        </Callout>
        <Callout tone="ok" title="Privacy">
          <p>
            All processing happens on your computer. No video, metadata or usage information is
            transmitted anywhere. See the{' '}
            <Link href="/privacy" className="link">privacy statement</Link>.
          </p>
        </Callout>
      </div>
    </>
  );
}
