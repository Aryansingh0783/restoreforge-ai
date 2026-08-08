# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project will
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) from 1.0.0.

## [Unreleased]

### Added
- Public documentation website in `web/` — landing page, features, workflow,
  requirements, four documentation pages, privacy statement, download guidance
  and changelog, plus a client-side planning estimator that uploads nothing.
- GitHub repository hygiene: issue templates for bugs, features and restoration
  quality; a pull-request template carrying the regression checklist; and a CI
  workflow that runs both Python suites, verifies CRLF line endings on Windows
  scripts and fails on hard-coded user paths.
- `config.py` — portable paths, persisted settings and planning estimates, with
  no machine-specific values compiled in.

### Changed
- Renamed the project to **RestoreForge AI**.
- Rebuilt the desktop interface around a dark technical theme with sidebar
  navigation, a readiness panel reporting GPU, CUDA, model and FFmpeg status, a
  chunk-position card, VRAM and disk guidance, tooltips on advanced settings and
  keyboard-accessible controls.
- Source video, scratch folder and output folder are now chosen in the
  application and persisted to a git-ignored `settings.json`, replacing values
  that were previously hard-coded.
- The progress stream now reports chunk position alongside frame counts.

### Fixed
- Removed hard-coded personal file paths from `gui.py`, `restore_video.py` and
  `verify_setup.py`.

## [0.1.0] — unreleased

First working version. Recorded here for context; not tagged as a release.

### Restoration engine
- Streaming pipeline: FFmpeg decode, temporal stabilization, SCUNet denoise,
  Real-ESRGAN 4×, optional downscale, NVENC HEVC encode.
- Frames stream through pipes rather than being spooled as PNG sequences,
  reducing scratch usage from hundreds of GB to roughly the size of the output.
- Resumable 1,500-frame chunks, each independently playable, joined at the end
  by stream copy with the original audio muxed in.
- Variable frame rate converted to constant frame rate at the measured average,
  so no real frame is dropped and audio stays in sync.
- Source colour range detected and preserved.
- Feathered tile blending, verified exact to floating point at every tile size.
- Bit-identical duplicate frames from VFR conversion detected and reused.
- NVENC options validated with a two-frame dummy encode before a long run,
  falling back through four option tiers and finally to CPU encoding.
- Clean stop via a sentinel file so the chunk in flight is finalised.

### Setup and verification
- Resumable eight-step installer that reuses a good environment and retries
  interrupted downloads; model weights are size-checked.
- Completion gated on a `.setup_ok` marker written only after verification.
- GPU verification checks compiled kernel architectures rather than trusting
  `torch.cuda.is_available()`.

### Notable bug fixes during development
- PyTorch builds without `sm_120` kernels load successfully and then fail on
  every kernel launch; setup now installs from the CUDA 12.8 index and verifies
  the architecture list.
- Frame reads from pipes used a 3-dimensional `memoryview`, whose slicing moves
  by rows rather than bytes — every frame was truncated at 64 KB.
- Nominal frame rate was used for a variable-frame-rate source, which would have
  silently discarded 83 real frames.
- Limited colour range was forced on a full-range source, darkening the entire
  video by a measured ~1.6/255 on every channel.
- Batch files written with LF endings caused `GOTO` to fail, closing the window
  instantly with no message.
- Setup treated the existence of a virtual environment as proof of a completed
  install, presenting a working-looking UI over an empty environment.
- `$ErrorActionPreference = "Stop"` turned expected native-command stderr into a
  terminating error, killing setup at the probe that checks whether PyTorch is
  installed.
- The AV1 encoder branch filtered flag names out of a shared option list and
  left orphaned values behind.
- `IntVar` bound to a `ttk.Scale` raised on `.get()`, since Scale writes floats.
- `StatCard` assigned a pixel width to `self._w`, overwriting tkinter's internal
  Tcl pathname and crashing the application on launch.
- In-place tensor operations were performed outside the `torch.inference_mode()`
  context that produced them, failing one frame into every job.

### Tests
- Pipeline suite: 30 checks including frame-exact chunk seams, pixel-identical
  resume and safe-stop finalisation.
- GUI suite: 54 checks covering construction, rendering, log parsing and command
  building, with no display required.
- Test doubles model tkinter internals and PyTorch inference-tensor semantics,
  after permissive stubs allowed three real bugs to reach the GPU.
