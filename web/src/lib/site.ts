/**
 * Single source of truth for outbound links and shared copy.
 *
 * Replace GITHUB_OWNER / GITHUB_REPO after creating the repository. Everything
 * that points outward is derived from these two values, so there is exactly one
 * place to edit and no chance of a half-updated link.
 */

// Annotated as `string` rather than inferred literals: the guard below is a
// real runtime check for forks that reset these to the placeholder, and TS
// would otherwise reject the comparison as provably false.
export const GITHUB_OWNER: string = 'Aryansingh0783';
export const GITHUB_REPO: string = 'restoreforge-ai';

/** True once the placeholders above have been replaced with a real account. */
export const REPO_CONFIGURED = GITHUB_OWNER !== 'your-github-username';

export const site = {
  name: 'RestoreForge AI',
  tagline: 'Local AI Video Restoration for Windows',
  description:
    'A privacy-first Windows desktop application that restores noisy, low-quality video with AI denoising and upscaling. Everything runs on your own GPU — no uploads, no accounts, no cloud.',
  url: 'https://restoreforge.example',
  version: '0.1.0',
  repo: `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}`,
  releases: `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases`,
  latestRelease: `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`,
  issues: `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/issues`,
  license: `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/blob/main/LICENSE`,
} as const;

export const nav = [
  { href: '/features', label: 'Features' },
  { href: '/workflow', label: 'Workflow' },
  { href: '/requirements', label: 'Requirements' },
  { href: '/docs', label: 'Docs' },
  { href: '/download', label: 'Download' },
] as const;

export const docsNav = [
  { href: '/docs', label: 'Overview' },
  { href: '/docs/getting-started', label: 'Getting started' },
  { href: '/docs/quality-guide', label: 'Quality guide' },
  { href: '/docs/troubleshooting', label: 'Troubleshooting' },
] as const;

/** The pipeline, in the order the engine actually runs it. */
export const pipeline = [
  {
    id: '01',
    name: 'FFmpeg decode',
    detail:
      'Decodes the source and converts variable frame rate to constant frame rate at the measured average, so no real frame is dropped and audio stays in sync.',
  },
  {
    id: '02',
    name: 'Temporal stabilization',
    detail:
      'A temporal-only hqdn3d pass settles the noise field between frames before any AI sees it. Single-image models otherwise denoise each frame slightly differently, which reads as shimmer.',
  },
  {
    id: '03',
    name: 'SCUNet denoise',
    detail:
      'Spatial denoising on the GPU. The blend strength is adjustable, because full strength can flatten skin and fabric texture.',
  },
  {
    id: '04',
    name: 'Real-ESRGAN 4×',
    detail:
      'Super-resolution at 4×, with feathered tile blending so no seam grid appears when a frame is too large to process whole.',
  },
  {
    id: '05',
    name: 'NVENC encode',
    detail:
      'Optional downscale to 2×, then hardware HEVC encoding. Chunks are joined by stream copy and the original audio is muxed back in.',
  },
] as const;

export const features = [
  {
    icon: 'RotateCcw',
    title: 'Resumable chunk processing',
    body: 'Work is split into 1,500-frame chunks. Each finished chunk is a playable MP4, so a crash or a deliberate stop costs at most one chunk.',
  },
  {
    icon: 'AudioLines',
    title: 'Original audio preserved',
    body: 'The source audio track is muxed into the final file untouched by stream copy wherever the container allows it.',
  },
  {
    icon: 'Palette',
    title: 'Colour-aware processing',
    body: 'Full-range and limited-range sources are detected and matched. Forcing the wrong range measurably darkens the whole video.',
  },
  {
    icon: 'Grid2x2',
    title: 'Feathered tiling',
    body: 'Tiles are blended with a ramp rather than hard-cut. Verified to reconstruct the input to floating-point exactness at every tile size.',
  },
  {
    icon: 'Cpu',
    title: 'Blackwell ready',
    body: 'Built and tested against an RTX 5070 (sm_120). Setup verifies the installed PyTorch actually carries kernels for your GPU, not just that CUDA loads.',
  },
  {
    icon: 'FlaskConical',
    title: 'Test-first reliability',
    body: 'Two suites cover the pipeline and the desktop UI without needing a GPU, including frame-exact chunk seams and pixel-identical resume.',
  },
] as const;

export const faqs = [
  {
    q: 'Is my video ever uploaded anywhere?',
    a: 'No. The restoration engine is a desktop application that runs on your computer using your GPU. This website is documentation only — it has no upload form and no server-side processing. There is no account system and no telemetry.',
  },
  {
    q: 'What hardware do I need?',
    a: 'Windows 10 or 11, an NVIDIA GPU with CUDA support, and Python 3.11. Development and testing were done on an RTX 5070 with 12 GB of VRAM. Other CUDA GPUs are expected to work but have not been individually verified, and AMD, Intel Arc and Apple Silicon are not supported.',
  },
  {
    q: 'How long does a restoration take?',
    a: 'On the reference machine, roughly 2.2 seconds per source frame at 720p. A 41-minute clip is about 37,000 frames, so on the order of a day. The application measures your actual speed over 120 frames before you commit, and the job is resumable.',
  },
  {
    q: 'Why is 2× recommended over 4×?',
    a: 'Both settings run the AI at 4×; 2× then downsamples the result. Supersampling averages away detail the model invented, usually giving a sharper and cleaner picture than native 4× at a quarter of the file size, with far better playback compatibility. 4× remains available.',
  },
  {
    q: 'Will it fix badly damaged footage?',
    a: 'It will usually make footage cleaner, sharper and more watchable. It cannot recover detail that was never recorded — an AI upscaler invents plausible detail rather than restoring lost truth. Always run the 30-second test first and judge the result yourself.',
  },
  {
    q: 'Can I stop a long job and continue later?',
    a: 'Yes. Stop finishes the chunk currently in flight before exiting, so the resume point stays exact. Starting again continues from the same frame. Closing the window is equally safe; at worst you lose the unfinished chunk.',
  },
  {
    q: 'How much disk space does it need?',
    a: 'The engine streams raw frames through pipes rather than writing PNG sequences, so scratch usage is roughly the size of the finished video — on the order of 15 GB for a 41-minute 2× job, more at 4×. The application shows an estimate and the free space on the scratch volume before you start.',
  },
  {
    q: 'Is this production-tested?',
    a: 'Be aware that a full end-to-end restoration of a feature-length source has not yet been completed. The pipeline, resume behaviour and encoder validation are covered by automated tests, and every stage has run on real footage, but long-run results are not yet published.',
  },
] as const;
