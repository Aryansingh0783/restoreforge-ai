#!/usr/bin/env python
"""
verify_setup.py - prove the whole RestoreForge AI stack works before
starting a long job.

    python verify_setup.py

Checks, in order:
  1. PyTorch sees the GPU AND has sm_120 kernels compiled in
  2. A real matmul actually executes (catches the silent Blackwell failure)
  3. SCUNet loads its checkpoint strictly and denoises a real tensor
  4. Real-ESRGAN loads its checkpoint strictly and 4x's a real tensor
  5. Peak VRAM at 1280x720, so you know whether tiling will be needed
  6. ffmpeg + NVENC actually encode a frame
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OK, BAD, WARN = "  [ok]  ", "  [FAIL]", "  [warn]"
failures: list[str] = []


def fail(msg: str):
    failures.append(msg)
    print(f"{BAD} {msg}")


def main():
    print("\n" + "=" * 62)
    print(" AI Video Restoration - environment check")
    print("=" * 62)

    # ---------------------------------------------------------- 1. torch/cuda
    print("\n1. PyTorch and CUDA")
    try:
        import torch
    except ImportError:
        fail("PyTorch is not installed. Run setup.ps1.")
        return report()

    print(f"{OK} torch {torch.__version__}  (CUDA {torch.version.cuda})")

    if not torch.cuda.is_available():
        fail("torch.cuda.is_available() is False - GPU not visible to PyTorch")
        return report()

    name = torch.cuda.get_device_name(0)
    cap = torch.cuda.get_device_capability(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    arches = torch.cuda.get_arch_list()
    print(f"{OK} {name}  {vram:.0f} GB  compute sm_{cap[0]}{cap[1]}")

    target = f"sm_{cap[0]}{cap[1]}"
    if target in arches:
        print(f"{OK} this build has {target} kernels")
    else:
        fail(f"NO {target} KERNELS. This build only has: {', '.join(arches)}\n"
             f"          A Blackwell RTX 5070 needs PyTorch >= 2.7 built for CUDA 12.8.\n"
             f"          Fix: pip install torch torchvision "
             f"--index-url https://download.pytorch.org/whl/cu128")
        return report()

    # ---------------------------------------------------------- 2. real kernel
    print("\n2. Executing a real CUDA kernel")
    try:
        a = torch.randn(2048, 2048, device="cuda", dtype=torch.float16)
        b = (a @ a).float().mean().item()
        torch.cuda.synchronize()
        if b != b:  # NaN
            raise RuntimeError("matmul produced NaN")
        print(f"{OK} fp16 matmul on GPU succeeded")
        del a
    except Exception as e:
        fail(f"kernel launch failed: {e}")
        return report()

    # ---------------------------------------------------------- 3/4. models
    sys.path.insert(0, str(ROOT))
    try:
        from archs import build_denoiser, build_upscaler
    except Exception as e:
        fail(f"cannot import archs.py: {e}")
        return report()

    dev = torch.device("cuda")
    checks = [
        ("3. SCUNet denoiser", ROOT / "models/SCUNet/scunet_color_real_psnr.pth",
         build_denoiser, 1),
        ("4. Real-ESRGAN x4", ROOT / "models/RealESRGAN/RealESRGAN_x4plus.pth",
         build_upscaler, 4),
    ]

    peak_total = 0.0
    for label, path, builder, scale in checks:
        print(f"\n{label}")
        if not path.exists():
            fail(f"weights missing: {path}")
            continue
        print(f"{OK} found {path.name} ({path.stat().st_size / 1e6:.0f} MB)")
        try:
            torch.cuda.reset_peak_memory_stats()
            model = builder(str(path), dev).half()
            x = torch.rand(1, 3, 720, 1280, device=dev, dtype=torch.float16)
            torch.cuda.synchronize()
            t = time.time()
            with torch.inference_mode():
                y = model(x)
            torch.cuda.synchronize()
            dt = time.time() - t

            expect = (720 * scale, 1280 * scale)
            if tuple(y.shape[-2:]) != expect:
                fail(f"wrong output shape {tuple(y.shape[-2:])}, expected {expect}")
                continue

            peak = torch.cuda.max_memory_allocated() / 1e9
            peak_total = max(peak_total, peak)
            print(f"{OK} loaded strictly, ran 720p -> {y.shape[-1]}x{y.shape[-2]}")
            print(f"{OK} {dt:.2f} s/frame full-frame, peak VRAM {peak:.1f} GB")
            del model, x, y
            torch.cuda.empty_cache()
        except torch.cuda.OutOfMemoryError:
            print(f"{WARN} OOM at full frame - the script will tile automatically")
            torch.cuda.empty_cache()
        except Exception as e:
            fail(f"{label} failed: {type(e).__name__}: {e}")

    # ---------------------------------------------------------- 5. ffmpeg
    print("\n5. ffmpeg and NVENC")
    if not shutil.which("ffmpeg"):
        fail("ffmpeg is not on PATH (open a new terminal after installing)")
    else:
        ver = subprocess.run(["ffmpeg", "-version"], capture_output=True,
                             text=True).stdout.splitlines()[0]
        print(f"{OK} {ver[:60]}")
        encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                                  capture_output=True, text=True).stdout
        for enc in ("hevc_nvenc", "av1_nvenc"):
            if enc not in encoders:
                (fail if enc == "hevc_nvenc" else print)(
                    f"{enc} not in this ffmpeg build" if enc == "hevc_nvenc"
                    else f"{WARN} {enc} not available (optional)")
                continue
            # Presence in -encoders does not prove the driver will accept it.
            r = subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-f", "lavfi", "-i", "color=c=gray:s=1280x720:d=0.1",
                 "-c:v", enc, "-preset", "p7", "-f", "null", "-"],
                capture_output=True, text=True)
            if r.returncode == 0:
                print(f"{OK} {enc} encoded a test frame")
            else:
                fail(f"{enc} present but failed: {r.stderr.strip()[:120]}")

    return report(peak_total)


def report(peak: float = 0.0):
    print("\n" + "=" * 62)
    if failures:
        print(f" {len(failures)} PROBLEM(S) - fix these before running a long job:")
        for f in failures:
            print(f"   - {f.splitlines()[0]}")
        print("=" * 62 + "\n")
        return 1

    print(" ALL CHECKS PASSED")
    if peak:
        print(f" Peak VRAM at 720p: {peak:.1f} GB")
    print("""
 Next: run a short test before committing to a long job.

   python restore_video.py "path\to\input.mp4" --limit 450 --final-scale 2 -o test.mp4

 Watch the fps figure it reports. Total hours = frames / fps / 3600.""")
    print("=" * 62 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
