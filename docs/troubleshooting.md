# Troubleshooting

## GPU detected, but "no kernel image is available"

Your PyTorch build has no compiled kernels for your GPU architecture. CUDA
reports itself available, models load, then the first real operation fails. An
RTX 50-series card reports `sm_120`; builds against CUDA 12.1 or older only
carry kernels up to `sm_90`.

```powershell
.\venv\Scripts\python.exe -m pip uninstall -y torch torchvision
.\venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Setup says it is incomplete

Setup did not reach verification — usually the 2.5 GB PyTorch download was
interrupted. A virtual environment exists after step 3 of 8, so its presence is
not proof of completion; the app gates on `.setup_ok`.

Press **Install / Repair** again. Setup resumes and nothing is wasted. If it
fails repeatedly, the Activity log names the failing step.

## FFmpeg not found

```powershell
winget install Gyan.FFmpeg
```

Close every terminal and the application, then start again so PATH updates are
visible. Verify with `ffmpeg -version`.

## NVENC rejects the encoder options

Handled automatically. Before a long run, the exact command is tested against a
two-frame dummy encode; if rejected, the engine falls back through simpler
option sets and finally to CPU `libx265`, logging which tier it used. If it
falls back to CPU, update your NVIDIA driver and reinstall a full FFmpeg build.

## Model download failed

Press **Install / Repair**. Each weight file is size-checked, so anything
truncated is deleted and re-fetched. To force a clean download, delete the file
under `models\` and repeat.

## Out of memory

Handled automatically: the engine probes full-frame, then falls back through
768, 640, 512, 384 and 256-pixel tiles, re-tiling mid-run if another application
takes VRAM. Tiles are feathered so no seam grid appears. If it still fails,
close other GPU applications or choose a smaller output scale.

## Not enough disk space

A 41-minute job needs roughly 10–15 GB at 2× and 30–40 GB at 4×. Use **Change
scratch folder** on the Environment page to point at a roomier drive. Completed
chunks remain valid, so the job resumes after you free space.

## An interrupted job will not resume

- Resume requires identical settings; changing scale, quality or denoise
  deliberately invalidates existing chunks.
- The scratch folder must be the same one.
- To start over cleanly, delete the scratch folder.

## The window will not open

If `START_HERE.bat` reports Python with tkinter was not found, reinstall Python
3.11 with **tcl/tk and IDLE** selected. If the window closes with no message,
run `py -3.11 gui.py` from a terminal to see the error.

## Output shimmers in flat areas

Temporal instability from single-image models. Confirm temporal pre-denoise is
enabled (default) and consider raising denoise strength slightly.

## Playback stutters

Usually the player, not the file — 5120 × 2880 10-bit HEVC is demanding. Use a
2× output, or a player with hardware decoding such as mpv or VLC.
