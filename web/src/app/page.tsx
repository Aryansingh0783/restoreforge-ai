import Link from 'next/link';
import {
  ArrowRight,
  AudioLines,
  BookOpen,
  Cpu,
  FlaskConical,
  Github,
  Grid2x2,
  HardDrive,
  MonitorDown,
  Palette,
  RotateCcw,
  ShieldCheck,
  Zap,
} from 'lucide-react';
import { Badge, Btn, Card, Section, SectionHead, SpecTable } from '@/components/ui';
import { PipelineDiagram } from '@/components/pipeline';
import { Estimator } from '@/components/estimator';
import { faqs, features, site } from '@/lib/site';

const ICONS = {
  RotateCcw,
  AudioLines,
  Palette,
  Grid2x2,
  Cpu,
  FlaskConical,
} as const;

export default function HomePage() {
  return (
    <>
      {/* ------------------------------------------------------------- hero */}
      <section className="gridwash relative overflow-hidden border-b border-line">
        <div className="glow pointer-events-none absolute inset-0" aria-hidden />
        <div className="relative mx-auto w-full max-w-content px-5 py-20 sm:px-8 sm:py-28">
          <Badge tone="accent">
            <ShieldCheck size={12} aria-hidden /> 100% local processing
          </Badge>

          <h1 className="mt-6 max-w-4xl text-pretty text-4xl font-semibold leading-[1.08] tracking-tight sm:text-6xl">
            RestoreForge AI
          </h1>
          <p className="mt-4 max-w-2xl text-pretty text-xl text-sub sm:text-2xl">
            Local AI video restoration for Windows.
          </p>
          <p className="lede mt-5 max-w-2xl">
            Denoise and upscale noisy, low-quality footage on your own NVIDIA GPU.{' '}
            <strong className="font-medium text-ink">
              Your video never leaves your computer
            </strong>{' '}
            — there is no upload, no queue, no account, and no cloud subscription.
          </p>

          <div className="mt-9 flex flex-wrap gap-3">
            <Btn href="/download" variant="primary">
              <MonitorDown size={16} aria-hidden /> Download for Windows
            </Btn>
            <Btn href={site.repo} external>
              <Github size={16} aria-hidden /> View on GitHub
            </Btn>
            <Btn href="/docs">
              <BookOpen size={16} aria-hidden /> Read the docs
            </Btn>
          </div>

          <dl className="mt-14 grid max-w-3xl grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
            {[
              ['Pipeline stages', '5'],
              ['Chunk size', '1,500 frames'],
              ['Upload size', '0 bytes'],
              ['License', 'MIT'],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="kicker">{k}</dt>
                <dd className="mt-1.5 font-mono text-lg text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {/* --------------------------------------------------------- pipeline */}
      <Section>
        <SectionHead
          index="01"
          title="The restoration pipeline"
          lede="Five stages, all on your machine. Frames stream between them through pipes rather than being written out as image sequences, which keeps a long job to gigabytes of scratch space instead of hundreds."
        />
        <PipelineDiagram />
        <p className="mt-6 text-sm text-faint">
          <Link href="/workflow" className="link">
            See what each stage does and why
          </Link>
        </p>
      </Section>

      {/* ------------------------------------------------------------- why */}
      <Section className="bg-panel">
        <SectionHead
          index="02"
          title="Why local?"
          lede="Restoration is a long, heavy, private job. Sending it to someone else's computer makes all three of those worse."
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: ShieldCheck,
              title: 'Privacy by architecture',
              body: 'Home videos, interviews, medical or legal footage. Nothing is transmitted, so nothing can leak, be retained, or be used for training.',
            },
            {
              icon: Zap,
              title: 'No upload queue',
              body: 'A 1.3 GB source would take longer to upload on many connections than to start processing locally. Work begins the moment you press start.',
            },
            {
              icon: Cpu,
              title: 'Your GPU, full speed',
              body: 'Direct CUDA and NVENC access with no shared tenancy, no rate limits, and no per-minute billing meter running.',
            },
            {
              icon: HardDrive,
              title: 'No subscription',
              body: 'Open source under MIT. Run it as often as you like on as much footage as you like, offline.',
            },
          ].map((f) => (
            <Card key={f.title} hover className="p-5">
              <f.icon size={18} aria-hidden className="text-accent" />
              <h3 className="mt-3.5 text-sm font-medium text-ink">{f.title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-faint">{f.body}</p>
            </Card>
          ))}
        </div>
      </Section>

      {/* -------------------------------------------------------- features */}
      <Section>
        <SectionHead
          index="03"
          title="Built for long, interruptible jobs"
          lede="A restoration can run for hours. The engine is designed around that reality rather than pretending it is instant."
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => {
            const Icon = ICONS[f.icon as keyof typeof ICONS];
            return (
              <Card key={f.title} hover className="p-5">
                <Icon size={18} aria-hidden className="text-accent" />
                <h3 className="mt-3.5 text-sm font-medium text-ink">{f.title}</h3>
                <p className="mt-2 text-[13px] leading-relaxed text-faint">{f.body}</p>
              </Card>
            );
          })}
        </div>
        <p className="mt-6 text-sm text-faint">
          <Link href="/features" className="link">
            Full feature breakdown
          </Link>
        </p>
      </Section>

      {/* ------------------------------------------------------- estimator */}
      <Section className="bg-panel" id="estimator">
        <SectionHead
          index="04"
          title="Plan a run before you start one"
          lede="Type in the shape of your source to get a rough sense of the time, disk and chunk count involved. This runs entirely in your browser — no file is read, nothing is uploaded."
        />
        <Estimator />
      </Section>

      {/* ---------------------------------------------------------- expect */}
      <Section>
        <SectionHead
          index="05"
          title="What to expect"
          lede="Restoration software attracts overpromising. Here is the honest version."
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-ok/25 bg-ok/[0.04] p-6">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.15em] text-ok">
              What it does well
            </p>
            <ul className="space-y-2.5 text-sm leading-relaxed text-sub">
              <li>Removes sensor and compression noise that makes footage tiring to watch.</li>
              <li>Produces a visibly cleaner, sharper, more watchable picture.</li>
              <li>Keeps the original audio and frame timing intact.</li>
              <li>Survives interruption without losing meaningful work.</li>
            </ul>
          </Card>
          <Card className="border-warn/25 bg-warn/[0.04] p-6">
            <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.15em] text-warn">
              What it cannot do
            </p>
            <ul className="space-y-2.5 text-sm leading-relaxed text-sub">
              <li>
                Recover detail that was never recorded. Upscalers invent plausible detail; they
                do not retrieve lost truth.
              </li>
              <li>
                Guarantee faces or text come back correctly. Invented detail is where artifacts
                live — always check a short test clip.
              </li>
              <li>
                Make every damaged source pristine. Severe damage may stay visible or be
                emphasised.
              </li>
              <li>
                Run quickly. Expect hours, not minutes, and never real time.
              </li>
            </ul>
          </Card>
        </div>
        <Card className="mt-4 border-accent/25 bg-accent/[0.05] p-6">
          <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.15em] text-accent">
            Recommended default
          </p>
          <p className="max-w-3xl text-sm leading-relaxed text-sub">
            For low-quality 720p footage, use <strong className="text-ink">2×</strong>. Both
            settings run the AI at 4×; 2× then downsamples the result. That supersampling
            averages away invented detail, usually producing a cleaner picture than native 4× at
            a quarter of the file size and with far better playback compatibility. 4× remains
            available when the source genuinely warrants it.
          </p>
        </Card>
      </Section>

      {/* ------------------------------------------------------------ specs */}
      <Section className="bg-panel">
        <SectionHead
          index="06"
          title="System requirements"
          lede="Windows and NVIDIA only. This is a hard architectural constraint, not a roadmap item."
        />
        <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <SpecTable
            rows={[
              ['Operating system', 'Windows 10 or 11 (64-bit)'],
              ['GPU', 'NVIDIA with CUDA support'],
              ['Reference GPU', 'RTX 5070, 12 GB, Blackwell sm_120'],
              ['Python', '3.11 with tkinter'],
              ['FFmpeg', 'On PATH, NVENC build recommended'],
              ['Disk', '~5 GB install + scratch space per job'],
            ]}
          />
          <div className="space-y-4">
            <Card className="p-5">
              <h3 className="text-sm font-medium text-ink">Not supported</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-faint">
                AMD and Intel Arc GPUs, Apple Silicon, Linux, and CPU-only machines. The pipeline
                depends on CUDA for inference and NVENC for encoding.
              </p>
            </Card>
            <Card className="p-5">
              <h3 className="text-sm font-medium text-ink">Verified before you start</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-faint">
                Setup checks that your PyTorch build actually carries kernels for your GPU
                architecture — not merely that CUDA reports itself available, which is a
                misleading signal on newer cards.
              </p>
            </Card>
            <Btn href="/requirements">
              Full requirements <ArrowRight size={15} aria-hidden />
            </Btn>
          </div>
        </div>
      </Section>

      {/* -------------------------------------------------------- how it works */}
      <Section>
        <SectionHead
          index="07"
          title="How it works"
          lede="Five steps from a fresh install to a finished file."
        />
        <ol className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {[
            ['Install', 'Double-click START_HERE.bat. Setup builds the environment and downloads model weights — resumable if the download drops.'],
            ['Verify', 'Check setup confirms your GPU, CUDA kernels, both models and the NVENC encoder actually work.'],
            ['Estimate', 'Measures 120 frames on your machine and projects the real duration of the full job.'],
            ['Test', 'Renders 30 seconds so you can judge the quality before committing hours.'],
            ['Restore', 'Runs in resumable chunks with live progress. Stop and resume whenever you like.'],
          ].map(([title, body], i) => (
            <li key={title} className="card p-5">
              <span className="font-mono text-[11px] text-accent">
                /{String(i + 1).padStart(2, '0')}
              </span>
              <h3 className="mt-2 text-sm font-medium text-ink">{title}</h3>
              <p className="mt-2 text-[13px] leading-relaxed text-faint">{body}</p>
            </li>
          ))}
        </ol>
      </Section>

      {/* -------------------------------------------------------------- faq */}
      <Section className="bg-panel" id="faq">
        <SectionHead index="08" title="Frequently asked questions" />
        <div className="max-w-3xl divide-y divide-line border-y border-line">
          {faqs.map((f) => (
            <details key={f.q} className="group py-4">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-4 text-[15px] font-medium text-ink marker:content-none">
                {f.q}
                <span
                  aria-hidden
                  className="mt-1 shrink-0 font-mono text-faint transition-transform group-open:rotate-45"
                >
                  +
                </span>
              </summary>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">{f.a}</p>
            </details>
          ))}
        </div>
      </Section>

      {/* -------------------------------------------------------------- cta */}
      <Section>
        <div className="card gridwash relative overflow-hidden p-10 text-center sm:p-16">
          <div className="glow pointer-events-none absolute inset-0" aria-hidden />
          <div className="relative">
            <h2 className="text-pretty text-2xl font-semibold tracking-tight sm:text-4xl">
              Restore your footage without giving it away
            </h2>
            <p className="lede mx-auto mt-4 max-w-xl">
              Free, open source, and built to run entirely on hardware you already own.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Btn href="/download" variant="primary">
                <MonitorDown size={16} aria-hidden /> Download for Windows
              </Btn>
              <Btn href="/docs/getting-started">
                <BookOpen size={16} aria-hidden /> Getting started guide
              </Btn>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}
