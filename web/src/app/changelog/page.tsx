import type { Metadata } from 'next';
import { Badge, PageHeader, Section } from '@/components/ui';
import { site } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Changelog',
  description: 'Release history for RestoreForge AI.',
};

const releases = [
  {
    version: '0.1.0',
    date: 'Unreleased',
    tone: 'accent' as const,
    summary:
      'First public preview. The pipeline, desktop application, test suites and documentation site.',
    groups: [
      {
        title: 'Restoration engine',
        items: [
          'Streaming pipeline: FFmpeg decode, temporal stabilization, SCUNet denoise, Real-ESRGAN 4x, optional downscale, NVENC HEVC encode.',
          'Frames stream through pipes instead of being spooled as PNG sequences, cutting scratch usage from hundreds of GB to roughly the size of the output.',
          'Resumable 1,500-frame chunks, each an independently playable MP4, joined at the end by stream copy with the original audio muxed in.',
          'Variable frame rate sources converted to constant frame rate at the measured average so no real frame is dropped.',
          'Source colour range detected and preserved; forcing limited range on a full-range source measurably darkens the picture.',
          'Feathered tile blending, verified to reconstruct the input to floating-point exactness at every tile size.',
          'Bit-identical duplicate frames produced by VFR conversion are detected and their result reused.',
          'NVENC options validated with a two-frame dummy encode before a long run, falling back through four option tiers and finally to CPU encoding.',
          'Clean stop via a sentinel file so the chunk in flight is finalised and the resume point stays frame-exact.',
        ],
      },
      {
        title: 'Desktop application',
        items: [
          'Dark technical interface with sidebar navigation, readiness panel and live stat cards.',
          'Environment probe reporting GPU, VRAM, compute capability, PyTorch and CUDA versions, model presence and FFmpeg availability.',
          'Estimate time measures 120 frames on the local machine and projects the full runtime.',
          'Live progress: percentage, current chunk, elapsed, remaining, throughput and projected finish time.',
          'Configurable scratch and output folders with free-space reporting; settings persist locally.',
          'Tooltips on advanced settings, keyboard-accessible controls and a visible focus ring.',
        ],
      },
      {
        title: 'Setup and verification',
        items: [
          'Resumable eight-step installer that reuses a good environment and retries interrupted downloads.',
          'Model weights size-checked, so a truncated download is re-fetched rather than failing later.',
          'Setup completion gated on a verification marker rather than the mere existence of a virtual environment.',
          'GPU verification checks compiled kernel architectures rather than trusting a CUDA availability flag.',
        ],
      },
      {
        title: 'Quality and tooling',
        items: [
          'Pipeline test suite: 30 checks including frame-exact chunk seams, pixel-identical resume and safe stop.',
          'Interface test suite: 54 checks covering construction, rendering, log parsing and command building without a display.',
          'Test doubles model real tkinter internals and PyTorch inference-tensor semantics, so permissive stubs cannot hide real failures.',
          'Documentation website with workflow explanation, quality guide, troubleshooting and a client-side planning estimator.',
        ],
      },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <>
      <PageHeader
        kicker="History"
        title="Changelog"
        lede="Notable changes to RestoreForge AI. This project follows semantic versioning once it reaches 1.0."
      />
      <Section>
        <div className="space-y-12">
          {releases.map((r) => (
            <article key={r.version}>
              <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="font-mono text-xl font-semibold text-ink">v{r.version}</h2>
                <Badge tone={r.tone}>{r.date}</Badge>
              </div>
              <p className="mb-6 max-w-2xl text-sm leading-relaxed text-sub">{r.summary}</p>
              <div className="space-y-6">
                {r.groups.map((g) => (
                  <div key={g.title} className="card p-5">
                    <h3 className="mb-3 font-mono text-[11px] uppercase tracking-[0.15em] text-accent">
                      {g.title}
                    </h3>
                    <ul className="list-disc space-y-2 pl-5 text-[13px] leading-relaxed text-sub marker:text-faint">
                      {g.items.map((i) => (
                        <li key={i}>{i}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
        <p className="mt-10 text-sm text-faint">
          Full commit history is available{' '}
          <a href={site.repo} className="link" target="_blank" rel="noopener noreferrer">
            on GitHub
          </a>
          .
        </p>
      </Section>
    </>
  );
}
