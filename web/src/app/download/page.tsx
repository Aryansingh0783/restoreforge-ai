import type { Metadata } from 'next';
import Link from 'next/link';
import { AlertTriangle, BookOpen, Github, Terminal } from 'lucide-react';
import { Btn, Callout, Card, PageHeader, Pre, Section, SectionHead, SpecTable } from '@/components/ui';
import { GITHUB_REPO, REPO_CONFIGURED, site } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Download',
  description:
    'How to get RestoreForge AI, install the prerequisites and run your first restoration on Windows.',
};

export default function DownloadPage() {
  return (
    <>
      <PageHeader
        kicker="Get the app"
        title="Download for Windows"
        lede="RestoreForge AI is distributed as source. Setup builds the environment and fetches model weights on first run, so the download itself stays small."
      />

      <Section>
        {!REPO_CONFIGURED ? (
          <Callout tone="warn" title="Repository not yet published">
            <p>
              This site is configured with placeholder repository details. The maintainer needs
              to set <code className="font-mono text-ink">GITHUB_OWNER</code> and{' '}
              <code className="font-mono text-ink">GITHUB_REPO</code> in{' '}
              <code className="font-mono text-ink">web/src/lib/site.ts</code>, after which every
              link below resolves to the real repository and its releases.
            </p>
            <p>
              Until then, use the source you already have locally and follow the{' '}
              <Link href="/docs/getting-started" className="link">getting started guide</Link>.
            </p>
          </Callout>
        ) : null}

        <div className="mt-6 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          <Card className="p-6">
            <h2 className="text-lg font-medium text-ink">Option 1 — clone with Git</h2>
            <p className="mt-2 text-sm leading-relaxed text-sub">
              Recommended. Makes updating a single command later.
            </p>
            <div className="mt-4">
              <Pre>{`git clone ${site.repo}.git
cd ${GITHUB_REPO}`}</Pre>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-sub">
              Then double-click <code className="font-mono text-accent">START_HERE.bat</code>.
            </p>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-medium text-ink">Option 2 — download an archive</h2>
            <p className="mt-2 text-sm leading-relaxed text-sub">
              No Git required. Grab the latest source archive from the releases page, extract it
              somewhere with room to work, and run{' '}
              <code className="font-mono text-accent">START_HERE.bat</code>.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Btn href={site.releases} external variant="primary">
                <Github size={16} aria-hidden /> Releases page
              </Btn>
              <Btn href={site.repo} external>
                <Terminal size={16} aria-hidden /> Browse the source
              </Btn>
            </div>
          </Card>
        </div>
      </Section>

      <Section className="bg-panel">
        <SectionHead
          index="01"
          title="Before you install"
          lede="Two prerequisites must be present. Everything else is installed for you."
        />
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <div>
            <Pre>{`winget install Python.Python.3.11
winget install Gyan.FFmpeg`}</Pre>
            <p className="mt-4 text-sm leading-relaxed text-sub">
              Keep <strong className="text-ink">tcl/tk and IDLE</strong> ticked when installing
              Python. Open a new terminal afterwards so PATH updates are visible.
            </p>
          </div>
          <SpecTable
            rows={[
              ['Operating system', 'Windows 10 or 11, 64-bit'],
              ['GPU', 'NVIDIA with CUDA support'],
              ['Python', '3.11 with tkinter'],
              ['FFmpeg', 'On PATH'],
              ['First-run download', '~2.5 GB PyTorch + 144 MB weights'],
              ['Install footprint', '~5 GB'],
            ]}
          />
        </div>
      </Section>

      <Section>
        <SectionHead index="02" title="What you get" />
        <div className="grid gap-4 md:grid-cols-3">
          {[
            ['Desktop application', 'A tkinter interface for choosing a source, estimating runtime, testing, and running resumable restorations.'],
            ['Restoration engine', 'The full pipeline as a command-line tool, usable independently of the interface.'],
            ['Test suites', 'Two suites that run without a GPU, covering the pipeline and the interface.'],
          ].map(([t, b]) => (
            <Card key={t} className="p-5">
              <h3 className="text-sm font-medium text-ink">{t}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-faint">{b}</p>
            </Card>
          ))}
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-2">
          <Callout tone="warn" title="Windows and NVIDIA only">
            <p>
              The pipeline requires CUDA for inference and NVENC for hardware encoding. AMD,
              Intel Arc, Apple Silicon and CPU-only machines are not supported. Check the{' '}
              <Link href="/requirements" className="link">requirements</Link> first.
            </p>
          </Callout>
          <Callout tone="note" title="No installer, by design">
            <p>
              There is no signed .exe or MSI. The application is Python source you can read, and
              the setup step is a PowerShell script that shows exactly what it installs. That is
              a deliberate trade of convenience for transparency.
            </p>
          </Callout>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <Btn href="/docs/getting-started" variant="primary">
            <BookOpen size={16} aria-hidden /> Getting started guide
          </Btn>
          <Btn href="/docs/troubleshooting">
            <AlertTriangle size={16} aria-hidden /> Troubleshooting
          </Btn>
        </div>
      </Section>
    </>
  );
}
