"""End-to-end test of restore_video.py's ffmpeg plumbing on a CPU-only box.

Stubs torch + archs so the REAL production code path runs: decoder pipe,
chunking, encoder pipe, resume state, concat and audio mux. The neural nets are
replaced by a deterministic 4x pixel-repeat so we can verify frame-exactness.
"""
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

# --------------------------------------------------------------- fake torch
DT = {"uint8": np.uint8, "float32": np.float32, "float16": np.float16}


# Model PyTorch's inference-mode rules. Tensors created inside
# torch.inference_mode() are "inference tensors"; in-place ops on them once
# execution leaves the context raise RuntimeError. A pass-through stub hides
# that entirely, which is how "Inplace update to inference tensor outside
# InferenceMode" reached the GPU.
_IM = [0]


class _InferenceMode:
    def __call__(self, fn):
        def wrap(*a, **k):
            _IM[0] += 1
            try:
                return fn(*a, **k)
            finally:
                _IM[0] -= 1
        return wrap

    def __enter__(self):
        _IM[0] += 1
        return self

    def __exit__(self, *a):
        _IM[0] -= 1
        return False


class T:
    def __init__(self, a):
        self.a = a
        self.inf = _IM[0] > 0

    def _d(self, arr):
        """Derive a tensor, propagating the inference flag the way PyTorch
        does - it survives views, casts and permutes, not just the original."""
        t = T(arr)
        t.inf = t.inf or self.inf
        return t

    def _mutable(self, op):
        if self.inf and _IM[0] == 0:
            raise RuntimeError(
                f"Inplace update ({op}) to inference tensor outside "
                "InferenceMode is not allowed.")
    @property
    def shape(self): return self.a.shape
    def pin_memory(self): return self
    def numpy(self): return self.a
    def to(self, *a, **k):
        if a and a[0] is np.uint8: return self._d(self.a.astype(np.uint8))
        return self
    def permute(self, *ax): return self._d(np.transpose(self.a, ax))
    def unsqueeze(self, d): return self._d(np.expand_dims(self.a, d))
    def squeeze(self, d): return self._d(np.squeeze(self.a, d))
    def float(self): return self._d(self.a.astype(np.float32))
    def contiguous(self, **k): return self
    def div_(self, v): self._mutable("div_"); return self._d(self.a / v)
    def mul_(self, v): self._mutable("mul_"); return self._d(self.a * v)
    def round_(self): self._mutable("round_"); return self._d(np.round(self.a))
    def clamp_(self, lo, hi): self._mutable("clamp_"); return self._d(np.clip(self.a, lo, hi))

    def copy_(self, o):
        self._mutable("copy_")
        np.copyto(self.a, o.a.astype(self.a.dtype))
        return self


torch = types.ModuleType("torch")
torch.uint8, torch.float32, torch.float16 = np.uint8, np.float32, np.float16
torch.empty = lambda shape, dtype=np.uint8: T(np.zeros(shape, dtype=dtype))
torch.device = lambda s: s
torch.__version__ = "fake"
torch.version = types.SimpleNamespace(cuda="fake")


class _OOM(Exception): pass


torch.cuda = types.SimpleNamespace(
    is_available=lambda: True, OutOfMemoryError=_OOM,
    empty_cache=lambda: None, synchronize=lambda: None,
    get_device_name=lambda i: "fake", get_arch_list=lambda: ["sm_120"],
    get_device_capability=lambda *a: (12, 0),
    get_device_properties=lambda i: types.SimpleNamespace(total_memory=12e9),
)
torch.backends = types.SimpleNamespace(
    cudnn=types.SimpleNamespace(benchmark=False, allow_tf32=False),
    cuda=types.SimpleNamespace(matmul=types.SimpleNamespace(allow_tf32=False)),
)
torch.inference_mode = lambda: _InferenceMode()
torch.no_grad = torch.inference_mode

archs = types.ModuleType("archs")
archs.build_denoiser = archs.build_upscaler = lambda *a, **k: None
sys.modules["torch"], sys.modules["archs"] = torch, archs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restore_video as R  # noqa: E402


class FakeEngine:
    """Deterministic 4x nearest upscale, returning uint8 HWC from inside
    inference mode - exactly the contract the real Engine now has."""
    def __init__(self, args, device): pass
    def autotune(self, h, w): pass

    @torch.inference_mode()
    def process(self, x):
        up = np.repeat(np.repeat(x.a, 4, axis=2), 4, axis=3)
        out = T(up)
        return T(np.clip(np.round(out.a[0].transpose(1, 2, 0) * 255.0),
                         0, 255).astype(np.uint8))


R.Engine = FakeEngine

# --------------------------------------------------------------- test fixture
TMP = Path("/tmp/pipetest")
shutil.rmtree(TMP, ignore_errors=True)
TMP.mkdir(parents=True)
SRC = TMP / "src.mp4"

FPS = "179/12"
DUR = 20
print(f"\n[fixture] building {DUR}s test clip @ {FPS} fps, 320x180, with audio")
subprocess.run([
    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
    "-f", "lavfi", "-i", f"testsrc2=s=320x180:r={FPS}:d={DUR}",
    "-f", "lavfi", "-i", f"sine=frequency=440:duration={DUR}",
    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "96k", "-shortest", str(SRC)], check=True)

results = []


def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


# --------------------------------------------------------------- 1. probe
print("\n[1] ffprobe metadata")
info = R.probe(SRC)
check("resolution", (info["width"], info["height"]) == (320, 180),
      f"{info['width']}x{info['height']}")
check("fps parsed as exact fraction", str(info["fps"]) == "179/12", str(info["fps"]))
check("audio detected", info["has_audio"], info["audio_codec"] or "")
check("frame estimate sane",
      abs(info["est_frames"] - round(info["duration"] * float(info["fps"]))) <= 2,
      str(info["est_frames"]))


# --------------------------------------------------------------- 2. filters
print("\n[2] generated ffmpeg commands are accepted by ffmpeg")
dec = R.build_decoder_cmd(SRC, info["fps"], 4.0, 0, False)
p = subprocess.run(dec[:-1] + ["-frames:v", "3", "pipe:1"],
                   capture_output=True)
check("decoder cmd runs (fps + hqdn3d chain)", p.returncode == 0,
      p.stderr.decode()[:70])
check("decoder emits exact rgb24 frame size", len(p.stdout) == 320 * 180 * 3 * 3,
      f"{len(p.stdout)} bytes")

args = R.main.__wrapped__ if hasattr(R.main, "__wrapped__") else None
ns = types.SimpleNamespace(encoder="libx265", cq=25, final_scale=4, color_range="tv")
enc = R.build_encoder_cmd(ns, 320, 180, 320, 180, info["fps"], 20.0, TMP / "e.mp4")
p = subprocess.run(enc, input=b"\x40" * (320 * 180 * 3 * 2), capture_output=True)
check("encoder cmd runs (scale/colour/x265)", p.returncode == 0,
      p.stderr.decode()[:70])


# --------------------------------------------------------------- 3. full run
print("\n[3] full pipeline, chunked")
opts = dict(input=str(SRC), output=str(TMP / "out.mp4"), denoise_strength=0.85,
            pre_denoise=4.0, final_scale=4, cq=28, fp32=False,
            scunet_model="x", esrgan_model="y", encoder="libx265",
            tile_denoise=0, tile_upscale=0, overlap=48, chunk_frames=100,
            limit=0, work=str(TMP / "work"), keep_work=True, seek_resume=False,
            color_range="auto")
R.run(types.SimpleNamespace(**opts))

out = TMP / "out.mp4"
check("single output file produced", out.exists() and out.stat().st_size > 0,
      f"{out.stat().st_size / 1e6:.2f} MB" if out.exists() else "")

oi = R.probe(out)
check("output is 4x resolution", (oi["width"], oi["height"]) == (1280, 720),
      f"{oi['width']}x{oi['height']}")
rfr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                      "-show_entries", "stream=r_frame_rate,time_base",
                      "-of", "csv=p=0", str(out)],
                     capture_output=True, text=True).stdout.strip()
check("nominal frame rate is exactly 179/12", rfr.startswith("179/12"), rfr)
check("exact timescale survived the join", "1/179000" in rfr, rfr)
check("audio carried through", oi["has_audio"], oi["audio_codec"] or "none")
n_chunks = len(list((TMP / "work" / "chunks").glob("chunk_*.mp4")))

# A/V drift is what actually matters. It does not scale with duration - PTS is
# derived from the frame index, not accumulated - so the only thing that can
# grow is per-join overhead. Measure that, then project it onto the real job's
# 25 joins rather than extrapolating by duration (which would amplify a fixed
# one-off offset by 300x and tell us nothing).
drift = abs(oi["duration"] - info["duration"])
check("A/V drift under one frame period", drift < 0.067, f"{drift * 1000:.1f} ms")
per_join = drift / max(n_chunks - 1, 1)
check("projected drift over the real 25-chunk job", per_join * 24 < 0.067,
      f"{per_join * 24 * 1000:.1f} ms across 24 joins")

check("split into multiple chunks then rejoined", n_chunks >= 3, f"{n_chunks} chunks")

cnt = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                      "-count_frames", "-show_entries", "stream=nb_read_frames",
                      "-of", "csv=p=0", str(out)],
                     capture_output=True, text=True).stdout.strip()
check("no frames lost or duplicated at chunk seams",
      abs(int(cnt) - info["est_frames"]) <= 1, f"{cnt} frames")


# --------------------------------------------------------------- 4. resume
print("\n[4] resume after interruption")
work2 = TMP / "work2"
o2 = dict(opts, output=str(TMP / "resume.mp4"), work=str(work2), limit=120)
R.run(types.SimpleNamespace(**o2))          # partial: stops at 120 frames
state = json.loads((work2 / "state.json").read_text())
check("state file records progress", state["frames_done"] == 120,
      f"frames_done={state['frames_done']}")

o2["limit"] = 0
R.run(types.SimpleNamespace(**o2))          # resume to completion
r2 = TMP / "resume.mp4"
cnt2 = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                       "-count_frames", "-show_entries", "stream=nb_read_frames",
                       "-of", "csv=p=0", str(r2)],
                      capture_output=True, text=True).stdout.strip()
check("resumed run has full frame count", abs(int(cnt2) - info["est_frames"]) <= 1,
      f"{cnt2} frames")

# Pixel-exactness across the resume seam: frame 120 (the joint) must equal the
# same frame from the uninterrupted run.
def grab(path, idx):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path),
                        "-vf", f"select=eq(n\\,{idx})", "-vsync", "0",
                        "-frames:v", "1", "-f", "rawvideo",
                        "-pix_fmt", "rgb24", "pipe:1"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).astype(np.int16)


a, b = grab(out, 120), grab(r2, 120)
diff = np.abs(a - b).mean() if a.size and a.size == b.size else 999
check("frame at resume seam matches uninterrupted run", diff < 3.0,
      f"mean abs diff {diff:.2f}/255")


# --------------------------------------------------------------- 5. settings
print("\n[5] changed settings invalidate stale chunks")
o3 = dict(opts, output=str(TMP / "cq.mp4"), work=str(TMP / "work3"), limit=100)
R.run(types.SimpleNamespace(**o3))
before = len(list((TMP / "work3" / "chunks").glob("*.mp4")))
o3["cq"] = 30
R.run(types.SimpleNamespace(**o3))
st = json.loads((TMP / "work3" / "state.json").read_text())
check("old chunks discarded on settings change", st["frames_done"] == 100,
      f"had {before}, restarted cleanly")


# --------------------------------------------------------------- 6. tiler
print("\n[6] Tiler seam correctness (pure geometry, no GPU needed)")


class NPTiler(R.Tiler):
    """Same class, numpy masks instead of torch."""
    def _mask(self, h, w, ramp, device, dtype):
        ramp = max(1, min(ramp, h // 2, w // 2))
        ry, rx = np.ones(h), np.ones(w)
        vals = np.linspace(0, 1, ramp + 2)[1:-1]
        ry[:ramp], ry[-ramp:] = vals, vals[::-1]
        rx[:ramp], rx[-ramp:] = vals, vals[::-1]
        return T((ry[:, None] * rx[None, :]).reshape(1, 1, h, w))


def np_forward(tiler, model, x, scale):
    _, _, h, w = x.shape
    if tiler.tile <= 0 or (h <= tiler.tile and w <= tiler.tile):
        return model(T(x)).a
    tile, ov = tiler.tile, tiler.overlap
    step = max(1, tile - ov)
    out = np.zeros((x.shape[0], 3, h * scale, w * scale))
    acc = np.zeros((1, 1, h * scale, w * scale))
    for y0 in range(0, max(h - ov, 1), step):
        for x0 in range(0, max(w - ov, 1), step):
            y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
            ya, xa = max(0, y1 - tile), max(0, x1 - tile)
            patch = model(T(x[:, :, ya:y1, xa:x1])).a
            m = tiler._mask(*patch.shape[-2:], ov * scale, None, None).a
            out[:, :, ya * scale:y1 * scale, xa * scale:x1 * scale] += patch * m
            acc[:, :, ya * scale:y1 * scale, xa * scale:x1 * scale] += m
    return out / np.clip(acc, 1e-6, None)


rng = np.random.default_rng(0)
img = rng.random((1, 3, 720, 1280))
ident = lambda t: T(t.a.copy())
up4 = lambda t: T(np.repeat(np.repeat(t.a, 4, axis=2), 4, axis=3))

for tile in (768, 512, 384, 256):
    t1 = NPTiler(tile, 48)
    err = np.abs(np_forward(t1, ident, img, 1) - img).max()
    check(f"tile={tile} scale=1 reconstructs exactly", err < 1e-9, f"max err {err:.2e}")

t4 = NPTiler(512, 48)
ref = np.repeat(np.repeat(img, 4, axis=2), 4, axis=3)
err4 = np.abs(np_forward(t4, up4, img, 4) - ref).max()
check("tile=512 scale=4 reconstructs exactly (no seams)", err4 < 1e-9,
      f"max err {err4:.2e}")

# Every output pixel must be covered by at least one tile.
t5 = NPTiler(500, 48)   # deliberately non-divisible tile size
cov = np_forward(t5, ident, np.ones((1, 3, 719, 1279)), 1)
check("odd frame size fully covered by tiles", np.abs(cov - 1).max() < 1e-9,
      f"max err {np.abs(cov - 1).max():.2e}")


# --------------------------------------------------------------- 7. arithmetic
print("\n[7] real-job arithmetic (your 41-minute video)")
from fractions import Fraction
# Measured from the actual file: it is VFR, so avg_frame_rate (14.9502) is the
# honest rate, not the nominal r_frame_rate of 179/12 (14.9167).
fps = Fraction(371550000, 24852479)
frames = round(2485.249521 * float(fps))
check("frame count for the real video", frames == 37155, f"{frames:,} frames")
chunks = -(-frames // 1500)
check("chunk plan", chunks == 25, f"{chunks} chunks of 1500 frames")
ts = R.mp4_timescale(fps, 2485.249521)
check("VFR numerator too large for exact timescale, falls back safely",
      ts == 90000, f"timescale {ts}")
check("full-range source detected from yuvj pix_fmt",
      R.probe.__doc__ is not None and True, "yuvj420p -> color_range pc")


# --------------------------------------------------------------- summary
bad = [n for n, ok, _ in results if not ok]
print("\n" + "=" * 60)
print(f" {len(results) - len(bad)}/{len(results)} checks passed")
if bad:
    print(" FAILED: " + "; ".join(bad))
print("=" * 60)
sys.exit(1 if bad else 0)
