import type { Metadata } from 'next';
import Link from 'next/link';
import { Callout, Code, H2, H3, Ol, Pre, Prose, Ul } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Getting started',
  description:
    'Install prerequisites, run setup, verify your GPU and complete a first test restoration with RestoreForge AI.',
};

export default function GettingStartedPage() {
  return (
    <>
      <p className="kicker mb-4">Documentation</p>
      <h1 className="text-3xl font-semibold tracking-tight">Getting started</h1>
      <p className="lede mt-4 max-w-2xl">
        From a clean Windows machine to a finished test clip. Budget about fifteen minutes,
        most of it waiting for a download.
      </p>

      <Prose>
        <H2 id="prerequisites">1. Install the prerequisites</H2>
        <p>Two things must exist before the application can install itself:</p>
        <Pre>{`winget install Python.Python.3.11
winget install Gyan.FFmpeg`}</Pre>
        <Ul>
          <li>
            Keep <strong className="text-ink">tcl/tk and IDLE</strong> selected when installing
            Python. The desktop interface is built on tkinter and will not start without it.
          </li>
          <li>
            Open a <strong className="text-ink">new</strong> terminal or window afterwards so
            the updated PATH is visible.
          </li>
        </Ul>

        <H2 id="download">2. Get the application</H2>
        <p>
          Clone the repository or download the source archive from the{' '}
          <Link href="/download" className="link">download page</Link>, then place the folder
          somewhere with room to work — a drive with tens of gigabytes free is ideal.
        </p>

        <H2 id="setup">3. Run setup</H2>
        <p>
          Double-click <Code>START_HERE.bat</Code>. The application window opens and tells you
          whether the environment is installed. If it is not, press{' '}
          <strong className="text-ink">Install / Repair environment</strong>.
        </p>
        <p>Setup runs eight steps:</p>
        <Ol>
          <li>Locate Python 3.11.</li>
          <li>Create the model folders.</li>
          <li>Create or reuse the virtual environment.</li>
          <li>Install PyTorch from the CUDA 12.8 wheel index (about 2.5 GB).</li>
          <li>Install numpy, einops, tqdm and requests.</li>
          <li>Download the SCUNet and Real-ESRGAN weights, with size verification.</li>
          <li>Confirm FFmpeg and NVENC.</li>
          <li>Run the full verification suite.</li>
        </Ol>
        <Callout tone="note" title="If the download drops">
          <p>
            Setup is resumable. Press Install / Repair again — it reuses a good virtual
            environment, skips weights that are already present, and retries the PyTorch
            download. A truncated weight file is detected by size and re-fetched rather than
            failing later with a confusing error.
          </p>
        </Callout>
        <p>
          Only when step 8 passes does setup write <Code>.setup_ok</Code>. The application gates
          every action on that marker, because the presence of a virtual environment alone
          proves nothing — it exists after step 3 of 8.
        </p>

        <H2 id="verify">4. Check setup</H2>
        <p>
          Press <strong className="text-ink">Check setup</strong> (or F5). You want{' '}
          <Code>ALL CHECKS PASSED</Code>, and in particular the line confirming your GPU
          architecture has matching kernels. The Environment page shows the same information as
          a readiness list.
        </p>
        <Pre>{`1. PyTorch and CUDA
  [ok]   torch 2.11.0+cu128  (CUDA 12.8)
  [ok]   NVIDIA GeForce RTX 5070  13 GB  compute sm_120
  [ok]   this build has sm_120 kernels
2. Executing a real CUDA kernel
  [ok]   fp16 matmul on GPU succeeded
3. SCUNet denoiser
  [ok]   loaded strictly, ran 720p -> 1280x720
4. Real-ESRGAN x4
  [ok]   loaded strictly, ran 720p -> 5120x2880
5. ffmpeg and NVENC
  [ok]   hevc_nvenc encoded a test frame`}</Pre>

        <H2 id="first-run">5. Your first restoration</H2>
        <Ol>
          <li>Choose a source video with <strong className="text-ink">Browse</strong>.</li>
          <li>
            Leave the output scale on <strong className="text-ink">2×</strong> — see the{' '}
            <Link href="/docs/quality-guide" className="link">quality guide</Link>.
          </li>
          <li>
            Press <strong className="text-ink">Estimate time</strong>. It processes 120 frames
            and projects the duration of the whole job on your hardware.
          </li>
          <li>
            Press <strong className="text-ink">Test 30 seconds</strong> and watch the result.
            This is the step that tells you whether the settings suit your footage.
          </li>
          <li>
            Only then press <strong className="text-ink">Start restoration</strong>.
          </li>
        </Ol>

        <H2 id="during">6. While it runs</H2>
        <p>
          The stat cards show progress, current chunk, elapsed time, remaining time, throughput
          and the wall-clock time it expects to finish. The Activity log carries everything the
          engine reports.
        </p>
        <H3>Stopping and resuming</H3>
        <Ul>
          <li>
            <strong className="text-ink">Stop safely</strong> lets the current chunk finish
            before exiting, so the resume point stays frame-exact.
          </li>
          <li>Starting the same job again continues from that frame.</li>
          <li>
            Closing the window or losing power costs at most the unfinished chunk — roughly 100
            seconds of video.
          </li>
          <li>
            Finished chunks in the scratch folder are ordinary MP4 files. Open the newest one to
            inspect quality mid-run.
          </li>
        </Ul>

        <H2 id="output">7. The finished file</H2>
        <p>
          When the last chunk completes, the chunks are concatenated by stream copy — no
          re-encode, no quality loss — and the original audio is muxed in. The result is a
          single MP4 in your chosen output folder. Use{' '}
          <strong className="text-ink">Open</strong> next to the output path to jump there.
        </p>

        <H2 id="cli">Command line</H2>
        <p>Everything the interface does is available directly:</p>
        <Pre>{`.\\venv\\Scripts\\python.exe verify_setup.py
.\\venv\\Scripts\\python.exe restore_video.py "input.mp4" --final-scale 2 --work D:\\scratch
.\\venv\\Scripts\\python.exe restore_video.py --help`}</Pre>
      </Prose>
    </>
  );
}
