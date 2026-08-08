# Contributing to RestoreForge AI

Thanks for considering a contribution. This document covers how to get set up,
what the project cares about, and the rules that exist because breaking them
has already cost real debugging time.

## Getting set up

You need Windows 10/11, an NVIDIA GPU, Python 3.11 with tkinter, and FFmpeg on
PATH. Run `START_HERE.bat` and press **Install / Repair environment**, or run
`powershell -ExecutionPolicy Bypass -File .\setup.ps1` directly.

For the website you need Node 18.18 or newer:

```bash
cd web
npm install
npm run dev
```

## Running the tests

Both suites run without a GPU and without a display, because they stub torch
and tkinter. Install the small test-only dependency set first:

```bash
python -m pip install -r requirements-dev.txt
```

Then run them before opening a pull request.

```powershell
.\venv\Scripts\python.exe _test_pipeline.py   # 30 checks, needs ffmpeg
.\venv\Scripts\python.exe _test_gui.py        # 54 checks, no display needed
```

For the website:

```bash
cd web
npm run lint
npm run typecheck
npm run build
```

## Things that must not regress

Each item below is a bug that was diagnosed, fixed and covered by a test. Please
do not reintroduce them.

| Area | Rule |
| --- | --- |
| PyTorch | Never pin a CUDA build without kernels for the target architecture. Verify with `torch.cuda.get_arch_list()`, not `torch.cuda.is_available()`. |
| `basicsr` | Stays uninstalled. Architectures live in `archs.py`. Adding it back reintroduces the `functional_tensor` and `__version__` failures and re-pins torchvision. |
| Pipe reads | Read frames through a flat 1-D byte view. Slicing a multi-dimensional `memoryview` moves by rows, not bytes, and silently truncates every frame. |
| Frame rate | Use the measured average frame rate for VFR sources, never the nominal header value. |
| Colour range | Preserve the source range. Forcing limited range on a full-range source darkens the whole video. |
| Batch files | Keep CRLF endings and valid `GOTO` labels. A failed `GOTO` closes the window with no message. |
| Setup state | A virtual environment is not proof of installation. Gate on `.setup_ok`, written only after verification passes. |
| PowerShell | Do not use `$ErrorActionPreference = "Stop"` around native commands whose stderr is expected. Check exit codes explicitly. |
| Encoder options | Keep per-codec option tables. Filtering flag names out of a shared list leaves orphaned values behind. |
| tkinter | Never assign to `self._w`, `self._name` or other `tkinter.Misc` internals. Use `DoubleVar` with `ttk.Scale`. |
| PyTorch tensors | No in-place operations on tensors created under `torch.inference_mode()` once execution has left that context. |
| GUI feedback | A button press must never be silently ignored. Say why, and self-heal stale job state. |
| Test doubles | Stubs must model real behaviour. A permissive fake that cannot fail is worse than no test — this has caused three separate escaped bugs. |

## Style

**Python.** Standard library plus the six pinned dependencies. `gui.py`,
`config.py` and `START_HERE.bat` run on the *system* Python before the virtual
environment exists, so they must not import torch, numpy or anything else from
`venv/`. Comments should explain *why*, not restate the code.

**TypeScript.** Strict mode, no `any`. Prefer server components; add
`'use client'` only where interactivity genuinely requires it. Tailwind
utilities with the shared tokens in `tailwind.config.ts` — no new colour values
scattered through components.

**Copy.** Accuracy over marketing. Do not claim lossless restoration, perfect
face recovery, real-time performance, or that any GPU will work. If a number is
not measured, do not state it as measured.

## Pull requests

1. Branch from `main`.
2. Keep the change focused; unrelated refactors make review harder.
3. Run both Python suites and the website's lint, typecheck and build.
4. Add a test for behaviour you changed or fixed.
5. Update the docs and `CHANGELOG.md` if user-visible behaviour changed.
6. Never commit weights, videos, `venv/`, `.setup_ok`, `settings.json` or
   restoration output. `.gitignore` covers these — check `git status` anyway.

## Reporting bugs

Use the issue templates. For restoration-quality problems please include the
source resolution, duration, codec and frame rate, plus your settings — but do
**not** attach the video itself.
