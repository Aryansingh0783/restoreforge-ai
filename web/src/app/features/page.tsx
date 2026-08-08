import type { Metadata } from 'next';
import {
  AudioLines, Cpu, FlaskConical, Gauge, Grid2x2, HardDrive, Palette,
  RotateCcw, ShieldCheck, SlidersHorizontal, Timer, Waves,
} from 'lucide-react';
import { Card, PageHeader, Section, SectionHead } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Features',
  description:
    'Resumable chunk processing, feathered tiling, colour-aware handling, original-audio preservation and Blackwell-ready GPU verification.',
};

const groups = [
  {
    index: '01',
    title: 'Reliability under long runs',
    lede: 'A restoration can occupy your machine for most of a day. Everything here exists because that is the normal case, not the exception.',
    items: [
      { icon: RotateCcw, title: 'Resumable chunks',
        body: 'Work splits into 1,500-frame chunks. Each completed chunk is a self-contained, playable MP4, so an interruption costs at most one chunk of progress.' },
      { icon: ShieldCheck, title: 'Safe stop',
        body: 'Stop writes a sentinel file rather than killing the process. The chunk in flight finishes and is finalised properly, keeping the resume point frame-exact.' },
      { icon: Gauge, title: 'Encoder pre-flight',
        body: 'Before a long run begins, the exact NVENC command is tested against a two-frame dummy encode, falling back through simpler option sets and finally to CPU encoding.' },
      { icon: Timer, title: 'Measured estimates',
        body: 'Rather than guessing, the app runs 120 frames on your hardware and projects the real duration, including the wall-clock time it expects to finish.' },
    ],
  },
  {
    index: '02',
    title: 'Image quality decisions',
    lede: 'The defaults are chosen to minimise invented detail and temporal artifacts, which are what actually make AI-restored footage look wrong.',
    items: [
      { icon: Waves, title: 'Temporal pre-denoise',
        body: 'SCUNet and Real-ESRGAN are single-image models. Left alone they denoise each frame slightly differently and flat areas shimmer. A temporal pass settles the noise field first.' },
      { icon: Grid2x2, title: 'Feathered tile blending',
        body: 'When a frame is too large to process whole, tiles are blended with a ramp instead of hard-cut. Tested to reconstruct the input to floating-point exactness at every tile size.' },
      { icon: Palette, title: 'Colour-range awareness',
        body: 'Full-range sources are detected and preserved. Forcing limited range on a full-range source measurably darkens the entire video and shifts every channel.' },
      { icon: SlidersHorizontal, title: 'Adjustable denoise blend',
        body: 'Full-strength denoising can flatten skin and fabric into plastic. The blend is exposed so you can keep fine texture, with 0.85 as a deliberate default.' },
    ],
  },
  {
    index: '03',
    title: 'Faithful output',
    lede: 'What comes out should differ from what went in only in the ways you asked for.',
    items: [
      { icon: AudioLines, title: 'Original audio preserved',
        body: 'The source audio is muxed into the final file by stream copy where the container allows, so it is bit-identical to the original track.' },
      { icon: Cpu, title: 'Variable frame rate handled',
        body: 'VFR sources are converted to constant frame rate at the measured average rather than the nominal header value, so no real frame is silently discarded and audio stays in sync.' },
      { icon: HardDrive, title: 'Streamed, not spooled',
        body: 'Raw frames move between stages through pipes. A 4x job that would need hundreds of GB as PNG sequences needs roughly the size of the finished file instead.' },
      { icon: FlaskConical, title: 'Test-first reliability',
        body: 'Two suites cover the pipeline and the desktop UI without a GPU, including frame-exact chunk seams, pixel-identical resume and encoder option validity.' },
    ],
  },
];

export default function FeaturesPage() {
  return (
    <>
      <PageHeader
        kicker="Product"
        title="Features"
        lede="RestoreForge AI is a focused tool: denoise, upscale, encode, locally, without losing your work when something goes wrong."
      />
      {groups.map((g, gi) => (
        <Section key={g.index} className={gi % 2 ? 'bg-panel' : ''}>
          <SectionHead index={g.index} title={g.title} lede={g.lede} />
          <div className="grid gap-4 md:grid-cols-2">
            {g.items.map((f) => (
              <Card key={f.title} hover className="p-5">
                <f.icon size={18} aria-hidden className="text-accent" />
                <h3 className="mt-3.5 text-sm font-medium text-ink">{f.title}</h3>
                <p className="mt-2 text-[13px] leading-relaxed text-faint">{f.body}</p>
              </Card>
            ))}
          </div>
        </Section>
      ))}
    </>
  );
}
