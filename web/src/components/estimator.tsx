'use client';

import { useMemo, useState } from 'react';
import { Info } from 'lucide-react';

/**
 * Planning estimator. Everything is computed in the browser from numbers the
 * user types — nothing is uploaded, nothing is measured, no file is read.
 *
 * The per-frame cost is anchored on the reference machine (RTX 5070, 720p:
 * SCUNet ~0.40 s + Real-ESRGAN ~1.80 s = ~2.2 s/frame) and scaled by input
 * pixel count, since the AI work is proportional to source resolution.
 */

const REF_SECONDS_PER_FRAME = 2.2;
const REF_PIXELS = 1280 * 720;

const GPU_TIERS = [
  { id: 'ref', label: 'RTX 5070 class (reference)', factor: 1 },
  { id: 'fast', label: 'RTX 4080 / 4090 class', factor: 0.62 },
  { id: 'mid', label: 'RTX 3060 / 4060 class', factor: 1.9 },
] as const;

const PRESETS = [
  { id: 'p1', label: '720p → 1440p (2×)', w: 1280, h: 720, minutes: 41, scale: 2 },
  { id: 'p2', label: '720p → 2880p (4×)', w: 1280, h: 720, minutes: 41, scale: 4 },
  { id: 'p3', label: '480p → 960p (2×)', w: 640, h: 480, minutes: 20, scale: 2 },
  { id: 'p4', label: '1080p → 2160p (2×)', w: 1920, h: 1080, minutes: 10, scale: 2 },
] as const;

function fmtDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h === 0) return `${Math.max(1, m)} min`;
  return `${h} h ${String(m).padStart(2, '0')} min`;
}

function Field({
  label,
  suffix,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string;
  suffix?: string;
  value: number;
  onChange: (n: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  const id = `est-${label.toLowerCase().replace(/[^a-z]+/g, '-')}`;
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-[13px] text-sub">
        {label}
      </label>
      <div className="flex items-center gap-2">
        <input
          id={id}
          type="number"
          inputMode="numeric"
          value={Number.isFinite(value) ? value : ''}
          min={min}
          max={max}
          step={step}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full rounded-lg border border-line bg-[#0b0e12] px-3 py-2 font-mono text-sm text-ink transition-colors focus:border-accent/50"
        />
        {suffix ? <span className="font-mono text-[11px] text-faint">{suffix}</span> : null}
      </div>
    </div>
  );
}

export function Estimator() {
  const [width, setWidth] = useState(1280);
  const [height, setHeight] = useState(720);
  const [minutes, setMinutes] = useState(41);
  const [fps, setFps] = useState(15);
  const [scale, setScale] = useState<2 | 4>(2);
  const [gpu, setGpu] = useState<(typeof GPU_TIERS)[number]['id']>('ref');

  const result = useMemo(() => {
    const w = Math.max(1, width || 0);
    const h = Math.max(1, height || 0);
    const mins = Math.max(0, minutes || 0);
    const rate = Math.max(1, fps || 0);
    const factor = GPU_TIERS.find((g) => g.id === gpu)?.factor ?? 1;

    const frames = Math.round(mins * 60 * rate);
    const perFrame = REF_SECONDS_PER_FRAME * ((w * h) / REF_PIXELS) * factor;
    const seconds = frames * perFrame;

    const outW = w * scale;
    const outH = h * scale;
    // Scratch chunks are roughly the size of the finished file. Conservative
    // coefficient, deliberately rounded up.
    const diskGb = Math.max(1, mins * ((outW * outH) / 1e6) * 0.055);

    return { frames, perFrame, seconds, outW, outH, diskGb };
  }, [width, height, minutes, fps, scale, gpu]);

  const applyPreset = (p: (typeof PRESETS)[number]) => {
    setWidth(p.w);
    setHeight(p.h);
    setMinutes(p.minutes);
    setScale(p.scale as 2 | 4);
  };

  return (
    <div className="card overflow-hidden">
      <div className="grid gap-0 lg:grid-cols-[1.15fr_1fr]">
        {/* ---------------------------------------------------------- inputs */}
        <div className="border-b border-line p-6 lg:border-b-0 lg:border-r">
          <div className="mb-5 flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => applyPreset(p)}
                className="rounded-full border border-line bg-cardhi px-3 py-1.5 font-mono text-[11px] text-sub transition-colors hover:border-accent/40 hover:text-ink"
              >
                {p.label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Source width" suffix="px" value={width} onChange={setWidth} min={16} max={7680} />
            <Field label="Source height" suffix="px" value={height} onChange={setHeight} min={16} max={4320} />
            <Field label="Duration" suffix="min" value={minutes} onChange={setMinutes} min={0} max={600} />
            <Field label="Frame rate" suffix="fps" value={fps} onChange={setFps} min={1} max={120} />
          </div>

          <fieldset className="mt-5">
            <legend className="mb-2 text-[13px] text-sub">Output scale</legend>
            <div className="flex gap-2">
              {([2, 4] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setScale(s)}
                  aria-pressed={scale === s}
                  className={`rounded-lg border px-4 py-2 text-sm transition-colors ${
                    scale === s
                      ? 'border-accent/50 bg-accent/10 text-accent'
                      : 'border-line bg-cardhi text-sub hover:text-ink'
                  }`}
                >
                  {s}×{s === 2 ? '  recommended' : ''}
                </button>
              ))}
            </div>
          </fieldset>

          <div className="mt-5">
            <label htmlFor="est-gpu" className="mb-1.5 block text-[13px] text-sub">
              GPU class
            </label>
            <select
              id="est-gpu"
              value={gpu}
              onChange={(e) => setGpu(e.target.value as typeof gpu)}
              className="w-full rounded-lg border border-line bg-[#0b0e12] px-3 py-2 text-sm text-ink transition-colors focus:border-accent/50"
            >
              {GPU_TIERS.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* --------------------------------------------------------- outputs */}
        <div className="bg-[#0c0f13] p-6">
          <p className="kicker mb-4">Planning estimate</p>

          <div className="mb-5">
            <p className="font-mono text-3xl font-semibold text-accent">
              {fmtDuration(result.seconds)}
            </p>
            <p className="mt-1 text-[13px] text-faint">of local GPU time, start to finish</p>
          </div>

          <dl className="space-y-0 text-sm">
            {[
              ['Frames to process', result.frames.toLocaleString()],
              ['Per frame', `${result.perFrame.toFixed(2)} s`],
              ['Output resolution', `${result.outW} × ${result.outH}`],
              ['Scratch space', `~${Math.round(result.diskGb)} GB`],
              ['Resumable chunks', Math.max(1, Math.ceil(result.frames / 1500)).toLocaleString()],
            ].map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between border-b border-line py-2.5">
                <dt className="text-sub">{k}</dt>
                <dd className="font-mono text-[13px] text-ink">{v}</dd>
              </div>
            ))}
          </dl>

          <p className="mt-5 flex gap-2 text-[12px] leading-relaxed text-faint">
            <Info size={14} aria-hidden className="mt-0.5 shrink-0" />
            <span>
              Planning estimate only; actual speed depends on resolution, GPU, tile settings,
              codec, and source characteristics. The desktop application measures your real
              throughput over 120 frames before you commit to a long run.
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
