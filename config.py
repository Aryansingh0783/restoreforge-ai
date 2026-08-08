"""
config.py - portable configuration for RestoreForge AI.

Standard library only. The GUI imports this while running on the *system*
Python, before the virtual environment exists, so it must never pull in torch,
numpy or anything else from the venv.

Nothing user-specific is hard-coded here. Machine-specific choices (last video,
scratch directory, output directory) live in settings.json next to this file,
which is git-ignored.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

APP_NAME = "RestoreForge AI"
APP_TAGLINE = "Local AI Video Restoration for Windows"
VERSION = "0.1.0"

ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / "settings.json"
STAMP = ROOT / ".setup_ok"
VENV_PY = ROOT / "venv" / "Scripts" / "python.exe"
MODELS_DIR = ROOT / "models"

SCUNET_MODEL = MODELS_DIR / "SCUNet" / "scunet_color_real_psnr.pth"
ESRGAN_MODEL = MODELS_DIR / "RealESRGAN" / "RealESRGAN_x4plus.pth"

VIDEO_TYPES = (".mp4", ".mkv", ".avi", ".mov", ".wmv", ".m4v", ".webm", ".flv")

# Measured on an RTX 5070 at 720p: SCUNet ~0.40 s/frame plus Real-ESRGAN
# ~1.80 s/frame. Used only as a first guess before the app measures the real
# rate on this machine.
SECONDS_PER_FRAME_HINT = 2.2

# Roughly how many GB of chunk files a minute of finished output takes at the
# default quality, per megapixel of output. Deliberately conservative.
GB_PER_MINUTE_PER_MP = 0.055

DEFAULTS = {
    "video": "",
    "work_dir": "",       # empty means "<project>/work"
    "output_dir": "",     # empty means "next to the source video"
    "scale": "2",
    "denoise": 0.85,
    "cq": 19,
    "encoder": "hevc_nvenc",
}


# ---------------------------------------------------------------- settings


def load_settings() -> dict:
    """Merged defaults + settings.json. Never raises."""
    data = dict(DEFAULTS)
    try:
        if SETTINGS_FILE.exists():
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return data


def save_settings(values: dict) -> None:
    """Persist the subset of keys we recognise. Never raises."""
    try:
        current = load_settings()
        current.update({k: v for k, v in values.items() if k in DEFAULTS})
        SETTINGS_FILE.write_text(json.dumps(current, indent=2), encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass


# ---------------------------------------------------------------- paths


def work_dir(settings: dict | None = None) -> Path:
    s = settings if settings is not None else load_settings()
    raw = (s.get("work_dir") or "").strip()
    return Path(raw) if raw else ROOT / "work"


def output_dir(settings: dict | None = None, source: Path | None = None) -> Path:
    """Where the finished file goes: the configured directory, else beside the
    source video, else the project folder."""
    s = settings if settings is not None else load_settings()
    raw = (s.get("output_dir") or "").strip()
    if raw:
        return Path(raw)
    if source is not None:
        try:
            return Path(source).resolve().parent
        except OSError:
            pass
    return ROOT


def free_gb(path: Path) -> float:
    """Free space on the volume holding `path`, walking up to the first parent
    that exists. Returns 0.0 if it cannot be determined."""
    p = Path(path)
    for candidate in [p, *p.parents]:
        try:
            if candidate.exists():
                return shutil.disk_usage(candidate).free / 1e9
        except OSError:
            continue
    return 0.0


def is_setup_complete() -> bool:
    """A venv alone proves nothing - it exists after the first of eight setup
    steps. setup.ps1 writes .setup_ok only once verify_setup.py passes."""
    return STAMP.exists() and VENV_PY.exists()


def models_present() -> bool:
    return SCUNET_MODEL.exists() and ESRGAN_MODEL.exists()


# ---------------------------------------------------------------- estimates


def estimate_seconds(frames: int, seconds_per_frame: float = SECONDS_PER_FRAME_HINT) -> float:
    """Planning estimate only. Real throughput depends on GPU, resolution,
    tile size, codec and source characteristics."""
    if frames <= 0 or seconds_per_frame <= 0:
        return 0.0
    return frames * seconds_per_frame


def estimate_disk_gb(minutes: float, out_w: int, out_h: int) -> float:
    """Rough scratch-space requirement for the encoded chunks."""
    if minutes <= 0 or out_w <= 0 or out_h <= 0:
        return 0.0
    megapixels = (out_w * out_h) / 1e6
    return max(1.0, minutes * megapixels * GB_PER_MINUTE_PER_MP)


def vram_guidance(out_w: int, out_h: int) -> str:
    """Plain-language note about VRAM for a given output size."""
    mp = (out_w * out_h) / 1e6
    if mp >= 12:
        return "~8-10 GB VRAM at full frame; tiling engages automatically below that"
    if mp >= 5:
        return "~5-7 GB VRAM at full frame"
    return "~3-4 GB VRAM at full frame"


NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
