#!/usr/bin/env python
"""
gui.py - RestoreForge AI desktop front end.

Runs on the SYSTEM Python and imports only the standard library plus tkinter,
because it has to work *before* the virtual environment exists - installing
that environment is one of its jobs. Everything heavy (torch, the models, the
pipeline) runs in venv\\Scripts\\python.exe as a subprocess.

    py -3.11 gui.py
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as cfg  # noqa: E402

ROOT = cfg.ROOT
VENV_PY = cfg.VENV_PY
STAMP = cfg.STAMP
NO_WINDOW = cfg.NO_WINDOW

# ---- palette ---------------------------------------------------------------
# Near-black graphite with a restrained cyan accent. Contrast of body text on
# the panel background is ~11:1, comfortably past WCAG AA.
BG = "#08090b"
PANEL = "#0b0d10"
CARD = "#111419"
CARD_HI = "#161a20"
LINE = "#1d222a"
LINE_HI = "#2b323d"
INK = "#e9edf2"
SUB = "#98a2b3"
FAINT = "#667085"
ACC = "#22d3ee"
ACC_DIM = "#0e3a44"
ACC_TX = "#04222a"
BLUE = "#60a5fa"
VIOLET = "#a78bfa"
GOOD = "#34d399"
GOOD_BG = "#0d2a22"
WARN = "#fbbf24"
WARN_BG = "#2c2411"
BAD = "#f87171"
BAD_BG = "#2d1517"

F = "Segoe UI"
MONO = "Consolas"

CHUNK_FRAMES = 1500  # must match restore_video.py's default


# =============================================================================
# Pure helpers - no Tk, unit-testable
# =============================================================================


def fmt_hms(seconds) -> str:
    if seconds is None or seconds < 0:
        return "--:--:--"
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def fmt_short(seconds) -> str:
    """'17h 12m' - easier to scan than 17:12:05."""
    if seconds is None or seconds < 0:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"


def fmt_finish(seconds) -> str:
    if seconds is None or seconds < 0:
        return ""
    end = datetime.now() + timedelta(seconds=seconds)
    same = end.date() == datetime.now().date()
    return "done by " + end.strftime("%H:%M" if same else "%a %H:%M")


def parse_progress(line: str):
    if not line.startswith("@@P "):
        return None
    try:
        return json.loads(line[4:])
    except (ValueError, TypeError):
        return None


def project_total(frames_done: int, total: int, elapsed: float):
    if frames_done <= 0 or elapsed <= 0 or total <= 0:
        return None
    return elapsed / frames_done * total


def classify(line: str):
    low = line.lower()
    if "[fail]" in low or "traceback" in low or "error" in low or low.startswith("die"):
        return "err"
    if "[ok]" in low or "passed" in low or "complete" in low:
        return "ok"
    if "[warn]" in low or line.strip().startswith("!"):
        return "warn"
    if line.startswith("===") or line.startswith("$"):
        return "head"
    return None


def chunk_position(frames_done: int, total: int, chunk_frames: int = CHUNK_FRAMES):
    """(current chunk, total chunks) for a frame position, 1-based."""
    if total <= 0 or chunk_frames <= 0:
        return (0, 0)
    total_chunks = max(1, -(-total // chunk_frames))
    current = min(total_chunks, max(1, -(-max(frames_done, 1) // chunk_frames)))
    return (current, total_chunks)


def probe_video(path: Path):
    """Video facts via ffprobe. No torch, no numpy - safe on system Python."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True, timeout=60,
            creationflags=NO_WINDOW).stdout
        d = json.loads(out)
        v = next(s for s in d["streams"] if s["codec_type"] == "video")
        dur = float(d["format"].get("duration", 0))
        num, den = (v.get("avg_frame_rate") or "0/1").split("/")
        fps = float(num) / float(den) if float(den) else 0.0
        frames = int(v.get("nb_frames") or 0) or int(round(dur * fps))
        pix = str(v.get("pix_fmt", "?"))
        return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps,
                "dur": dur, "frames": frames, "codec": v.get("codec_name", "?"),
                "pix_fmt": pix,
                "full_range": v.get("color_range") == "pc" or pix.startswith("yuvj"),
                "audio": any(s["codec_type"] == "audio" for s in d["streams"])}
    except Exception:
        return None


ENV_PROBE = (
    "import json,torch;"
    "d=torch.cuda.is_available();"
    "c=torch.cuda.get_device_capability(0) if d else (0,0);"
    "print(json.dumps({"
    "'torch':torch.__version__,'cuda':torch.version.cuda,'avail':d,"
    "'name':torch.cuda.get_device_name(0) if d else '',"
    "'vram':round(torch.cuda.get_device_properties(0).total_memory/1e9) if d else 0,"
    "'arch':'sm_%d%d'%c if d else '',"
    "'arch_list':list(torch.cuda.get_arch_list())}))"
)


def parse_env(stdout: str):
    """Pull the JSON line out of the environment probe's output."""
    for line in reversed((stdout or "").splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except ValueError:
                continue
    return None


def env_summary(env: dict | None):
    """(text, level) for the GPU readiness row. level: ok | warn | bad."""
    if not env:
        return ("GPU not detected yet", "warn")
    if not env.get("avail"):
        return ("No CUDA GPU visible to PyTorch", "bad")
    arch = env.get("arch", "")
    # is_available() returning True is not enough: a build without kernels for
    # this architecture loads fine and then fails on every kernel launch.
    if arch and arch not in (env.get("arch_list") or []):
        return (f"{env.get('name', 'GPU')} needs {arch} kernels - this build lacks them", "bad")
    return (f"{env.get('name', 'GPU')} · {env.get('vram', 0)} GB · {arch}", "ok")


# =============================================================================
# Drawn widgets. Tk has no rounded corners, so cards and pills are painted on a
# Canvas. They hold only canvas items - never child widgets - which keeps them
# free of the layout problems a canvas-hosted Frame introduces.
# =============================================================================


def round_rect(cv, x1, y1, x2, y2, r, **kw):
    r = min(r, abs(x2 - x1) / 2, abs(y2 - y1) / 2)
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class StatCard(tk.Canvas):
    """Small caps label above a large monospaced value."""

    def __init__(self, parent, title, value="-", note="", w=190, h=92):
        super().__init__(parent, width=w, height=h, bg=BG,
                         highlightthickness=0, bd=0)
        # NEVER name these _w / _h. tkinter.Misc keeps the widget's Tcl pathname
        # in self._w; assigning a number there makes every later canvas call
        # address a command named "190" instead of the widget.
        self._cw, self._ch = w, h
        self._title, self._value, self._note = title, value, note
        self.bind("<Configure>", self._redraw)
        self._draw()

    def _redraw(self, ev):
        self._cw, self._ch = ev.width, ev.height
        self._draw()

    def _draw(self):
        self.delete("all")
        round_rect(self, 1, 1, self._cw - 2, self._ch - 2, 10,
                   fill=CARD, outline=LINE)
        self.create_text(15, 19, text=self._title.upper(), anchor="w",
                         fill=FAINT, font=(F, 8, "bold"))
        self.create_text(15, 48, text=self._value, anchor="w", tags="v",
                         fill=INK, font=(MONO, 17, "bold"))
        self.create_text(15, 73, text=self._note, anchor="w", tags="n",
                         fill=SUB, font=(F, 8))

    def set(self, value=None, note=None):
        if value is not None:
            self._value = str(value)
            self.itemconfigure("v", text=self._value)
        if note is not None:
            self._note = str(note)
            self.itemconfigure("n", text=self._note)


class Pill(tk.Canvas):
    """Rounded status chip."""

    def __init__(self, parent, text="", fg=SUB, bg=CARD_HI, bgc=BG, w=150, h=24):
        super().__init__(parent, width=w, height=h, bg=bgc,
                         highlightthickness=0, bd=0)
        self._ch = h
        self.set(text, fg, bg)

    def set(self, text, fg=SUB, bg=CARD_HI):
        self.delete("all")
        w = max(74, len(text) * 7 + 28)
        self.configure(width=w)
        round_rect(self, 1, 1, w - 2, self._ch - 2, (self._ch - 2) / 2,
                   fill=bg, outline=bg)
        self.create_text(w / 2, self._ch / 2, text=text, fill=fg,
                         font=(F, 9, "bold"))


class Card(tk.Frame):
    """Panel with a hairline border and an optional small-caps title."""

    def __init__(self, parent, title=None, sub=None):
        super().__init__(parent, bg=CARD, highlightbackground=LINE,
                         highlightcolor=LINE, highlightthickness=1, bd=0)
        if title:
            head = tk.Frame(self, bg=CARD)
            head.pack(fill="x", padx=16, pady=(13, 0))
            tk.Label(head, text=title.upper(), bg=CARD, fg=SUB,
                     font=(F, 8, "bold")).pack(side="left")
            if sub:
                tk.Label(head, text=sub, bg=CARD, fg=FAINT,
                         font=(F, 8)).pack(side="right")
        self.body = tk.Frame(self, bg=CARD)
        self.body.pack(fill="both", expand=True, padx=16, pady=(10, 15))


class Btn(tk.Button):
    """Flat button. kind: primary | ghost | danger."""

    def __init__(self, parent, text, command, kind="ghost", bg=CARD, **kw):
        style = {
            "primary": dict(fg=ACC_TX, back=ACC, act="#67e8f9", bd_=ACC),
            "ghost": dict(fg=INK, back=CARD_HI, act="#1d232b", bd_=LINE_HI),
            "danger": dict(fg=BAD, back=CARD_HI, act=BAD_BG, bd_=LINE_HI),
        }[kind]
        super().__init__(parent, text=text, command=command, bd=0, relief="flat",
                         bg=style["back"], fg=style["fg"],
                         activebackground=style["act"], activeforeground=style["fg"],
                         font=(F, 9, "bold" if kind == "primary" else "normal"),
                         padx=16, pady=8, cursor="hand2",
                         highlightthickness=1, highlightbackground=style["bd_"],
                         highlightcolor=ACC,           # visible keyboard focus
                         takefocus=1,
                         disabledforeground="#3f4753", **kw)
        self._kind = kind


class NavItem(tk.Frame):
    def __init__(self, parent, text, command):
        super().__init__(parent, bg=PANEL, cursor="hand2")
        self.command = command
        self.lab = tk.Label(self, text=text, bg=PANEL, fg=SUB, font=(F, 10),
                            anchor="w", padx=14, pady=8)
        self.lab.pack(fill="x")
        for w in (self, self.lab):
            w.bind("<Button-1>", lambda _e: self.command())

    def select(self, on):
        self.lab.configure(bg=CARD if on else PANEL, fg=ACC if on else SUB,
                           font=(F, 10, "bold" if on else "normal"))
        self.configure(bg=CARD if on else PANEL)


class Tip:
    """Hover tooltip for advanced settings."""

    def __init__(self, widget, text):
        self.widget, self.text, self.win = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<FocusIn>", self._show, add="+")
        widget.bind("<FocusOut>", self._hide, add="+")

    def _show(self, _e=None):
        if self.win is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.win = tk.Toplevel(self.widget)
            self.win.wm_overrideredirect(True)
            self.win.wm_geometry(f"+{x}+{y}")
            tk.Label(self.win, text=self.text, bg=CARD_HI, fg=INK,
                     font=(F, 8), justify="left", wraplength=320,
                     padx=10, pady=7, bd=0,
                     highlightbackground=LINE_HI, highlightthickness=1).pack()
        except tk.TclError:
            self.win = None

    def _hide(self, _e=None):
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None


# =============================================================================
# Application
# =============================================================================


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.proc = None
        self.q: queue.Queue = queue.Queue()
        self.info = None
        self.env = None
        self.t_start = 0.0
        self.running = False
        self.mode = ""
        self.last = {}
        self.page = "restore"
        self.settings = cfg.load_settings()

        root.title(f"{cfg.APP_NAME} - {cfg.APP_TAGLINE}")
        root.configure(bg=BG)
        root.geometry("1240x860")
        root.minsize(1080, 760)

        ttk.Style().configure("P.Horizontal.TProgressbar", background=ACC,
                              troughcolor="#161a20", borderwidth=0, thickness=8)
        self._build()

        saved = (self.settings.get("video") or "").strip()
        self.set_video(Path(saved) if saved and Path(saved).exists() else None)
        self.refresh_state()
        self.root.after(100, self._drain)
        self.root.after(300, self.probe_env)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.bind("<F5>", lambda _e: self.run_verify())
        root.bind("<Escape>", lambda _e: self.stop() if self.running else None)

    # ---------------------------------------------------------------- layout
    def _build(self):
        side = tk.Frame(self.root, bg=PANEL, width=214)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(self.root, bg=LINE, width=1).pack(side="left", fill="y")

        brand = tk.Frame(side, bg=PANEL)
        brand.pack(fill="x", pady=(20, 6), padx=16)
        tk.Label(brand, text="◆", bg=PANEL, fg=ACC, font=(F, 13)).pack(side="left")
        tk.Label(brand, text="  RestoreForge", bg=PANEL, fg=INK,
                 font=(F, 12, "bold")).pack(side="left")
        tk.Label(side, text=f"v{cfg.VERSION}  ·  LOCAL ONLY", bg=PANEL, fg=FAINT,
                 font=(MONO, 7)).pack(anchor="w", padx=17, pady=(0, 16))

        self.nav = {}
        for group, items in (("WORK", [("restore", "Restore"),
                                       ("activity", "Activity log")]),
                             ("SYSTEM", [("environment", "Environment"),
                                         ("help", "Help")])):
            tk.Label(side, text=group, bg=PANEL, fg=FAINT, font=(F, 7, "bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(10, 4))
            for key, label in items:
                it = NavItem(side, label, lambda k=key: self.show(k))
                it.pack(fill="x", padx=8, pady=1)
                self.nav[key] = it

        foot = tk.Frame(side, bg=PANEL)
        foot.pack(side="bottom", fill="x", padx=16, pady=16)
        self.lbl_disk = tk.Label(foot, text="", bg=PANEL, fg=FAINT, font=(MONO, 7),
                                 anchor="w", justify="left")
        self.lbl_disk.pack(fill="x")

        main = tk.Frame(self.root, bg=BG)
        main.pack(side="left", fill="both", expand=True)

        top = tk.Frame(main, bg=BG)
        top.pack(fill="x", padx=24, pady=(20, 2))
        self.lbl_title = tk.Label(top, text="Restore", bg=BG, fg=INK,
                                  font=(F, 16, "bold"))
        self.lbl_title.pack(side="left")
        self.pill = Pill(top, "checking", SUB, CARD_HI, BG)
        self.pill.pack(side="right")

        self.banner = tk.Frame(main, bg=WARN_BG, highlightbackground="#4a3a12",
                               highlightthickness=1)
        inner = tk.Frame(self.banner, bg=WARN_BG)
        inner.pack(fill="x", padx=16, pady=12)
        self.lbl_banner = tk.Label(inner, bg=WARN_BG, fg="#f5d894", font=(F, 9),
                                   justify="left", anchor="w", wraplength=740)
        self.lbl_banner.pack(side="left", fill="x", expand=True)
        self.btn_setup = Btn(inner, "Install / Repair", self.run_setup,
                             kind="primary", bg=WARN_BG)
        self.btn_setup.pack(side="right", padx=(12, 0))

        stats = tk.Frame(main, bg=BG)
        stats.pack(fill="x", padx=24, pady=(12, 2))
        self.stats = {}
        for key, title, note in (("prog", "Progress", "not started"),
                                 ("chunk", "Chunk", "1500 frames each"),
                                 ("elapsed", "Elapsed", "this session"),
                                 ("remain", "Remaining", "estimated"),
                                 ("speed", "Speed", "frames / second"),
                                 ("eta", "Finishes", "wall clock")):
            c = StatCard(stats, title, "-", note)
            c.pack(side="left", fill="both", expand=True, padx=(0, 9))
            self.stats[key] = c

        holder = tk.Frame(main, bg=BG)
        holder.pack(fill="x", padx=24, pady=(8, 2))
        self.bar = ttk.Progressbar(holder, style="P.Horizontal.TProgressbar",
                                   maximum=1000)
        self.bar.pack(fill="x")
        self.lbl_sub = tk.Label(main, text="", bg=BG, fg=SUB, font=(F, 9),
                                anchor="w")
        self.lbl_sub.pack(fill="x", padx=24, pady=(6, 8))

        self.pages = tk.Frame(main, bg=BG)
        self.pages.pack(fill="both", expand=True, padx=24, pady=(2, 18))
        self._page_restore()
        self._page_activity()
        self._page_env()
        self._page_help()
        self.show("restore")

    # ---------------------------------------------------------------- pages
    def _page_restore(self):
        pg = tk.Frame(self.pages, bg=BG)
        self.pg_restore = pg

        src = Card(pg, "Source video", "stays on this computer")
        src.pack(fill="x")
        row = tk.Frame(src.body, bg=CARD)
        row.pack(fill="x")
        self.var_video = tk.StringVar()
        tk.Entry(row, textvariable=self.var_video, bd=0, relief="flat",
                 bg="#0b0e12", fg=INK, font=(MONO, 9), insertbackground=ACC,
                 highlightthickness=1, highlightbackground=LINE,
                 highlightcolor=ACC, disabledforeground=FAINT
                 ).pack(side="left", fill="x", expand=True, ipady=7, ipadx=8)
        Btn(row, "Browse", self.browse).pack(side="left", padx=(10, 0))
        self.lbl_meta = tk.Label(src.body, text="", bg=CARD, fg=SUB,
                                 font=(MONO, 8), anchor="w", justify="left")
        self.lbl_meta.pack(fill="x", pady=(10, 0))

        cfg_card = Card(pg, "Settings")
        cfg_card.pack(fill="x", pady=(12, 0))
        b = cfg_card.body

        r1 = tk.Frame(b, bg=CARD)
        r1.pack(fill="x", pady=(0, 11))
        tk.Label(r1, text="Output scale", bg=CARD, fg=INK, font=(F, 9),
                 width=14, anchor="w").pack(side="left")
        self.var_scale = tk.StringVar(value=str(self.settings.get("scale", "2")))
        for val, lab in (("2", "2×  recommended"), ("4", "4×  advanced")):
            rb = tk.Radiobutton(r1, text=lab, value=val, variable=self.var_scale,
                                command=self.update_meta, bg=CARD, fg=INK,
                                selectcolor=CARD_HI, activebackground=CARD,
                                activeforeground=ACC, font=(F, 9), bd=0,
                                highlightthickness=0, cursor="hand2",
                                takefocus=1)
            rb.pack(side="left", padx=(0, 18))
        Tip(r1, "Both scales run the AI at 4×. 2× then downsamples, which "
                "averages away invented detail, shrinks the file and plays "
                "back on more devices. 2× is not faster.")
        self.lbl_res = tk.Label(r1, text="", bg=CARD, fg=ACC, font=(MONO, 9))
        self.lbl_res.pack(side="left")

        self.var_dn = tk.DoubleVar(value=float(self.settings.get("denoise", 0.85)))
        self.lbl_dn = self._slider(
            b, "Denoise", self.var_dn, 0.0, 1.0, lambda v: f"{v:.2f}",
            "lower keeps more natural texture",
            "How much of the SCUNet result is blended in. 1.00 is full "
            "strength and can look plastic on skin; 0.85 keeps fine texture.")

        self.var_cq = tk.DoubleVar(value=float(self.settings.get("cq", 19)))
        self.lbl_cq = self._slider(
            b, "Quality (cq)", self.var_cq, 14, 28,
            lambda v: f"{int(round(v))}", "lower is better quality, larger file",
            "NVENC constant-quality target. 16-20 is visually lossless for "
            "this kind of source.")

        r4 = tk.Frame(b, bg=CARD)
        r4.pack(fill="x")
        tk.Label(r4, text="Output folder", bg=CARD, fg=INK, font=(F, 9),
                 width=14, anchor="w").pack(side="left")
        self.lbl_outdir = tk.Label(r4, text="", bg=CARD, fg=SUB, font=(MONO, 8),
                                   anchor="w")
        self.lbl_outdir.pack(side="left", fill="x", expand=True)
        Btn(r4, "Change", self.pick_outdir).pack(side="left", padx=(8, 0))
        Btn(r4, "Open", self.open_out).pack(side="left", padx=(6, 0))

        act = tk.Frame(pg, bg=BG)
        act.pack(fill="x", pady=(14, 0))
        self.btn_check = Btn(act, "Check setup  (F5)", self.run_verify, bg=BG)
        self.btn_check.pack(side="left")
        self.btn_est = Btn(act, "Estimate time", self.run_estimate, bg=BG)
        self.btn_est.pack(side="left", padx=8)
        self.btn_test = Btn(act, "Test 30 seconds", self.run_test, bg=BG)
        self.btn_test.pack(side="left")
        self.btn_stop = Btn(act, "Stop safely", self.stop, kind="danger", bg=BG)
        self.btn_stop.pack(side="right")
        self.btn_go = Btn(act, "Start restoration", self.run_full, kind="primary")
        self.btn_go.pack(side="right", padx=10)
        self.btn_stop.configure(state="disabled")

        self.lbl_safety = tk.Label(
            pg, bg=BG, fg=FAINT, font=(F, 8), anchor="w", justify="left",
            text="Stop finishes the chunk in flight before exiting, so the resume "
                 "point stays exact. Starting again continues from the same frame; "
                 "closing the window is equally safe.")
        self.lbl_safety.pack(fill="x", pady=(10, 0))

    def _slider(self, parent, label, var, lo, hi, fmt, hint, tip):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=(0, 11))
        tk.Label(row, text=label, bg=CARD, fg=INK, font=(F, 9),
                 width=14, anchor="w").pack(side="left")
        val = tk.Label(row, text=fmt(var.get()), bg=CARD, fg=ACC,
                       font=(MONO, 10, "bold"), width=6, anchor="w")
        sc = tk.Scale(row, from_=lo, to=hi, variable=var, orient="horizontal",
                      showvalue=False, resolution=0.01 if hi <= 1 else 1,
                      length=230, bg=CARD, fg=INK, troughcolor="#0b0e12",
                      highlightthickness=0, bd=0, sliderrelief="flat",
                      activebackground=ACC, sliderlength=18, width=6,
                      takefocus=1,
                      command=lambda _v: val.configure(text=fmt(var.get())))
        sc.pack(side="left", padx=(0, 12))
        val.pack(side="left")
        tk.Label(row, text=hint, bg=CARD, fg=FAINT,
                 font=(F, 8)).pack(side="left", padx=(10, 0))
        Tip(sc, tip)
        return val

    def _page_activity(self):
        pg = tk.Frame(self.pages, bg=BG)
        self.pg_activity = pg
        card = Card(pg, "Activity log", "everything the pipeline reports")
        card.pack(fill="both", expand=True)
        wrap = tk.Frame(card.body, bg=CARD)
        wrap.pack(fill="both", expand=True)
        self.log = tk.Text(wrap, bg="#07090c", fg="#c3ccd8", bd=0,
                           font=(MONO, 9), wrap="word", relief="flat",
                           highlightthickness=1, highlightbackground=LINE,
                           insertbackground=ACC, padx=12, pady=10)
        self.log.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(wrap, command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set, state="disabled")
        for tag, col in (("err", BAD), ("ok", GOOD), ("warn", WARN), ("head", ACC)):
            self.log.tag_configure(tag, foreground=col)
        btns = tk.Frame(pg, bg=BG)
        btns.pack(fill="x", pady=(10, 0))
        Btn(btns, "Clear", self.clear_log, bg=BG).pack(side="left")
        Btn(btns, "Open output folder", self.open_out, bg=BG).pack(side="left", padx=8)

    def _page_env(self):
        pg = tk.Frame(self.pages, bg=BG)
        self.pg_environment = pg

        ready = Card(pg, "Readiness")
        ready.pack(fill="x")
        self.env_rows = {}
        for key, label in (("gpu", "GPU"), ("torch", "PyTorch / CUDA"),
                           ("models", "Model weights"), ("setup", "Setup marker"),
                           ("ffmpeg", "FFmpeg")):
            r = tk.Frame(ready.body, bg=CARD)
            r.pack(fill="x", pady=2)
            tk.Label(r, text=label, bg=CARD, fg=SUB, font=(F, 9),
                     width=18, anchor="w").pack(side="left")
            dot = tk.Label(r, text="●", bg=CARD, fg=FAINT, font=(F, 9))
            dot.pack(side="left", padx=(0, 8))
            txt = tk.Label(r, text="checking…", bg=CARD, fg=INK, font=(MONO, 8),
                           anchor="w", justify="left")
            txt.pack(side="left", fill="x", expand=True)
            self.env_rows[key] = (dot, txt)

        paths = Card(pg, "Paths")
        paths.pack(fill="x", pady=(12, 0))
        self.lbl_env = tk.Label(paths.body, bg=CARD, fg=SUB, font=(MONO, 8),
                                justify="left", anchor="w")
        self.lbl_env.pack(fill="x")
        row = tk.Frame(paths.body, bg=CARD)
        row.pack(fill="x", pady=(12, 0))
        Btn(row, "Check setup", self.run_verify).pack(side="left")
        Btn(row, "Install / Repair", self.run_setup).pack(side="left", padx=8)
        Btn(row, "Re-check", self.refresh_state).pack(side="left")
        Btn(row, "Change scratch folder", self.pick_workdir).pack(side="left", padx=8)

    def _page_help(self):
        pg = tk.Frame(self.pages, bg=BG)
        self.pg_help = pg
        card = Card(pg, "How to use this")
        card.pack(fill="both", expand=True)
        tk.Label(card.body, bg=CARD, fg=SUB, font=(F, 9), justify="left",
                 anchor="w", wraplength=780, text=(
                     "1.  Install the environment if the banner asks you to.\n"
                     "2.  Check setup — you want ALL CHECKS PASSED.\n"
                     "3.  Estimate time — measures 120 frames on this machine and\n"
                     "      projects the length of the whole job.\n"
                     "4.  Test 30 seconds, then watch the result.\n"
                     "5.  Start restoration.\n\n"
                     "Everything runs on this computer. No video is uploaded, no\n"
                     "account is needed, and nothing is sent anywhere.\n\n"
                     "Long jobs are split into 1,500-frame chunks. Each finished\n"
                     "chunk is a playable MP4 in the scratch folder, so you can\n"
                     "check quality while the run continues. At the end they are\n"
                     "joined by stream copy — no re-encode — and the original\n"
                     "audio is muxed back in.\n\n"
                     "2× is preselected on purpose. The AI renders at 4× either\n"
                     "way; 2× then downsamples, which averages away invented\n"
                     "detail. It is a quality choice, not a speed one."
                 )).pack(fill="x")

    def show(self, key):
        self.page = key
        for k, item in self.nav.items():
            item.select(k == key)
        for k in ("restore", "activity", "environment", "help"):
            getattr(self, f"pg_{k}").pack_forget()
        getattr(self, f"pg_{key}").pack(fill="both", expand=True)
        self.lbl_title.configure(text={"restore": "Restore",
                                       "activity": "Activity log",
                                       "environment": "Environment",
                                       "help": "Help"}[key])

    # ---------------------------------------------------------------- utils
    def say(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def open_out(self):
        target = cfg.output_dir(self.settings, self._video_path())
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        try:
            os.startfile(str(target))                      # noqa: S606
        except (AttributeError, OSError):
            webbrowser.open(target.as_uri())

    def set_pill(self, text, fg=SUB, bg=CARD_HI):
        self.pill.set(text, fg, bg)

    def busy(self, on):
        self.running = on
        for b in (self.btn_go, self.btn_check, self.btn_est, self.btn_test,
                  self.btn_setup):
            b.configure(state="disabled" if on else "normal")
        self.btn_stop.configure(state="normal" if on else "disabled")
        if not on:
            self.refresh_state()

    def _video_path(self):
        v = (self.var_video.get() or "").strip()
        return Path(v) if v else None

    # ---------------------------------------------------------------- state
    def probe_env(self):
        """Ask the venv's PyTorch what hardware it can actually use. Runs off
        the UI thread; harmless if the venv does not exist yet."""
        def worker():
            env = None
            if VENV_PY.exists():
                try:
                    r = subprocess.run([str(VENV_PY), "-c", ENV_PROBE],
                                       capture_output=True, text=True, timeout=120,
                                       creationflags=NO_WINDOW)
                    env = parse_env(r.stdout)
                except (OSError, subprocess.SubprocessError):
                    env = None
            self.q.put(("env", env))
        threading.Thread(target=worker, daemon=True).start()

    def _set_row(self, key, level, text):
        dot, lab = self.env_rows[key]
        dot.configure(fg={"ok": GOOD, "warn": WARN, "bad": BAD}.get(level, FAINT))
        lab.configure(text=text)

    def refresh_state(self):
        ready = cfg.is_setup_complete()
        work = cfg.work_dir(self.settings)
        free = cfg.free_gb(work)
        self.lbl_disk.configure(
            text=f"SCRATCH\n{work}\n{free:.0f} GB free" if free else f"SCRATCH\n{work}")

        if hasattr(self, "lbl_env"):
            self.lbl_env.configure(text="\n".join([
                f"project   {ROOT}",
                f"scratch   {work}",
                f"output    {cfg.output_dir(self.settings, self._video_path())}",
                f"venv      {'present' if VENV_PY.exists() else 'missing'}",
            ]))
        if hasattr(self, "lbl_outdir"):
            self.lbl_outdir.configure(
                text=str(cfg.output_dir(self.settings, self._video_path())))

        if hasattr(self, "env_rows"):
            text, level = env_summary(self.env)
            self._set_row("gpu", level if VENV_PY.exists() else "warn",
                          text if VENV_PY.exists() else "install the environment first")
            if self.env:
                self._set_row("torch", "ok",
                              f"torch {self.env.get('torch')} · CUDA {self.env.get('cuda')}")
            else:
                self._set_row("torch", "warn", "not detected yet")
            self._set_row("models", "ok" if cfg.models_present() else "bad",
                          "SCUNet + Real-ESRGAN present" if cfg.models_present()
                          else "missing — run Install / Repair")
            self._set_row("setup", "ok" if ready else "warn",
                          ".setup_ok written by a verified install" if ready
                          else "not verified yet")
            self._set_row("ffmpeg", "ok" if _has_ffmpeg() else "bad",
                          "on PATH" if _has_ffmpeg()
                          else "not found — winget install Gyan.FFmpeg")

        if ready:
            self.banner.pack_forget()
            self.set_pill("ready", GOOD, GOOD_BG)
            for b in (self.btn_go, self.btn_est, self.btn_test):
                b.configure(state="normal")
        else:
            self.banner.pack(fill="x", padx=24, pady=(8, 0),
                             after=self.lbl_title.master)
            if VENV_PY.exists():
                self.lbl_banner.configure(
                    text="Setup was started but never finished — PyTorch is most "
                         "likely still missing. This resumes rather than starting over.")
                self.set_pill("setup incomplete", WARN, WARN_BG)
            else:
                self.lbl_banner.configure(
                    text="The environment is not installed yet. About 2.5 GB of "
                         "PyTorch, roughly 10 minutes, all local.")
                self.set_pill("not installed", WARN, WARN_BG)
            for b in (self.btn_go, self.btn_est, self.btn_test):
                b.configure(state="disabled")

    def browse(self):
        f = filedialog.askopenfilename(
            title="Choose a video",
            filetypes=[("Video", " ".join(f"*{e}" for e in cfg.VIDEO_TYPES)),
                       ("All files", "*.*")])
        if f:
            self.set_video(Path(f))

    def pick_outdir(self):
        d = filedialog.askdirectory(title="Where should finished videos go?")
        if d:
            self.settings["output_dir"] = d
            cfg.save_settings(self.settings)
            self.refresh_state()

    def pick_workdir(self):
        d = filedialog.askdirectory(title="Scratch folder for chunk files")
        if d:
            self.settings["work_dir"] = d
            cfg.save_settings(self.settings)
            self.refresh_state()

    def set_video(self, path):
        if path is None:
            self.var_video.set("")
            self.info = None
            self.lbl_meta.configure(
                text="No video selected. Choose a file to see its details and a "
                     "runtime estimate.")
            return
        self.var_video.set(str(path))
        self.info = probe_video(path)
        self.settings["video"] = str(path)
        cfg.save_settings(self.settings)
        self.update_meta()
        self.refresh_state()

    def update_meta(self):
        if not self.info:
            if self.var_video.get():
                self.lbl_meta.configure(
                    text="Could not read this file. Is FFmpeg installed and on PATH?")
            return
        i = self.info
        m, s = divmod(int(i["dur"]), 60)
        k = int(self.var_scale.get())
        ow, oh = i["w"] * k, i["h"] * k
        mins = i["dur"] / 60
        est = cfg.estimate_seconds(i["frames"])
        self.lbl_meta.configure(text=(
            f"{i['w']}×{i['h']}  ·  {i['fps']:.2f} fps  ·  {m}m {s:02d}s  ·  "
            f"{i['frames']:,} frames  ·  {i['codec']}  ·  {i['pix_fmt']}"
            f"{' (full range)' if i['full_range'] else ''}  ·  "
            f"audio {'yes' if i['audio'] else 'none'}\n"
            f"output {ow}×{oh}  ·  {cfg.vram_guidance(ow, oh)}  ·  "
            f"~{cfg.estimate_disk_gb(mins, ow, oh):.0f} GB scratch  ·  "
            f"rough first guess {fmt_short(est)} — press Estimate time to measure"))
        self.lbl_res.configure(text=f"→ {ow}×{oh}")
        self.settings["scale"] = self.var_scale.get()
        cfg.save_settings(self.settings)

    # ---------------------------------------------------------------- runner
    def launch(self, cmd, mode):
        if self.running:
            # Swallowing the click silently is how "nothing happens when I press
            # the button" happens. Say so, and self-heal a stale flag.
            if self.proc is None or self.proc.poll() is not None:
                self.say("Previous job had already finished — clearing the busy "
                         "flag and continuing.", "warn")
                self.busy(False)
            else:
                self.say("A job is already running. Press Stop safely first.", "warn")
                self.show("activity")
                return
        self.mode = mode
        self.t_start = time.time()
        self.last = {}
        self.bar.configure(value=0)
        for c in self.stats.values():
            c.set("-")
        self.lbl_sub.configure(text="")
        self.busy(True)
        self.set_pill({"setup": "installing", "verify": "checking",
                       "estimate": "measuring", "test": "test run",
                       "full": "restoring"}.get(mode, "working"), ACC, ACC_DIM)
        self.show("activity" if mode in ("setup", "verify") else self.page)
        self.say("\n$ " + " ".join(str(c) for c in cmd), "head")

        def worker():
            try:
                self.proc = subprocess.Popen(
                    [str(c) for c in cmd], cwd=str(ROOT),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace",
                    creationflags=NO_WINDOW)
                for line in self.proc.stdout:
                    self.q.put(("line", line))
                self.proc.wait()
                self.q.put(("done", self.proc.returncode))
            except Exception as exc:                       # noqa: BLE001
                self.q.put(("line", f"Failed to start: {exc}\n"))
                self.q.put(("done", 1))

        threading.Thread(target=worker, daemon=True).start()

    def _drain(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "line":
                    self._on_line(payload)
                elif kind == "env":
                    self.env = payload
                    self.refresh_state()
                else:
                    self._on_exit(payload)
        except queue.Empty:
            pass
        if self.running:
            self._tick()
        self.root.after(120, self._drain)

    def _on_line(self, line):
        rec = parse_progress(line)
        if rec is None:
            txt = line.rstrip()
            if txt:
                self.say(txt, classify(txt))
            return
        self.last = rec
        self._render(rec)

    def _render(self, rec):
        stage = rec.get("stage", "")
        labels = {"models": "loading the AI models…",
                  "autotune": "measuring how much fits in VRAM…",
                  "encoder": "validating the GPU encoder with a dummy encode…",
                  "joining": "joining chunks by stream copy…",
                  "stopped": "stopped — start again to resume"}
        if stage in labels:
            self.lbl_sub.configure(text=labels[stage])
        if stage == "done":
            self.bar.configure(value=1000)
            self.stats["prog"].set("100%", "complete")
            self.stats["remain"].set("-", "finished")
            self.set_pill("finished", GOOD, GOOD_BG)
            self.lbl_sub.configure(
                text=f"Saved to {rec.get('output', '')}  ·  {rec.get('size_gb', '?')} GB")
            return
        if stage != "restoring":
            return

        frames, total = rec.get("frames", 0), rec.get("total", 0) or 1
        frac = min(frames / total, 1.0)
        eta = rec.get("eta")
        cur, tot = chunk_position(frames, rec.get("total", 0))
        self.bar.configure(value=frac * 1000)
        self.stats["prog"].set(f"{frac * 100:.1f}%", f"{frames:,} of {total:,}")
        self.stats["chunk"].set(f"{cur}/{tot}" if tot else "-", "1500 frames each")
        self.stats["elapsed"].set(fmt_hms(rec.get("elapsed")), "this session")
        self.stats["remain"].set(fmt_short(eta), "estimated")
        self.stats["speed"].set(f"{rec.get('fps', 0):.2f}", "frames / second")
        self.stats["eta"].set(fmt_finish(eta).replace("done by ", "") or "-",
                              "wall clock")
        extra = (f"  ·  {rec['dupes']:,} duplicate frames reused"
                 if rec.get("dupes") else "")
        self.lbl_sub.configure(text=f"{frames:,} of {total:,} frames{extra}")

    def _tick(self):
        if self.last.get("stage") == "restoring":
            return
        self.stats["elapsed"].set(fmt_hms(time.time() - self.t_start), "this session")
        if self.mode == "setup":
            self.lbl_sub.configure(
                text="Installing… the PyTorch download is about 2.5 GB and shows "
                     "no progress bar. It is working — leave it be.")

    def _on_exit(self, code):
        self.proc = None
        self.busy(False)

        if self.mode == "setup":
            self.refresh_state()
            self.probe_env()
            if STAMP.exists():
                self.say("Setup complete.", "ok")
                self.set_pill("ready", GOOD, GOOD_BG)
                messagebox.showinfo("Setup complete", parent=self.root,
                                    message="The environment is installed and verified.")
            else:
                self.set_pill("setup failed", BAD, BAD_BG)
                tail = "\n".join(self.log.get("1.0", "end").strip().splitlines()[-6:])
                messagebox.showerror(
                    "Setup incomplete", parent=self.root,
                    message="Setup did not finish.\n\nLast lines of the log:\n\n" + tail)
            return

        if self.mode == "verify":
            self.probe_env()

        if self.mode == "estimate" and code != 0:
            self.say("Estimate failed — see the error above.", "err")
            self.set_pill("estimate failed", BAD, BAD_BG)
            self.show("activity")
            messagebox.showerror(
                "Estimate failed", parent=self.root,
                message="The 120-frame measurement did not finish.\n\n"
                        "The Activity log shows the error.")
            return

        if self.mode == "estimate" and code == 0:
            rec = self.last
            secs = project_total(rec.get("frames", 0),
                                 self.info["frames"] if self.info else 0,
                                 rec.get("elapsed", 0))
            if secs:
                self.stats["remain"].set(fmt_short(secs), "for the whole video")
                self.stats["eta"].set(fmt_finish(secs).replace("done by ", ""),
                                      "if started now")
                self.lbl_sub.configure(
                    text=f"Estimated {fmt_hms(secs)} for {self.info['frames']:,} "
                         f"frames at {rec.get('fps', 0):.2f} fps")
                self.say(f"Estimated total: {fmt_hms(secs)}", "ok")
                messagebox.showinfo(
                    "Time estimate", parent=self.root,
                    message=f"About {fmt_short(secs)} for the whole video.\n\n"
                            f"Measured {rec.get('fps', 0):.2f} frames/sec over "
                            f"{rec.get('frames', 0)} frames on this machine.\n\n"
                            f"{fmt_finish(secs)}.")
            self.set_pill("ready", GOOD, GOOD_BG)
            return

        if code == 0:
            self.say("Finished.", "ok")
            self.set_pill("finished" if self.mode == "full" else "ready",
                          GOOD, GOOD_BG)
        elif self.last.get("stage") == "stopped":
            self.set_pill("stopped", WARN, WARN_BG)
            self.say("Stopped cleanly. Start again to resume from this frame.", "warn")
        else:
            self.say(f"Exited with code {code}.", "err")
            self.set_pill("failed", BAD, BAD_BG)
            self.show("activity")
            messagebox.showerror(
                "Stopped early", parent=self.root,
                message="The job stopped with an error — the Activity log shows "
                        "why.\n\nNothing is lost; starting again resumes.")

    # ---------------------------------------------------------------- actions
    def _cmd(self, extra):
        return [VENV_PY, "restore_video.py", self.var_video.get(),
                "--final-scale", self.var_scale.get(),
                "--denoise-strength", f"{self.var_dn.get():.2f}",
                "--cq", str(int(round(self.var_cq.get()))),
                "--json-progress"] + extra

    def _persist(self):
        self.settings.update({
            "scale": self.var_scale.get(),
            "denoise": round(float(self.var_dn.get()), 2),
            "cq": int(round(self.var_cq.get())),
        })
        cfg.save_settings(self.settings)

    def run_setup(self):
        self.launch(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", str(ROOT / "setup.ps1")], "setup")

    def run_verify(self):
        if not VENV_PY.exists():
            messagebox.showwarning("Not installed", parent=self.root,
                                   message="Install the environment first.")
            return
        self.say("Checking the environment…", "head")
        self.launch([VENV_PY, "verify_setup.py"], "verify")

    def run_estimate(self):
        if not self._ready():
            return
        self._persist()
        self.say("Measuring speed over 120 frames on this machine…", "head")
        work = cfg.work_dir(self.settings)
        self.launch(self._cmd([
            "--limit", "120",
            "-o", str(cfg.output_dir(self.settings, self._video_path()) / "_speedtest.mp4"),
            "--work", str(work) + "_est"]), "estimate")

    def run_test(self):
        if not self._ready():
            return
        self._persist()
        k = self.var_scale.get()
        out = cfg.output_dir(self.settings, self._video_path()) / f"test_{k}x.mp4"
        self.say(f"Rendering a 30-second test clip to {out}…", "head")
        self.launch(self._cmd([
            "--limit", "450", "-o", str(out),
            "--work", str(cfg.work_dir(self.settings)) + "_test"]), "test")

    def run_full(self):
        if not self._ready():
            return
        n = self.info["frames"] if self.info else 0
        work = cfg.work_dir(self.settings)
        if not messagebox.askyesno(
                "Start full restoration", parent=self.root,
                message=(f"Restore all {n:,} frames at {self.var_scale.get()}×?\n\n"
                         "This runs for many hours entirely on this computer.\n"
                         "Press Stop safely at any time, or close the window — it "
                         "resumes from where it stopped.\n\n"
                         f"Scratch folder: {work}\n"
                         f"Free space: {cfg.free_gb(work):.0f} GB\n\n"
                         "Run 'Estimate time' first if you want the duration.")):
            return
        self._persist()
        self.launch(self._cmd(["--work", str(work)]), "full")

    def _ready(self):
        if not cfg.is_setup_complete():
            messagebox.showwarning("Not installed", parent=self.root,
                                   message="Install the environment first.")
            return False
        v = (self.var_video.get() or "").strip()
        if not v or not Path(v).exists():
            messagebox.showwarning("No video", parent=self.root,
                                   message="Choose a video file first.")
            return False
        if self.info is None:
            messagebox.showwarning(
                "Unreadable video", parent=self.root,
                message="FFmpeg could not read that file. Check that FFmpeg is "
                        "installed and the file is a supported video.")
            return False
        return True

    def stop(self):
        if not self.proc:
            return
        base = str(cfg.work_dir(self.settings))
        for d in (Path(base), Path(base + "_test"), Path(base + "_est")):
            try:
                d.mkdir(parents=True, exist_ok=True)
                (d / "STOP").write_text("stop", encoding="utf-8")
            except OSError:
                pass
        self.say("Stopping cleanly after the current chunk…", "warn")
        self.set_pill("stopping", WARN, WARN_BG)
        self.btn_stop.configure(state="disabled")
        self.root.after(30000, self._force_stop)

    def _force_stop(self):
        if self.proc and self.proc.poll() is None:
            self.say("Still running — terminating.", "warn")
            self.proc.terminate()

    def on_close(self):
        if self.running and not messagebox.askokcancel(
                "Quit", parent=self.root,
                message="A job is running. Quit anyway?\n\n"
                        "Progress up to the last finished chunk is kept, and "
                        "starting again resumes from there."):
            return
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.root.destroy()


def _has_ffmpeg() -> bool:
    from shutil import which
    return which("ffmpeg") is not None


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
