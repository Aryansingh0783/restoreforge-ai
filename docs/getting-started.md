# Getting started

Full guide with screenshots: see the project website's documentation section.

## 1. Prerequisites

```powershell
winget install Python.Python.3.11    # keep "tcl/tk and IDLE" ticked
winget install Gyan.FFmpeg
```

Open a **new** terminal afterwards so PATH updates are visible.

## 2. Install

Double-click `START_HERE.bat`, then press **Install / Repair environment**.
Setup runs eight steps: locate Python, create folders, build the virtual
environment, install PyTorch from the CUDA 12.8 wheel index (~2.5 GB), install
the remaining dependencies, download the model weights, check FFmpeg and NVENC,
and finally run verification.

Setup is resumable. If the download drops, press the button again — it reuses a
good environment and skips weights already present.

Only when verification passes does setup write `.setup_ok`. The application
gates every action on that marker, because a virtual environment exists after
step 3 of 8 and therefore proves nothing.

## 3. Verify

Press **Check setup** (F5). You want `ALL CHECKS PASSED`, and in particular the
line confirming your GPU architecture has matching compiled kernels.

## 4. First restoration

1. **Browse** to a source video.
2. Leave the scale on **2×** — see [quality-guide.md](quality-guide.md).
3. **Estimate time** — measures 120 frames and projects the full runtime.
4. **Test 30 seconds** — watch the result before committing hours.
5. **Start restoration**.

## Stopping and resuming

- **Stop safely** lets the current chunk finish, keeping the resume point exact.
- Starting the same job again continues from that frame.
- Closing the window or losing power costs at most one chunk (~100 s of video).
- Finished chunks in the scratch folder are ordinary MP4 files — open the newest
  to inspect quality mid-run.

## Command line

```powershell
.\venv\Scripts\python.exe verify_setup.py
.\venv\Scripts\python.exe restore_video.py "input.mp4" --final-scale 2 --work D:\scratch
.\venv\Scripts\python.exe restore_video.py --help
```
