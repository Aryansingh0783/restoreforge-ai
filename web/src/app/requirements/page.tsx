import type { Metadata } from 'next';
import Link from 'next/link';
import { Callout, PageHeader, Section, SectionHead, SpecTable, Code } from '@/components/ui';

export const metadata: Metadata = {
  title: 'Requirements',
  description:
    'Windows, NVIDIA GPU, CUDA, Python 3.11 and FFmpeg requirements for running RestoreForge AI locally.',
};

export default function RequirementsPage() {
  return (
    <>
      <PageHeader
        kicker="Before you install"
        title="System requirements"
        lede="RestoreForge AI is Windows and NVIDIA only. That is an architectural constraint of the pipeline — CUDA for inference, NVENC for encoding — not a temporary limitation."
      />

      <Section>
        <SectionHead index="01" title="Minimum and recommended" />
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <p className="kicker mb-3">Required</p>
            <SpecTable
              rows={[
                ['Operating system', 'Windows 10 or 11, 64-bit'],
                ['GPU', 'NVIDIA with CUDA support'],
                ['VRAM', '6 GB minimum, 8 GB+ comfortable'],
                ['System RAM', '16 GB'],
                ['Python', '3.11, with tcl/tk and IDLE'],
                ['FFmpeg', 'On PATH'],
                ['Disk', '~5 GB for the environment and models'],
              ]}
            />
          </div>
          <div>
            <p className="kicker mb-3">Reference machine</p>
            <SpecTable
              rows={[
                ['GPU', 'NVIDIA RTX 5070, 12 GB'],
                ['Architecture', 'Blackwell, sm_120'],
                ['CPU', 'AMD Ryzen 7 9800X3D'],
                ['RAM', '32 GB DDR5'],
                ['PyTorch', '2.11.0 + CUDA 12.8'],
                ['FFmpeg', '8.1 with hevc_nvenc and av1_nvenc'],
                ['Measured', '~2.2 s per 720p source frame'],
              ]}
            />
            <p className="mt-3 text-[13px] leading-relaxed text-faint">
              This is the configuration the project is developed and tested on. Other CUDA GPUs
              are expected to work but have not been individually verified.
            </p>
          </div>
        </div>
      </Section>

      <Section className="bg-panel">
        <SectionHead
          index="02"
          title="GPU compatibility"
          lede="One detail matters more than raw speed: whether your PyTorch build contains compiled kernels for your GPU's architecture."
        />
        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <div className="space-y-4 text-sm leading-relaxed text-sub">
            <p>
              Newer cards produce a confusing failure. A PyTorch build without kernels for your
              architecture still reports <Code>torch.cuda.is_available() == True</Code>, loads
              models happily, and then fails on the first kernel launch with{' '}
              <em>no kernel image is available for execution on the device</em>.
            </p>
            <p>
              Setup therefore checks <Code>torch.cuda.get_arch_list()</Code> against your actual
              device capability. An RTX 50-series card reports <Code>sm_120</Code> and needs
              PyTorch 2.7 or newer built for CUDA 12.8.
            </p>
            <p>
              The Environment page inside the application shows the result of this check, and{' '}
              <Link href="/docs/troubleshooting" className="link">troubleshooting</Link> covers
              how to fix a mismatch.
            </p>
          </div>
          <div className="space-y-4">
            <Callout tone="ok" title="Expected to work">
              <p>NVIDIA RTX 20, 30, 40 and 50 series, and equivalent professional cards, with a
              PyTorch build matching the architecture.</p>
            </Callout>
            <Callout tone="warn" title="Not supported">
              <p>
                AMD and Intel Arc GPUs, Apple Silicon, CPU-only machines, Linux and macOS. The
                pipeline depends on CUDA and NVENC.
              </p>
            </Callout>
          </div>
        </div>
      </Section>

      <Section>
        <SectionHead
          index="03"
          title="Disk space"
          lede="The engine streams frames rather than writing image sequences, which keeps scratch usage close to the size of the finished video."
        />
        <SpecTable
          rows={[
            ['Environment + models', '~5 GB, one time'],
            ['Scratch, 41 min at 2x', '~10-15 GB'],
            ['Scratch, 41 min at 4x', '~30-40 GB'],
            ['Final output', 'Roughly the same as the scratch chunks'],
            ['If frames were spooled as PNG', 'Several hundred GB — which is why they are not'],
          ]}
        />
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-sub">
          The scratch folder is configurable in the application, so you can point it at a drive
          with room to spare. Free space is shown before you start a run, and the estimate is
          recalculated whenever you change the output scale.
        </p>
      </Section>

      <Section className="bg-panel">
        <SectionHead index="04" title="Installing the prerequisites" />
        <div className="max-w-3xl space-y-4 text-sm leading-relaxed text-sub">
          <p>Both prerequisites are available through winget on Windows:</p>
          <pre className="overflow-x-auto rounded-xl2 border border-line bg-[#07090c] p-4 font-mono text-[12.5px] text-[#c3ccd8]">
            <code>{`winget install Python.Python.3.11
winget install Gyan.FFmpeg`}</code>
          </pre>
          <p>
            Keep <strong className="text-ink">tcl/tk and IDLE</strong> ticked when installing
            Python — the desktop interface needs tkinter. After installing FFmpeg, open a new
            terminal so the updated PATH is picked up.
          </p>
          <p>
            Everything else, including PyTorch and the model weights, is installed by the
            application itself. See{' '}
            <Link href="/docs/getting-started" className="link">getting started</Link>.
          </p>
        </div>
      </Section>
    </>
  );
}
