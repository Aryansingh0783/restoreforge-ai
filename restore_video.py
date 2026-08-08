#!/usr/bin/env python
"""
restore_video.py - RestoreForge AI restoration engine.

SCUNet denoise -> Real-ESRGAN 4x -> optional downscale -> NVENC HEVC encode.

    python restore_video.py "path\\to\\input.mp4" --final-scale 2

ARCHITECTURE NOTE
-----------------
This does NOT extract frames to PNG. A 41-minute 720p clip is roughly 37,000
frames; at 4x that is 5120x2880 each, which would be several hundred GB of
intermediate PNGs plus hours of CPU time spent purely on PNG compression.

Instead frames stream through pipes:

    ffmpeg decode --> stdout --> [SCUNet -> Real-ESRGAN] --> stdin --> ffmpeg NVENC

Nothing touches disk except the encoded chunk files (~15 GB total). Quality is
identical to the PNG route because the pipe carries raw uncompressed rgb24.

Work is split into chunks so an interrupted run resumes. Chunks are concatenated
with stream copy (zero re-encode, zero quality loss) into ONE final MP4 with the
original audio.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from archs import build_denoiser, build_upscaler  # noqa: E402

ROOT = Path(__file__).resolve().parent
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

# Set by --json-progress. The GUI parses these lines off stdout; everything
# else the script prints is treated as plain log text. Keeping the machine
# channel separate from the human one means the GUI never has to scrape a
# tqdm bar full of carriage returns.
EMIT_JSON = False


def emit(**payload):
    if EMIT_JSON:
        sys.stdout.write("@@P " + json.dumps(payload) + "\n")
        sys.stdout.flush()


# =============================================================================
# ffmpeg helpers
# =============================================================================


def probe(path: Path) -> dict:
    """Pull the metadata we need in one ffprobe call."""
    cmd = [FFPROBE, "-v", "error", "-print_format", "json",
           "-show_streams", "-show_format", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    data = json.loads(out)

    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise SystemExit(f"No video stream found in {path}")
    audio = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)

    # avg_frame_rate is the honest number for a variable-frame-rate webcam
    # capture; r_frame_rate is often a meaningless high value like 1000/1.
    fps = Fraction(video.get("avg_frame_rate") or "0/1")
    if fps <= 0:
        fps = Fraction(video.get("r_frame_rate") or "30/1")

    duration = float(data["format"].get("duration")
                     or video.get("duration") or 0.0)

    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": fps,
        "duration": duration,
        "codec": video.get("codec_name", "?"),
        "pix_fmt": video.get("pix_fmt", "?"),
        "has_audio": audio is not None,
        "audio_codec": (audio or {}).get("codec_name"),
        # yuvj420p / color_range=pc means the camera wrote full-range levels.
        "full_range": (video.get("color_range") == "pc"
                       or str(video.get("pix_fmt", "")).startswith("yuvj")),
        # Prefer the container's own count; fall back to duration * fps.
        "est_frames": int(video.get("nb_frames") or 0)
                      or (int(round(duration * float(fps))) if duration else 0),
    }


# Progressively simpler NVENC option sets. Some driver / ffmpeg combinations
# reject the fancier flags (multipass, temporal AQ, B-frame pyramids), and
# discovering that 20 hours into a job would be miserable - so we test the
# real command against two dummy frames before committing to anything.
NVENC_TIERS = {
    "hevc_nvenc": [
        ["-spatial-aq", "1", "-aq-strength", "8", "-temporal-aq", "1",
         "-rc-lookahead", "32", "-bf", "3", "-b_ref_mode", "middle",
         "-multipass", "fullres"],
        ["-spatial-aq", "1", "-aq-strength", "8", "-temporal-aq", "1",
         "-rc-lookahead", "32", "-bf", "3"],
        ["-spatial-aq", "1", "-rc-lookahead", "32"],
        [],
    ],
    # AV1 NVENC has no temporal AQ or multipass, and flag names differ enough
    # that filtering the HEVC list would leave orphaned values behind.
    "av1_nvenc": [
        ["-spatial-aq", "1", "-aq-strength", "8", "-rc-lookahead", "32"],
        ["-spatial-aq", "1"],
        [],
    ],
}


def enc_extras(args) -> list:
    tiers = NVENC_TIERS.get(args.encoder)
    if not tiers:
        return []
    return tiers[min(getattr(args, "enc_tier", 0), len(tiers) - 1)]


def validate_encoder(args, w: int, h: int, fps: Fraction) -> None:
    """Pick the richest encoder option set this machine actually accepts."""
    if not args.encoder.endswith("nvenc"):
        args.enc_tier = 0
        return
    frames = b"\x40" * (w * h * 3 * 2)
    for tier in range(len(NVENC_TIERS[args.encoder])):
        args.enc_tier = tier
        cmd = build_encoder_cmd(args, w, h, w, h, fps, 1.0, Path("-"))
        cmd[-1] = "-"
        cmd = cmd[:-1] + ["-f", "null", "-"]
        r = subprocess.run(cmd, input=frames, capture_output=True)
        if r.returncode == 0:
            if tier:
                print(f"  encoder    using reduced option set (tier {tier}) - "
                      f"this driver rejected some tuning flags")
            return
    print("  ! hevc_nvenc could not encode a test frame - falling back to CPU")
    args.encoder = "libx265"
    args.enc_tier = 0


def encoder_available(name: str) -> bool:
    try:
        out = subprocess.run([FFMPEG, "-hide_banner", "-encoders"],
                             capture_output=True, text=True, check=True).stdout
        return name in out
    except Exception:
        return False


def build_decoder_cmd(src: Path, fps: Fraction, pre_denoise: float,
                      start_frame: int, seek: bool) -> list[str]:
    """Decode to raw rgb24 on stdout at a locked constant frame rate."""
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin",
           "-hwaccel", "auto"]

    # Fast resume: input seek is frame-accurate in modern ffmpeg but can land
    # +/-1 frame after CFR conversion. Exact resume (default) instead decodes
    # from zero and discards, costing a few minutes on a multi-hour job.
    if seek and start_frame > 0:
        cmd += ["-ss", f"{start_frame / float(fps):.6f}"]

    cmd += ["-i", str(src)]

    # fps first: normalises the VFR webcam capture to true CFR so audio stays
    # in sync. Temporal denoise then sees an evenly-spaced sequence.
    chain = [f"fps={fps.numerator}/{fps.denominator}"]
    if pre_denoise > 0:
        # Temporal-only hqdn3d (spatial terms zeroed). This is the single most
        # effective anti-flicker step: it stabilises the noise field between
        # frames BEFORE SCUNet sees it, so SCUNet makes consistent decisions
        # frame to frame. Spatial denoise is left entirely to SCUNet.
        chain.append(f"hqdn3d=0:0:{pre_denoise:g}:{pre_denoise:g}")

    cmd += ["-vf", ",".join(chain), "-an", "-sn", "-dn",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    return cmd


def build_encoder_cmd(args, in_w: int, in_h: int, out_w: int, out_h: int,
                      fps: Fraction, duration: float, dest: Path) -> list[str]:
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{in_w}x{in_h}",
           "-r", f"{fps.numerator}/{fps.denominator}",
           "-i", "pipe:0"]

    # Match the source's signal range instead of forcing limited range.
    # This camera writes yuvj420p (full range). Squeezing that into 64-940 and
    # then subsampling chroma costs a measurable ~1.6/255 darkening; staying
    # full range keeps chroma where the source had it and cuts the round-trip
    # error to 0.6/255. Verified by measurement on this exact file.
    rng = "pc" if args.color_range == "pc" else "tv"

    # One scale filter does the optional downsample AND the RGB -> YUV
    # conversion, so we never quantise twice.
    scale = "scale="
    if (out_w, out_h) != (in_w, in_h):
        scale += f"{out_w}:{out_h}:"
    scale += "flags=lanczos+accurate_rnd+full_chroma_int"
    scale += f":in_range=pc:out_color_matrix=bt709:out_range={rng}"

    cmd += ["-vf", scale]

    cq = str(args.cq)
    if args.encoder == "hevc_nvenc":
        cmd += [
            "-c:v", "hevc_nvenc", "-preset", "p7", "-tune", "hq",
            "-rc", "vbr", "-cq", cq, "-b:v", "0",
            "-profile:v", "main10", "-pix_fmt", "p010le", "-g", "150",
        ] + enc_extras(args)
    elif args.encoder == "av1_nvenc":
        cmd += [
            "-c:v", "av1_nvenc", "-preset", "p7", "-tune", "hq",
            "-rc", "vbr", "-cq", cq, "-b:v", "0",
            "-pix_fmt", "p010le", "-g", "150",
        ] + enc_extras(args)
    else:  # libx265 CPU fallback
        cmd += ["-c:v", "libx265", "-preset", "slow",
                "-crf", cq, "-pix_fmt", "yuv420p10le"]

    cmd += ["-color_primaries", "bt709", "-color_trc", "bt709",
            "-colorspace", "bt709", "-color_range", rng]
    if dest.suffix.lower() in (".mp4", ".mov", ".m4v"):
        cmd += ["-video_track_timescale", str(mp4_timescale(fps, duration))]
    cmd.append(str(dest))
    return cmd


def mp4_timescale(fps: Fraction, duration: float = 0.0) -> int:
    """Pick an MP4 timescale that represents 1/fps as a whole number of ticks.

    A nominal rate like 179/12 gives frames of 67.0391 ms, which the default
    millisecond timebase cannot express. timescale = numerator * k makes each
    frame exactly denominator * k ticks - no rounding anywhere.

    But a measured VFR average like 371550000/24852479 has a numerator far too
    large to use as a timescale: total ticks would overflow 32 bits and some
    players would choke. In that case fall back to 90000. That is safe because
    ffmpeg derives each PTS from the frame index rather than accumulating, so
    the sub-tick error stays at +/-11 us forever instead of drifting.
    """
    for k in (1000, 100, 10, 1):
        ts = fps.numerator * k
        if ts <= 1_000_000 and ts * max(duration, 1.0) < 2 ** 31:
            return ts
    return 90000


# =============================================================================
# Tiled inference with feathered blending
# =============================================================================


class Tiler:
    """Splits a frame into overlapping tiles and blends them back with a linear
    ramp across the overlap.

    Real-ESRGAN's stock tiler hard-cuts tiles at the seam, which leaves faint
    grid lines that become very visible once they sit still across thousands of
    frames. Weighted feathering removes them completely.
    """

    def __init__(self, tile: int, overlap: int):
        self.tile = tile
        self.overlap = overlap
        self._mask_cache: dict[tuple, torch.Tensor] = {}

    def _mask(self, h: int, w: int, ramp: int, device, dtype) -> torch.Tensor:
        key = (h, w, ramp, device, dtype)
        cached = self._mask_cache.get(key)
        if cached is not None:
            return cached
        ramp = max(1, min(ramp, h // 2, w // 2))
        ry = torch.ones(h, device=device, dtype=dtype)
        rx = torch.ones(w, device=device, dtype=dtype)
        ramp_vals = torch.linspace(0, 1, ramp + 2, device=device, dtype=dtype)[1:-1]
        ry[:ramp] = ramp_vals
        ry[-ramp:] = ramp_vals.flip(0)
        rx[:ramp] = ramp_vals
        rx[-ramp:] = ramp_vals.flip(0)
        mask = (ry[:, None] * rx[None, :]).view(1, 1, h, w)
        self._mask_cache[key] = mask
        return mask

    def forward(self, model, x: torch.Tensor, scale: int) -> torch.Tensor:
        _, _, h, w = x.shape
        if self.tile <= 0 or (h <= self.tile and w <= self.tile):
            return model(x).float()

        tile, ov = self.tile, self.overlap
        step = max(1, tile - ov)
        ys = list(range(0, max(h - ov, 1), step))
        xs = list(range(0, max(w - ov, 1), step))

        out = torch.zeros(x.shape[0], 3, h * scale, w * scale,
                          dtype=torch.float32, device=x.device)
        acc = torch.zeros(1, 1, h * scale, w * scale,
                          dtype=torch.float32, device=x.device)

        for y0 in ys:
            for x0 in xs:
                y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
                # Shift the window back instead of shrinking it, so every tile
                # is the same size (kinder to cudnn autotuning).
                ya, xa = max(0, y1 - tile), max(0, x1 - tile)
                patch = model(x[:, :, ya:y1, xa:x1]).float()
                ph, pw = patch.shape[-2:]
                m = self._mask(ph, pw, ov * scale, x.device, torch.float32)
                out[:, :, ya * scale:y1 * scale, xa * scale:x1 * scale] += patch * m
                acc[:, :, ya * scale:y1 * scale, xa * scale:x1 * scale] += m

        return out / acc.clamp_min(1e-6)


# =============================================================================
# Restoration engine
# =============================================================================


class Engine:
    def __init__(self, args, device):
        self.args = args
        self.device = device
        self.dtype = torch.float32 if args.fp32 else torch.float16

        print("  loading SCUNet      ...", end=" ", flush=True)
        self.denoiser = build_denoiser(args.scunet_model, device).to(self.dtype)
        print("ok")

        print("  loading Real-ESRGAN ...", end=" ", flush=True)
        self.upscaler = build_upscaler(args.esrgan_model, device).to(self.dtype)
        # Conv-heavy nets hit the tensor cores harder in NHWC layout.
        self.upscaler = self.upscaler.to(memory_format=torch.channels_last)
        print("ok")

        self.tiler_dn = Tiler(args.tile_denoise, args.overlap)
        self.tiler_up = Tiler(args.tile_upscale, args.overlap)

    @torch.inference_mode()
    def process(self, x: torch.Tensor) -> torch.Tensor:
        """(1,3,H,W) float in [0,1] -> (4H,4W,3) uint8, ready for the pipe."""
        a = self.args

        if a.denoise_strength > 0:
            xin = x.to(self.dtype)
            den = self.tiler_dn.forward(self.denoiser, xin, scale=1)
            if a.denoise_strength < 1.0:
                # Blending a little of the original back in preserves fine
                # texture (skin pores, fabric weave) that a full-strength
                # denoise flattens into plastic.
                x = den * a.denoise_strength + x * (1.0 - a.denoise_strength)
            else:
                x = den
            x = x.clamp_(0, 1)

        xin = x.to(self.dtype).contiguous(memory_format=torch.channels_last)
        out = self.tiler_up.forward(self.upscaler, xin, scale=4)

        # Pack into the exact bytes ffmpeg wants *here*, while still inside
        # inference mode. Anything produced under inference_mode is an
        # "inference tensor", and PyTorch forbids in-place ops on those once
        # execution leaves the context - doing .mul_() on the result in the
        # caller raised: "Inplace update to inference tensor outside
        # InferenceMode is not allowed". Converting in here also avoids three
        # full-size float intermediates per frame (~530 MB at 5120x2880).
        return (out.clamp_(0, 1).squeeze(0).permute(1, 2, 0)
                   .mul_(255.0).round_().to(torch.uint8).contiguous())

    def autotune(self, h: int, w: int):
        """Find the largest tile size that fits in VRAM, biggest first.
        Full-frame is fastest and seam-free, so we only tile if we must."""
        probe_in = torch.zeros(1, 3, h, w, device=self.device)

        for label, tiler, model, scale in (
            ("SCUNet", self.tiler_dn, self.denoiser, 1),
            ("Real-ESRGAN", self.tiler_up, self.upscaler, 4),
        ):
            if tiler.tile > 0:
                print(f"  {label:<12} tile={tiler.tile} (manual)")
                continue
            for candidate in (0, 768, 640, 512, 384, 256):
                tiler.tile = candidate
                try:
                    with torch.inference_mode():
                        xin = probe_in.to(self.dtype)
                        if scale == 4:
                            xin = xin.contiguous(memory_format=torch.channels_last)
                        tiler.forward(model, xin, scale=scale)
                    torch.cuda.synchronize()
                    print(f"  {label:<12} tile={'full frame' if candidate == 0 else candidate}")
                    break
                except torch.cuda.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    continue
            else:
                raise SystemExit(
                    f"{label} will not fit in VRAM even at 256px tiles. "
                    "Close other GPU applications and retry."
                )
            torch.cuda.empty_cache()

        del probe_in
        torch.cuda.empty_cache()


# =============================================================================
# Chunked streaming run
# =============================================================================


def write_progress(work: Path, frames_done: int, total: int, elapsed: float,
                   done_now: int, chunks: int, dupes: int, out_path: Path,
                   finished: bool = False):
    """Human-readable status file, rewritten at every chunk boundary.

    A 20-hour job in a console window gives you no way to answer "is this
    actually working?" from another room, and nothing survives the window being
    closed. This file does both.
    """
    rate = done_now / elapsed if elapsed > 0 else 0.0
    left = (total - frames_done) / rate if rate > 0 and total else 0

    def hm(sec):
        return f"{int(sec // 3600)}h {int(sec % 3600 // 60):02d}m"

    pct = f"{frames_done / total * 100:.1f}%" if total else "?"
    lines = [
        "AI VIDEO RESTORATION - " + ("COMPLETE" if finished else "IN PROGRESS"),
        "=" * 52,
        f"Updated     {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Frames      {frames_done:,} of {total:,}   ({pct})",
        f"Speed       {rate:.2f} frames/sec",
        f"Elapsed     {hm(elapsed)}  (this session)",
        f"Remaining   {'-' if finished else '~' + hm(left)}",
        f"Chunks      {chunks} finished",
    ]
    if dupes:
        lines.append(f"Duplicates  {dupes:,} frames reused instead of recomputed")
    lines += [
        "",
        f"Output      {out_path}",
        "",
        "It is working if the frame count here keeps climbing.",
        "Safe to close the window at any time - re-run and it resumes.",
    ]
    try:
        (work / "PROGRESS.txt").write_text("\n".join(lines) + "\n")
    except OSError:
        pass


def read_exact(stream, view: memoryview) -> int:
    """Read exactly len(view) bytes, looping over short reads.

    A pipe hands over at most one buffer per read (64 KB on Linux), and one
    5120x2880 frame is 44 MB, so short reads are the norm, not the exception.
    `view` MUST be one-dimensional: slicing a multi-dimensional memoryview
    slices rows, not bytes, which silently corrupts the offset arithmetic.
    """
    assert view.ndim == 1, "read_exact requires a flat byte view"
    n, total = 0, view.nbytes
    while n < total:
        got = stream.readinto(view[n:])
        if not got:
            return n
        n += got
    return n


def run(args):
    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        raise SystemExit(f"Input not found: {src}")

    info = probe(src)
    fps = info["fps"]
    in_w, in_h = info["width"], info["height"]
    up_w, up_h = in_w * 4, in_h * 4

    # Final delivery size. 4x is what was asked for; 2x (downsampled from the
    # 4x result) is the sharper-looking option because supersampling averages
    # away the GAN's high-frequency invention.
    if args.final_scale == 4:
        out_w, out_h = up_w, up_h
    else:
        out_w = (in_w * args.final_scale) // 2 * 2
        out_h = (in_h * args.final_scale) // 2 * 2

    if getattr(args, "color_range", "auto") == "auto":
        args.color_range = "pc" if info["full_range"] else "tv"

    total = info["est_frames"] or 0
    if args.limit:
        total = min(total, args.limit) if total else args.limit

    work = Path(args.work or (src.parent / f".{src.stem}_restore_work"))
    chunks_dir = work / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    state_path = work / "state.json"

    out_path = Path(args.output) if args.output else \
        src.parent / f"{src.stem}_RESTORED_{args.final_scale}X.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Settings fingerprint: if anything that affects pixels changed, old chunks
    # are invalid and silently mixing them would produce a seam mid-video.
    sig = json.dumps({
        "src": str(src), "size": src.stat().st_size,
        "fps": str(fps), "out": [out_w, out_h],
        "enc": args.encoder, "cq": args.cq, "range": args.color_range,
        "dn": args.denoise_strength, "pre": args.pre_denoise,
        "esr": Path(args.esrgan_model).name, "scu": Path(args.scunet_model).name,
        "fp32": args.fp32, "chunk": args.chunk_frames,
    }, sort_keys=True)

    state = {"sig": sig, "next_chunk": 0, "frames_done": 0}
    if state_path.exists():
        try:
            prev = json.loads(state_path.read_text())
            if prev.get("sig") == sig:
                state = prev
            else:
                print("! Settings changed since last run - discarding old chunks.")
                shutil.rmtree(chunks_dir, ignore_errors=True)
                chunks_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # MP4 chunks (not MKV) so the exact timescale above survives into the join.
    ext = "mp4"
    encoder_args = (args, up_w, up_h, out_w, out_h, fps, info["duration"])

    print()
    print(f"  source     {src.name}")
    print(f"  video      {in_w}x{in_h}  {float(fps):.4f} fps  {info['codec']}  "
          f"{info['duration'] / 60:.1f} min")
    print(f"  frames     {total:,}")
    print(f"  output     {out_w}x{out_h}  {args.encoder} cq{args.cq}  "
          f"{'full' if args.color_range == 'pc' else 'limited'} range")
    print(f"  audio      {info['audio_codec'] or 'none'}")
    free_gb = shutil.disk_usage(work).free / 1e9
    # Encoded chunks only - roughly what the final file will weigh. Nothing
    # like the ~700 GB a PNG frame dump of this video would need.
    need_gb = max(2.0, info["duration"] / 60 * 0.45 * (out_w * out_h) / (3840 * 2160))
    print(f"  work dir   {work}  ({free_gb:.0f} GB free, ~{need_gb:.0f} GB needed)")
    if free_gb < need_gb * 1.5:
        print("  ! Low disk space. Use --work to point at a roomier drive.")
    if state["frames_done"]:
        print(f"  RESUMING   {state['frames_done']:,} frames already done")
    print()

    emit(stage="models", total=total, frames=state["frames_done"])
    device = torch.device("cuda")
    print("Models:")
    engine = Engine(args, device)
    print("Autotuning VRAM:")
    emit(stage="autotune", total=total, frames=state["frames_done"])
    engine.autotune(in_h, in_w)
    print()

    emit(stage="encoder", total=total, frames=state["frames_done"])
    validate_encoder(args, up_w, up_h, fps)

    start_frame = state["frames_done"]
    dec_cmd = build_decoder_cmd(src, fps, args.pre_denoise, start_frame, args.seek_resume)
    dec = subprocess.Popen(dec_cmd, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, bufsize=0)

    frame_bytes = in_w * in_h * 3
    # Pinned host buffers: page-locked memory makes the PCIe copies async and
    # lets us reuse one allocation for all 37,000 frames.
    host_in = torch.empty((in_h, in_w, 3), dtype=torch.uint8).pin_memory()
    host_out = torch.empty((up_h, up_w, 3), dtype=torch.uint8).pin_memory()
    # Flat 1-D views over the same memory for the pipe I/O (see read_exact).
    view_in = memoryview(host_in.numpy().reshape(-1).data)
    view_out = memoryview(host_out.numpy().reshape(-1).data)

    # Exact resume: burn through the frames we already encoded.
    if start_frame > 0 and not args.seek_resume:
        for _ in tqdm(range(start_frame), desc="  skipping done frames",
                      unit="f", leave=False):
            if read_exact(dec.stdout, view_in) != frame_bytes:
                break

    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True

    enc = None
    chunk_idx = state["next_chunk"]
    frames_done = start_frame
    in_chunk = 0
    t0 = time.time()
    eof = False

    # Your source is VFR (frame durations swing between 64 ms and 80 ms), so
    # normalising it to CFR makes ffmpeg emit some frames twice - bit-identical
    # duplicates. The models are deterministic, so a repeated input provably
    # gives the repeated output: reuse it instead of paying for it again.
    prev_host = torch.empty((in_h, in_w, 3), dtype=torch.uint8)
    prev_valid = False
    dupes = 0

    write_progress(work, frames_done, total, 0.0, 0, chunk_idx, 0, out_path)
    stop_file = work / "STOP"
    if stop_file.exists():
        stop_file.unlink()
    last_emit = 0.0
    stopped = False

    bar = tqdm(total=total or None, initial=frames_done, unit="f",
               desc="  restoring", smoothing=0.03, dynamic_ncols=True,
               disable=EMIT_JSON)

    def close_encoder():
        nonlocal enc
        if enc is not None:
            enc.stdin.close()
            if enc.wait() != 0:
                raise SystemExit("\nffmpeg encoder failed - see output above.")
            enc = None

    try:
        while not eof:
            if args.limit and frames_done - start_frame >= args.limit:
                break

            got = read_exact(dec.stdout, view_in)
            if got != frame_bytes:
                eof = True
                break

            if enc is None:
                dest = chunks_dir / f"chunk_{chunk_idx:05d}.{ext}"
                enc = subprocess.Popen(
                    build_encoder_cmd(*encoder_args, dest),
                    stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0,
                )
                in_chunk = 0

            if prev_valid and np.array_equal(host_in.numpy(), prev_host.numpy()):
                # Identical to the frame before it - host_out still holds the
                # matching result, so just re-emit it.
                dupes += 1
            else:
                gpu = host_in.to(device, non_blocking=True)
                x = gpu.permute(2, 0, 1).unsqueeze(0).float().div_(255.0)

                try:
                    u8 = engine.process(x)
                except torch.cuda.OutOfMemoryError:
                    # Mid-run OOM (another app grabbed VRAM). Halve tiles, retry.
                    torch.cuda.empty_cache()
                    for t in (engine.tiler_dn, engine.tiler_up):
                        t.tile = 512 if t.tile <= 0 else max(256, t.tile // 2)
                        t._mask_cache.clear()
                    bar.write(f"  ! OOM - reduced tiles to "
                              f"{engine.tiler_dn.tile}/{engine.tiler_up.tile}")
                    u8 = engine.process(x)

                # Reading an inference tensor is fine; staying inside the
                # context keeps the whole hand-off unambiguously legal.
                with torch.inference_mode():
                    host_out.copy_(u8)
                np.copyto(prev_host.numpy(), host_in.numpy())
                prev_valid = True

            enc.stdin.write(view_out)

            frames_done += 1
            in_chunk += 1
            bar.update(1)

            now = time.time()
            if EMIT_JSON and now - last_emit >= 1.0:
                last_emit = now
                el = now - t0
                rate = (frames_done - start_frame) / el if el > 0 else 0.0
                emit(stage="restoring", frames=frames_done, total=total,
                     fps=round(rate, 3), elapsed=round(el, 1),
                     eta=round((total - frames_done) / rate, 1) if rate > 0 else None,
                     dupes=dupes, chunk=chunk_idx + 1,
                     chunks_total=max(1, -(-total // args.chunk_frames)) if total else 0)

            # A Stop button in the GUI drops this file rather than killing the
            # process, so the in-flight chunk is finalised properly and the
            # resume point stays exact.
            if in_chunk % 10 == 0 and stop_file.exists():
                stopped = True
                break

            if in_chunk >= args.chunk_frames:
                close_encoder()
                chunk_idx += 1
                state.update(next_chunk=chunk_idx, frames_done=frames_done)
                state_path.write_text(json.dumps(state))
                write_progress(work, frames_done, total, time.time() - t0,
                               frames_done - start_frame, chunk_idx, dupes,
                               out_path)

        close_encoder()
        if in_chunk > 0:
            chunk_idx += 1
        state.update(next_chunk=chunk_idx, frames_done=frames_done,
                     complete=not stopped)
        state_path.write_text(json.dumps(state))

        if stopped:
            bar.close()
            write_progress(work, frames_done, total, time.time() - t0,
                           frames_done - start_frame, chunk_idx, dupes, out_path)
            stop_file.unlink(missing_ok=True)
            emit(stage="stopped", frames=frames_done, total=total)
            print(f"\n  Stopped cleanly at frame {frames_done:,}. "
                  f"Start again to resume from here.")
            dec.stdout.close()
            dec.terminate()
            return

    except KeyboardInterrupt:
        bar.close()
        close_encoder()
        # The partial chunk is valid video; keep it and resume after it.
        if in_chunk > 0:
            chunk_idx += 1
        state.update(next_chunk=chunk_idx, frames_done=frames_done)
        state_path.write_text(json.dumps(state))
        write_progress(work, frames_done, total, time.time() - t0,
                       frames_done - start_frame, chunk_idx, dupes, out_path)
        print(f"\nStopped. {frames_done:,} frames saved.")
        print(f"Re-run the same command to resume from frame {frames_done:,}.")
        return
    finally:
        bar.close()
        dec.stdout.close()
        dec.terminate()

    elapsed = time.time() - t0
    done_now = frames_done - start_frame
    print(f"\n  processed {done_now:,} frames in {elapsed / 3600:.2f} h "
          f"({done_now / max(elapsed, 1):.2f} fps)")
    if dupes:
        print(f"  skipped {dupes:,} duplicate frames "
              f"({dupes / max(done_now, 1) * 100:.1f}% saved from VFR conversion)")

    emit(stage="joining", frames=frames_done, total=total)
    mux(chunks_dir, src, out_path, info, args)

    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)

    size_gb = out_path.stat().st_size / 1e9
    emit(stage="done", frames=frames_done, total=total,
         output=str(out_path), size_gb=round(size_gb, 2))
    print(f"\n  DONE -> {out_path}  ({size_gb:.2f} GB)")


def mux(chunks_dir: Path, src: Path, out_path: Path, info: dict, args):
    """Concatenate chunks with stream copy and attach the original audio."""
    chunks = sorted(chunks_dir.glob("chunk_*.mp4"))
    if not chunks:
        raise SystemExit("No chunks were produced.")

    listing = chunks_dir / "chunks.txt"
    # Relative names + cwd avoids every Windows path-escaping problem the
    # concat demuxer has with backslashes and drive letters.
    listing.write_text("".join(f"file '{c.name}'\n" for c in chunks))

    print(f"  joining {len(chunks)} chunks (stream copy, no re-encode)...")

    def build(audio_args):
        return [FFMPEG, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-f", "concat", "-safe", "0", "-i", listing.name,
                "-i", str(src),
                "-map", "0:v:0", *(["-map", "1:a:0"] if info["has_audio"] else []),
                "-c:v", "copy", *audio_args,
                "-video_track_timescale", str(mp4_timescale(info["fps"], info["duration"])),
                "-movflags", "+faststart", str(out_path)]

    audio = ["-c:a", "copy"] if info["has_audio"] else []
    r = subprocess.run(build(audio), cwd=chunks_dir,
                       capture_output=True, text=True)
    if r.returncode != 0 and info["has_audio"]:
        # Some source codecs (e.g. PCM) cannot live in MP4; transcode instead.
        print("  audio stream copy rejected by MP4 - re-encoding to AAC 256k")
        r = subprocess.run(build(["-c:a", "aac", "-b:a", "256k"]),
                           cwd=chunks_dir, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"Final mux failed:\n{r.stderr}")


# =============================================================================
# CLI
# =============================================================================


def main():
    p = argparse.ArgumentParser(
        description="Local AI video restoration: SCUNet + Real-ESRGAN 4x + NVENC",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("input", help="source video file")
    p.add_argument("-o", "--output", help="output path (default: <name>_RESTORED_4X.mp4)")

    q = p.add_argument_group("quality")
    q.add_argument("--denoise-strength", type=float, default=0.85,
                   help="SCUNet blend, 0=off 1=full. <1 keeps natural texture")
    q.add_argument("--pre-denoise", type=float, default=4.0,
                   help="ffmpeg temporal pre-denoise strength, 0=off. Reduces flicker")
    q.add_argument("--final-scale", type=int, default=4, choices=[2, 3, 4],
                   help="delivery scale; 2 = supersampled from 4x, cleaner")
    q.add_argument("--cq", type=int, default=19,
                   help="NVENC quality, lower=better. 16-20 is visually lossless")
    q.add_argument("--fp32", action="store_true",
                   help="full precision (2x slower, no visible gain)")
    q.add_argument("--color-range", default="auto", choices=["auto", "tv", "pc"],
                   help="auto matches the source; pc is more accurate for "
                        "full-range (yuvj) cameras, tv is safest on old players")

    m = p.add_argument_group("models")
    m.add_argument("--scunet-model", default=str(ROOT / "models/SCUNet/scunet_color_real_psnr.pth"))
    m.add_argument("--esrgan-model", default=str(ROOT / "models/RealESRGAN/RealESRGAN_x4plus.pth"))

    r = p.add_argument_group("runtime")
    r.add_argument("--encoder", default="hevc_nvenc",
                   choices=["hevc_nvenc", "av1_nvenc", "libx265"])
    r.add_argument("--tile-denoise", type=int, default=0, help="0 = autotune")
    r.add_argument("--tile-upscale", type=int, default=0, help="0 = autotune")
    r.add_argument("--overlap", type=int, default=48, help="tile overlap in px")
    r.add_argument("--chunk-frames", type=int, default=1500,
                   help="resume granularity (~100 s of video)")
    r.add_argument("--limit", type=int, default=0,
                   help="process only N frames (for tests)")
    r.add_argument("--work", help="scratch dir (default: hidden dir next to input)")
    r.add_argument("--keep-work", action="store_true", help="keep chunks after muxing")
    r.add_argument("--json-progress", action="store_true",
                   help="emit machine-readable progress on stdout (used by the GUI)")
    r.add_argument("--seek-resume", action="store_true",
                   help="fast resume by seeking (may shift by 1 frame)")

    args = p.parse_args()
    args.enc_tier = 0

    global EMIT_JSON
    EMIT_JSON = args.json_progress

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is not available.\n"
            "On an RTX 5070 (Blackwell, sm_120) you need a cu128 or newer\n"
            "PyTorch build. Run setup.ps1, then verify_setup.py."
        )

    cap = torch.cuda.get_device_capability()
    if cap[0] >= 12 and f"sm_{cap[0]}{cap[1]}" not in torch.cuda.get_arch_list():
        raise SystemExit(
            f"This PyTorch build has no sm_{cap[0]}{cap[1]} kernels "
            f"(has: {', '.join(torch.cuda.get_arch_list())}).\n"
            "Reinstall with the cu128 index - see setup.ps1."
        )

    for path, what in ((args.scunet_model, "SCUNet"), (args.esrgan_model, "Real-ESRGAN")):
        if not Path(path).exists():
            raise SystemExit(f"{what} weights missing: {path}\nRun setup.ps1 to download.")

    if args.encoder.endswith("nvenc") and not encoder_available(args.encoder):
        print(f"! {args.encoder} unavailable in this ffmpeg build - using libx265 (CPU).")
        args.encoder = "libx265"

    print(f"\n  GPU  {torch.cuda.get_device_name(0)}  "
          f"({torch.cuda.get_device_properties(0).total_memory / 1e9:.0f} GB, sm_{cap[0]}{cap[1]})")
    print(f"  torch {torch.__version__}  cuda {torch.version.cuda}")

    run(args)


if __name__ == "__main__":
    main()
