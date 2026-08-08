import type { Metadata } from 'next';
import Link from 'next/link';
import { Callout, Code, H2, Prose, Pre, Ul } from '@/components/ui';
import { site } from '@/lib/site';

export const metadata: Metadata = {
  title: 'Troubleshooting',
  description:
    'Fixes for kernel image errors, incomplete setup, missing FFmpeg, NVENC option rejections, model download failures and interrupted jobs.',
};

export default function TroubleshootingPage() {
  return (
    <>
      <p className="kicker mb-4">Documentation</p>
      <h1 className="text-3xl font-semibold tracking-tight">Troubleshooting</h1>
      <p className="lede mt-4 max-w-2xl">
        The problems that actually occur, what causes them, and how to fix each one.
      </p>

      <Prose>
        <H2 id="kernel">GPU detected, but &quot;no kernel image is available&quot;</H2>
        <p>
          The most confusing failure on newer cards. CUDA reports itself available, models load,
          and then the first real operation fails.
        </p>
        <p>
          <strong className="text-ink">Cause.</strong> Your PyTorch build has no compiled kernels
          for your GPU architecture. An RTX 50-series card reports <Code>sm_120</Code>, and
          builds against CUDA 12.1 or older only carry kernels up to <Code>sm_90</Code>.{' '}
          <Code>torch.cuda.is_available()</Code> is not a sufficient check.
        </p>
        <p>
          <strong className="text-ink">Fix.</strong> Reinstall PyTorch from the CUDA 12.8 index:
        </p>
        <Pre>{`.\\venv\\Scripts\\python.exe -m pip uninstall -y torch torchvision
.\\venv\\Scripts\\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128`}</Pre>
        <p>
          Then press Check setup. You want the line confirming the build carries kernels for
          your architecture.
        </p>

        <H2 id="setup-incomplete">Setup says it is incomplete, or the app stays locked</H2>
        <p>
          <strong className="text-ink">Cause.</strong> Setup did not reach verification. Most
          often the 2.5 GB PyTorch download was interrupted. A virtual environment folder exists
          after step 3 of 8, so its presence does not mean the install finished — the
          application deliberately gates on the <Code>.setup_ok</Code> marker, which is written
          only after verification passes.
        </p>
        <p>
          <strong className="text-ink">Fix.</strong> Press Install / Repair again. Setup resumes:
          it reuses a working environment, skips weights already downloaded, and retries the
          download. Nothing is wasted.
        </p>
        <p>
          If it fails repeatedly, the Activity log names the step that failed. Common causes are
          a missing Python 3.11, a proxy blocking the wheel index, or no space on the install
          drive.
        </p>

        <H2 id="ffmpeg">FFmpeg not found</H2>
        <p>
          <strong className="text-ink">Cause.</strong> FFmpeg is not on PATH, or the window was
          opened before installation.
        </p>
        <Pre>{`winget install Gyan.FFmpeg`}</Pre>
        <p>
          Then close every terminal and the application, and start again so the updated PATH is
          picked up. Verify with <Code>ffmpeg -version</Code>.
        </p>

        <H2 id="nvenc">NVENC rejects the encoder options</H2>
        <p>
          <strong className="text-ink">Cause.</strong> Driver and FFmpeg combinations vary in
          which tuning flags they accept — multi-pass, temporal AQ and B-frame pyramids are the
          usual culprits.
        </p>
        <p>
          <strong className="text-ink">Handled automatically.</strong> Before a long run starts,
          the exact encoder command is tested against a two-frame dummy encode. If it is
          rejected, the engine falls back through progressively simpler option sets and finally
          to CPU <Code>libx265</Code>, logging which tier it settled on. Discovering this six
          hours into a run would be considerably worse.
        </p>
        <p>
          If it falls back to CPU, encoding becomes the bottleneck. Update your NVIDIA driver
          and reinstall a full FFmpeg build.
        </p>

        <H2 id="models">Model download failed</H2>
        <p>
          <strong className="text-ink">Cause.</strong> Interrupted download, or a proxy returning
          an error page instead of the file.
        </p>
        <p>
          <strong className="text-ink">Fix.</strong> Press Install / Repair. Each weight file is
          size-checked; anything truncated is deleted and fetched again rather than failing
          later with an obscure error. To force a clean re-download, delete the file under{' '}
          <Code>models\\</Code> and repeat.
        </p>

        <H2 id="oom">Out of memory during processing</H2>
        <p>
          <strong className="text-ink">Handled automatically.</strong> The engine probes
          full-frame first, then falls back through 768, 640, 512, 384 and 256-pixel tiles, and
          re-tiles mid-run if another application takes VRAM. Tiles are feathered, so no seam
          grid appears.
        </p>
        <p>
          If it still fails, close other GPU applications — browsers with hardware acceleration
          are frequently the cause — or choose a smaller output scale.
        </p>

        <H2 id="disk">Not enough disk space</H2>
        <p>
          <strong className="text-ink">Cause.</strong> Scratch chunks accumulate until the final
          join. A 41-minute job needs roughly 10-15 GB at 2× and 30-40 GB at 4×.
        </p>
        <p>
          <strong className="text-ink">Fix.</strong> Use{' '}
          <strong className="text-ink">Change scratch folder</strong> on the Environment page to
          point at a roomier drive. Free space is shown before a run starts. If a run already
          failed part way, the completed chunks remain valid and the job resumes after you free
          space.
        </p>

        <H2 id="interrupted">An interrupted job will not resume</H2>
        <Ul>
          <li>
            Resume requires identical settings. Changing scale, quality or denoise strength
            deliberately invalidates existing chunks rather than splicing mismatched video
            together.
          </li>
          <li>
            The scratch folder must be the same one. If you changed it, point it back.
          </li>
          <li>
            To start over cleanly, delete the scratch folder. This discards all completed
            chunks.
          </li>
        </Ul>

        <H2 id="window">The window will not open</H2>
        <p>
          If <Code>START_HERE.bat</Code> reports that Python with tkinter was not found,
          reinstall Python 3.11 with <strong className="text-ink">tcl/tk and IDLE</strong>{' '}
          selected. If the window closes with no message at all, run{' '}
          <Code>py -3.11 gui.py</Code> from a terminal in the project folder to see the error.
        </p>

        <H2 id="flicker">Output shimmers or boils in flat areas</H2>
        <p>
          Temporal instability from single-image models. Confirm temporal pre-denoise is enabled
          (it is by default), and consider raising denoise strength slightly. See the{' '}
          <Link href="/docs/quality-guide" className="link">quality guide</Link>.
        </p>

        <H2 id="playback">The finished file stutters during playback</H2>
        <p>
          Usually the file is fine and the player is struggling — 5120×2880 10-bit HEVC is
          demanding. Try a 2× output, or a player with hardware decoding such as mpv or VLC.
        </p>

        <Callout tone="note" title="Still stuck?">
          <p>
            Open an issue with the contents of the Activity log, your GPU model, the output of
            Check setup, and the source video&apos;s resolution and duration. Do not attach the
            video itself.
          </p>
          <p>
            <a href={site.issues} className="link" target="_blank" rel="noopener noreferrer">
              Report a problem on GitHub
            </a>
          </p>
        </Callout>
      </Prose>
    </>
  );
}
