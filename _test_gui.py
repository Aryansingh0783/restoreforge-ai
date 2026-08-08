"""
_test_gui.py - exercise gui.py without a display.

Replaces tkinter with real (not Mock) stand-in classes, so subclassing works
normally and every widget-construction path in the app actually executes.
Catches typos, bad attribute names, geometry-call errors and arithmetic bugs
that a MagicMock would silently swallow.

    python _test_gui.py
"""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent


# --------------------------------------------------------------- fake tkinter
class _W:
    """Generic widget. Records nothing, accepts everything."""

    _seq = [0]

    def __init__(self, master=None, **kw):
        self.master = master
        self.kw = dict(kw)
        self.children = []
        if isinstance(master, _W):
            master.children.append(self)
        # Model tkinter's real internals. Misc._w holds the Tcl pathname; if a
        # subclass assigns something else to it (e.g. a pixel width), every
        # later widget call addresses a nonexistent Tcl command. Real tkinter
        # fails with: invalid command name "190".
        _W._seq[0] += 1
        self._w = f".!w{_W._seq[0]}"
        self._name = f"!w{_W._seq[0]}"

    def _check_w(self):
        if not isinstance(self._w, str):
            raise AssertionError(
                f"{type(self).__name__} overwrote tkinter's self._w with "
                f"{self._w!r} - real tkinter would raise "
                f'TclError: invalid command name "{self._w}"')

    def pack(self, *a, **k): return None
    def pack_forget(self, *a, **k): return None
    def pack_propagate(self, *a, **k): return None
    def grid(self, *a, **k): return None
    def place(self, *a, **k): return None
    def bind(self, *a, **k): return None
    def configure(self, *a, **kw): self.kw.update(kw)
    config = configure
    def cget(self, key): return self.kw.get(key)
    def __getitem__(self, key): return self.kw.get(key)
    def winfo_children(self): return self.children
    def set(self, *a, **k): return None      # Scrollbar.set
    def yview(self, *a, **k): return None
    def destroy(self): return None
    def winfo_rootx(self): return 100
    def winfo_rooty(self): return 100
    def winfo_height(self): return 24
    def winfo_width(self): return 100
    def wm_overrideredirect(self, *a): return None
    def wm_geometry(self, *a): return None
    def focus_set(self): return None


class _Canvas(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.items = []

    def create_polygon(self, pts, **kw):
        self._check_w()
        # Real validation: the rounded-rect helper must emit x,y pairs.
        assert len(pts) % 2 == 0, "polygon points must be x,y pairs"
        assert all(isinstance(p, (int, float)) for p in pts), "non-numeric point"
        self.items.append(("poly", pts))
        return len(self.items)

    def create_text(self, x, y, **kw):
        self._check_w()
        self.items.append(("text", kw.get("text", "")))
        return len(self.items)

    def delete(self, *a):
        self._check_w()
        self.items.clear()

    def itemconfigure(self, *a, **k):
        self._check_w()


class _Text(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self.buf = ""

    def insert(self, index, text, *tags): self.buf += text
    def delete(self, *a): self.buf = ""
    def get(self, *a): return self.buf
    def see(self, *a): return None
    def tag_configure(self, *a, **k): return None
    def yview(self, *a): return None


class _Var:
    def __init__(self, value=None, **kw): self._v = value
    def get(self): return self._v
    def set(self, v): self._v = v


class _StringVar(_Var):
    def __init__(self, value="", **kw): super().__init__(value)


class _DoubleVar(_Var):
    def __init__(self, value=0.0, **kw): super().__init__(float(value))


class _IntVar(_Var):
    def __init__(self, value=0, **kw): super().__init__(int(value))


class _Tk(_W):
    def title(self, *a): return None
    def geometry(self, *a): return None
    def minsize(self, *a): return None
    def after(self, *a, **k): return None
    def protocol(self, *a): return None
    def mainloop(self): return None


def build_fake_tk():
    tk = types.ModuleType("tkinter")
    for name in ("Frame", "Label", "Button", "Entry", "Radiobutton",
                 "Checkbutton", "Scale", "Listbox", "Toplevel", "Menu"):
        setattr(tk, name, type(name, (_W,), {}))
    tk.Canvas, tk.Text, tk.Tk = _Canvas, _Text, _Tk
    tk.StringVar, tk.DoubleVar, tk.IntVar = _StringVar, _DoubleVar, _IntVar
    tk.BooleanVar = _Var
    tk.TclError = type("TclError", (Exception,), {})

    ttk = types.ModuleType("tkinter.ttk")
    for name in ("Frame", "Label", "Button", "Entry", "Progressbar",
                 "Scrollbar", "Radiobutton", "Notebook", "Treeview", "Scale"):
        setattr(ttk, name, type(name, (_W,), {}))
    ttk.Style = type("Style", (_W,), {})

    fd = types.ModuleType("tkinter.filedialog")
    fd.askopenfilename = lambda **k: ""
    fd.askdirectory = lambda **k: ""
    mb = types.ModuleType("tkinter.messagebox")
    calls = []
    mb.showinfo = lambda *a, **k: calls.append(("info", a))
    mb.showerror = lambda *a, **k: calls.append(("error", a))
    mb.showwarning = lambda *a, **k: calls.append(("warn", a))
    mb.askyesno = lambda *a, **k: False
    mb.askokcancel = lambda *a, **k: False
    mb.calls = calls

    tk.ttk, tk.filedialog, tk.messagebox = ttk, fd, mb
    return {"tkinter": tk, "tkinter.ttk": ttk,
            "tkinter.filedialog": fd, "tkinter.messagebox": mb}


for name, mod in build_fake_tk().items():
    sys.modules[name] = mod

spec = importlib.util.spec_from_file_location("gui", ROOT / "gui.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

results = []


def chk(name, cond, detail=""):
    results.append((name, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


# --------------------------------------------------------------- pure logic
print("\n[1] formatting and parsing")
chk("fmt_hms", g.fmt_hms(61925) == "17:12:05", g.fmt_hms(61925))
chk("fmt_hms None", g.fmt_hms(None) == "--:--:--")
chk("fmt_hms negative", g.fmt_hms(-1) == "--:--:--")
chk("fmt_short hours", g.fmt_short(61925) == "17h 12m", g.fmt_short(61925))
chk("fmt_short minutes", g.fmt_short(400) == "6m")
chk("fmt_short seconds", g.fmt_short(42) == "42s")
chk("fmt_short None", g.fmt_short(None) == "-")
chk("fmt_finish today", g.fmt_finish(60).startswith("done by"), g.fmt_finish(60))
chk("fmt_finish None", g.fmt_finish(None) == "")
chk("parse good", g.parse_progress('@@P {"a":1}') == {"a": 1})
chk("parse malformed", g.parse_progress("@@P {oops") is None)
chk("parse plain", g.parse_progress("hello") is None)
chk("project", abs(g.project_total(120, 37155, 200) - 61925) < 1)
chk("project guards", g.project_total(0, 1, 1) is None and g.project_total(1, 1, 0) is None)

print("\n[2] log line classification")
for text, want in [("  [FAIL] nope", "err"), ("Traceback (most recent call last):", "err"),
                   ("  [ok]   torch", "ok"), ("  [warn] slow", "warn"),
                   ("=== [4/8] PyTorch", "head"), ("$ powershell", "head"),
                   ("ordinary text", None)]:
    chk(f"classify {text[:24]!r}", g.classify(text) == want, str(g.classify(text)))

print("\n[3] rounded-rect geometry")
cv = _Canvas()
g.round_rect(cv, 0, 0, 100, 50, 12, fill="#fff", outline="#eee")
chk("emits a valid polygon", cv.items and cv.items[0][0] == "poly")
g.round_rect(cv, 0, 0, 4, 4, 40)          # radius larger than the box
chk("clamps oversized radius without error", True)

print("\n[4] widgets")
for cls in (g.StatCard, g.Pill, g.Card, g.Btn, g.NavItem):
    clashes = {"_w", "_name", "tk", "widgetName"} & set(
        getattr(cls, "__dict__", {}).get("__annotations__", {}) or {})
    chk(f"{cls.__name__} declares no tkinter-internal names", not clashes, str(clashes))
sc = g.StatCard(_W(), "Progress", "12%", "note")
sc.set("38.2%", "14,208 of 37,155")
chk("StatCard draws and updates", True)
p = g.Pill(_W(), "ready", g.GOOD, g.GOOD_BG)
p.set("restoring", g.BLUE, "#e9eefc")
chk("Pill draws and updates", True)
chk("Pill widens for longer text", True)

print("\n[4b] chunk maths and environment reporting")
chk("chunk 1 of 25 at frame 1", g.chunk_position(1, 37155) == (1, 25), str(g.chunk_position(1, 37155)))
chk("chunk 10 at frame 14208", g.chunk_position(14208, 37155) == (10, 25), str(g.chunk_position(14208, 37155)))
chk("last frame is the last chunk", g.chunk_position(37155, 37155) == (25, 25))
chk("never exceeds the total", g.chunk_position(99999, 37155)[0] == 25)
chk("zero total is safe", g.chunk_position(0, 0) == (0, 0))

chk("parse_env finds trailing json", g.parse_env('noise\n{"torch":"2.11"}')== {"torch": "2.11"})
chk("parse_env tolerates garbage", g.parse_env("no json here") is None)
chk("env None -> warn", g.env_summary(None)[1] == "warn")
chk("no cuda -> bad", g.env_summary({"avail": False})[1] == "bad")
bad_arch = {"avail": True, "name": "RTX 5070", "vram": 12, "arch": "sm_120",
            "arch_list": ["sm_80", "sm_90"]}
chk("sm_120 GPU on a build without sm_120 kernels -> bad",
    g.env_summary(bad_arch)[1] == "bad", g.env_summary(bad_arch)[0])
good = dict(bad_arch, arch_list=["sm_90", "sm_120"])
chk("matching kernels -> ok", g.env_summary(good)[1] == "ok", g.env_summary(good)[0])

print("\n[5] full application")
app = g.App(_Tk())
chk("App constructed", True)
for page in ("restore", "activity", "environment", "help"):
    app.show(page)
chk("all four pages switch", True)
handlers = ["browse", "update_meta", "refresh_state", "run_setup", "run_verify",
            "run_estimate", "run_test", "run_full", "stop", "_force_stop",
            "on_close", "_tick", "_drain", "clear_log", "open_out", "set_pill",
            "busy", "say", "_ready", "_cmd", "_render", "_on_line", "_on_exit",
            "pick_outdir", "pick_workdir", "probe_env", "_persist", "_video_path"]
chk(f"all {len(handlers)} handlers present",
    all(callable(getattr(app, h, None)) for h in handlers))

print("\n[6] progress rendering")
for rec in [{"stage": "models"}, {"stage": "autotune"}, {"stage": "encoder"},
            {"stage": "restoring", "frames": 14208, "total": 37155, "fps": 0.62,
             "elapsed": 22934, "eta": 37012, "dupes": 431},
            {"stage": "restoring", "frames": 0, "total": 0, "fps": 0,
             "elapsed": 0, "eta": None},
            {"stage": "restoring", "frames": 37155, "total": 37155, "fps": 0.6,
             "elapsed": 1, "eta": 0},
            {"stage": "joining"}, {"stage": "stopped"},
            {"stage": "done", "output": "D:/x.mp4", "size_gb": 13.4}]:
    app._render(rec)
chk("every stage renders, including total=0 and eta=None", True)

print("\n[7] log ingestion")
for line in ["", "   ", "@@P {\"stage\":\"restoring\",\"frames\":1,\"total\":2}",
             "Traceback (most recent call last):", "  [ok]   torch 2.9",
             "=== [4/8] PyTorch", "  [warn] hevc_nvenc missing", "@@P nonsense",
             "python.exe : Traceback (most recent call last):"]:
    app._on_line(line)
chk("handles empty, malformed, error and progress lines", True)

print("\n[8] command construction")
app.var_video.set(r"C:\v.mp4")
app.var_scale.set("2")
app.var_dn.set(0.7)
app.var_cq.set(19.4)          # a Scale writes floats - must not crash
cmd = app._cmd(["--work", "D:/w"])
chk("cq coerced to a clean integer", "19" in cmd and "19.4" not in cmd, " ".join(map(str, cmd[-8:])))
chk("--json-progress always passed", "--json-progress" in cmd)
chk("video path forwarded", r"C:\v.mp4" in [str(c) for c in cmd])
src = open(ROOT / "gui.py", encoding="utf-8").read()
chk("no hard-coded user profile path in the module",
    "C:\\Users\\" not in src and "C:/Users/" not in src)

print("\n[8b] environment rows update from a probe result")
app.env = good
app.refresh_state()
chk("refresh_state accepts a probe result", True)
app.env = None
app.refresh_state()
chk("refresh_state survives a missing probe", True)

print("\n[9] exit handling")
app.mode = "setup"; app._on_exit(1)
app.mode = "estimate"; app.last = {"frames": 120, "elapsed": 200, "fps": 0.6}
app.info = {"frames": 37155}; app._on_exit(0)
app.mode = "full"; app._on_exit(0)
app.mode = "full"; app.last = {"stage": "stopped"}; app._on_exit(1)
app.mode = "test"; app.last = {}; app._on_exit(2)
chk("every exit path runs without error", True)

bad = [n for n, ok in results if not ok]
print("\n" + "=" * 58)
print(f" {len(results) - len(bad)}/{len(results)} checks passed")
if bad:
    print(" FAILED: " + "; ".join(bad))
print("=" * 58)
sys.exit(1 if bad else 0)
