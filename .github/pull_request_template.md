## What this changes

<!-- A short description. Link any issue this closes. -->

## Why

<!-- The problem being solved. -->

## How it was verified

- [ ] `_test_pipeline.py` passes (30 checks)
- [ ] `_test_gui.py` passes (54 checks)
- [ ] `npm run lint` passes (if the website changed)
- [ ] `npm run typecheck` passes (if the website changed)
- [ ] `npm run build` passes (if the website changed)
- [ ] Added or updated a test covering this change

## Regression checklist

Confirm none of the previously fixed bugs have returned. See CONTRIBUTING.md
for the full table and the reasoning behind each.

- [ ] No CUDA build without kernels for the target architecture
- [ ] `basicsr` still absent
- [ ] Pipe reads still use a flat 1-D byte view
- [ ] Measured VFR average still used, not nominal FPS
- [ ] Source colour range still preserved
- [ ] Batch files still CRLF with valid `GOTO` labels
- [ ] Setup completion still gated on `.setup_ok`
- [ ] PowerShell still checks exit codes rather than trapping expected stderr
- [ ] Per-codec encoder option tables intact, no orphaned values
- [ ] No writes to tkinter internals such as `self._w`
- [ ] No in-place ops on inference-mode tensors outside that context
- [ ] Test doubles still model real behaviour closely enough to fail

## Anything a reviewer should know

<!-- Trade-offs, follow-ups, or things you are unsure about. -->
