import type { Metadata } from 'next';
import Link from 'next/link';
import { Callout, PageHeader, Section, SectionHead, SpecTable } from '@/components/ui';
import { PipelineDiagram } from '@/components/pipeline';
import { pipeline } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Workflow',
  description:
    'How the restoration pipeline works: FFmpeg decode, temporal stabilization, SCUNet denoise, Real-ESRGAN upscale and NVENC encode.',
};

export default function WorkflowPage() {
  return (
    <>
      <PageHeader
        kicker="Pipeline"
        title="How a restoration runs"
        lede="Five stages, executed in order on your GPU. Frames stream between them through pipes; nothing is written to disk until the encoder produces a finished chunk."
      />

      <Section>
        <SectionHead index="01" title="The chain" />
        <PipelineDiagram detailed />
      </Section>

      <Section className="bg-panel">
        <SectionHead
          index="02"
          title="Stage by stage"
          lede="Each stage exists to solve a specific failure mode observed in real footage."
        />
        <div className="space-y-4">
          {pipeline.map((s) => (
            <div key={s.id} className="card p-6">
              <div className="flex flex-wrap items-baseline gap-3">
                <span className="font-mono text-[11px] text-accent">/{s.id}</span>
                <h3 className="text-base font-medium text-ink">{s.name}</h3>
              </div>
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-sub">{s.detail}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section>
        <SectionHead
          index="03"
          title="Chunking and resume"
          lede="Long jobs are split so that failure is cheap."
        />
        <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <div className="space-y-4 text-sm leading-relaxed text-sub">
            <p>
              Frames are grouped into chunks of 1,500 — roughly 100 seconds of finished video.
              Each chunk is encoded to its own complete MP4 in the scratch folder, so you can
              open the newest one and judge quality while the run continues.
            </p>
            <p>
              A state file records the exact resume point after every chunk. Starting the job
              again picks up from that frame. When all chunks exist they are concatenated by
              stream copy — no re-encode, no generation loss — and the original audio track is
              muxed in to produce a single output file.
            </p>
            <p>
              Because the state file also fingerprints your settings, changing scale or quality
              invalidates stale chunks rather than silently splicing mismatched video together.
            </p>
          </div>
          <SpecTable
            rows={[
              ['Chunk size', '1,500 frames'],
              ['Chunk container', 'MP4, independently playable'],
              ['Resume granularity', 'One chunk'],
              ['Join method', 'Stream copy (no re-encode)'],
              ['Audio', 'Muxed from the source'],
              ['Cost of a crash', 'At most one chunk'],
            ]}
          />
        </div>
      </Section>

      <Section className="bg-panel">
        <SectionHead index="04" title="Timing and throughput" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Callout tone="note" title="Reference measurement">
            <p>
              On an RTX 5070 at 720p input, SCUNet takes roughly 0.40 s per frame and
              Real-ESRGAN roughly 1.80 s, for about 2.2 s per source frame end to end. A
              41-minute clip is around 37,000 frames, so on the order of a day of GPU time.
            </p>
            <p>
              Your hardware will differ. Use{' '}
              <Link href="/#estimator" className="link">the estimator</Link> for a rough plan and
              the application&apos;s Estimate time button for a real measurement.
            </p>
          </Callout>
          <Callout tone="warn" title="2x is not faster than 4x">
            <p>
              Both settings run the AI at 4x. Choosing 2x adds a downscale after inference, so
              the GPU work is identical and the runtime is effectively the same.
            </p>
            <p>
              2x is recommended for image quality and compatibility, not speed. See the{' '}
              <Link href="/docs/quality-guide" className="link">quality guide</Link>.
            </p>
          </Callout>
        </div>
      </Section>
    </>
  );
}
