import type { Metadata } from 'next';
import Link from 'next/link';
import { Callout, Code, H2, H3, Prose, SpecTable, Ul } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Quality guide',
  description:
    'Choosing between 2x and 4x, setting denoise strength and encoder quality, and realistic expectations for AI upscaling artifacts.',
};

export default function QualityGuidePage() {
  return (
    <>
      <p className="kicker mb-4">Documentation</p>
      <h1 className="text-3xl font-semibold tracking-tight">Quality guide</h1>
      <p className="lede mt-4 max-w-2xl">
        Which settings to use, why the defaults are what they are, and what AI restoration can
        honestly achieve on damaged footage.
      </p>

      <Prose>
        <H2 id="scale">2× or 4×</H2>
        <p>
          <strong className="text-ink">Use 2× unless you have a specific reason not to.</strong>{' '}
          This surprises people, so it is worth explaining properly.
        </p>
        <p>
          Both settings run Real-ESRGAN at 4×. Choosing 2× adds a downscale after inference. The
          GPU work is identical, so 2× is not faster — it is a quality and compatibility choice.
        </p>
        <p>
          A 720p webcam capture contains nowhere near 5120×2880 of real detail. At 4×, most of
          those pixels are invented by the model, and invented detail is exactly where artifacts
          live. Rendering at 4× and then supersampling to 1440p averages that invention away,
          which usually produces a picture that is both sharper and cleaner than native 4×.
        </p>
        <SpecTable
          rows={[
            ['2× from a 720p source', '2560 × 1440, ~1/4 the file size, plays everywhere'],
            ['4× from a 720p source', '5120 × 2880, 10-bit HEVC, stutters on many players'],
            ['Processing time', 'Effectively identical'],
            ['Recommended for low-quality footage', '2×'],
            ['Worth trying 4× when', 'The source is already clean and reasonably detailed'],
          ]}
        />
        <Callout tone="note" title="Decide with your own eyes">
          <p>
            Render 30 seconds at each setting and compare them full-screen at 100%. It takes a
            few minutes and settles the question for your specific footage far better than any
            general advice.
          </p>
        </Callout>

        <H2 id="denoise">Denoise strength</H2>
        <p>
          The slider controls how much of the SCUNet result is blended into the frame.{' '}
          <Code>1.00</Code> is full strength; the default is <Code>0.85</Code>.
        </p>
        <Ul>
          <li>
            <strong className="text-ink">0.85 (default)</strong> — removes most noise while
            keeping fine texture such as skin pores and fabric weave.
          </li>
          <li>
            <strong className="text-ink">0.70</strong> — try this if faces look waxy or
            plastic, or if the picture has lost its material quality.
          </li>
          <li>
            <strong className="text-ink">1.00</strong> — for genuinely severe noise where
            texture loss is an acceptable trade.
          </li>
        </Ul>
        <p>
          Full-strength denoising is the most common cause of the flat, artificial look people
          associate with AI restoration. If your result looks synthetic, lower this before
          changing anything else.
        </p>

        <H2 id="flicker">Temporal stability</H2>
        <p>
          SCUNet and Real-ESRGAN are single-image models: they see one frame at a time. Run
          per-frame on noisy video, each frame is denoised slightly differently and flat areas
          shimmer and boil. Over a long clip this is far more objectionable than a little
          softness.
        </p>
        <p>
          A temporal pre-denoise pass settles the noise field between frames before SCUNet sees
          it, so the model makes consistent decisions frame to frame. It is enabled by default
          and is the single highest-value setting in the pipeline. Disable it only if you are
          deliberately investigating its effect.
        </p>

        <H2 id="cq">Encoder quality (cq)</H2>
        <p>
          NVENC constant-quality target. Lower is better quality and a larger file.
        </p>
        <SpecTable
          rows={[
            ['14-16', 'Archival. Large files, no visible loss.'],
            ['17-20', 'Default range. 19 is visually lossless for this material.'],
            ['21-24', 'Noticeably smaller, slight softening in fine detail.'],
            ['25+', 'Visible compression artifacts. Not recommended.'],
          ]}
        />

        <H2 id="colour">Colour handling</H2>
        <p>
          Sources are examined for signal range and the output matches. Many webcams record
          full-range (<Code>yuvj420p</Code>); forcing limited range on such a source measurably
          darkens the entire video. The default of <Code>auto</Code> preserves what the source
          used. Override it only if a specific player misinterprets the result.
        </p>

        <H2 id="expectations">What to expect</H2>
        <H3>Realistic outcomes</H3>
        <Ul>
          <li>Noise that made footage tiring to watch is largely gone.</li>
          <li>Edges are cleaner and the picture is easier to follow.</li>
          <li>The result looks like a better recording — not like different equipment.</li>
        </Ul>
        <H3>Known limitations</H3>
        <Ul>
          <li>
            Detail that was never recorded cannot be recovered. Upscalers synthesise plausible
            detail; they do not retrieve lost information.
          </li>
          <li>
            Faces and text are where invention is most visible. Small or heavily degraded faces
            may come back subtly wrong.
          </li>
          <li>
            Compression blocking, banding and severe motion blur may persist or be emphasised.
          </li>
          <li>
            Interlacing and heavy rolling shutter are not addressed by this pipeline.
          </li>
        </Ul>
        <Callout tone="warn" title="No guarantee">
          <p>
            There is no guarantee that a given damaged source can be made pristine. If a test
            clip does not look meaningfully better, a full run will not either — adjust
            settings, or accept that this particular footage is beyond what these models can do.
          </p>
        </Callout>

        <H2 id="workflow">A sensible workflow</H2>
        <Ul>
          <li>Run Estimate time so you know what you are committing to.</li>
          <li>Render 30 seconds at 2× with the defaults.</li>
          <li>If it looks plastic, lower denoise to 0.70 and re-test.</li>
          <li>If it looks soft and the source is clean, try 4× on the same 30 seconds.</li>
          <li>Choose a section with faces or text for the test, not a static shot.</li>
          <li>Only then start the full run.</li>
        </Ul>
        <p>
          If something goes wrong mid-run, see{' '}
          <Link href="/docs/troubleshooting" className="link">troubleshooting</Link>.
        </p>
      </Prose>
    </>
  );
}
