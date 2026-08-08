# Quality guide

## 2× or 4×

**Use 2× unless you have a specific reason not to.**

Both settings run Real-ESRGAN at 4×. Choosing 2× adds a downscale afterwards, so
the GPU work is identical and **2× is not faster** — it is a quality choice.

A 720p capture contains nowhere near 5120 × 2880 of real detail. At 4×, most of
those pixels are invented by the model, and invented detail is where artifacts
live. Rendering at 4× then supersampling to 1440p averages that invention away,
usually producing a picture that is both sharper and cleaner than native 4×, at
a quarter of the file size and with far better playback compatibility.

Render 30 seconds at each and compare full-screen. That settles it for your
footage better than any general advice.

## Denoise strength

Controls how much of the SCUNet result is blended in. Default `0.85`.

| Value | Effect |
| --- | --- |
| `0.70` | Use if faces look waxy or the picture has lost its material quality. |
| `0.85` | Default. Removes most noise while keeping fine texture. |
| `1.00` | For severe noise where texture loss is an acceptable trade. |

Full-strength denoising is the most common cause of the flat, artificial look
people associate with AI restoration. Lower this before changing anything else.

## Temporal stability

SCUNet and Real-ESRGAN are single-image models — they see one frame at a time.
Run per-frame on noisy video, each frame is denoised slightly differently and
flat areas shimmer. A temporal pre-denoise pass settles the noise field first so
the model makes consistent decisions frame to frame. Enabled by default; it is
the highest-value setting in the pipeline.

## Encoder quality (cq)

Lower is better quality and a larger file.

| Range | Use |
| --- | --- |
| 14–16 | Archival. Large files, no visible loss. |
| 17–20 | Default range. 19 is visually lossless for this material. |
| 21–24 | Noticeably smaller, slight softening of fine detail. |
| 25+ | Visible compression artifacts. Not recommended. |

## Colour handling

Sources are examined for signal range and the output matches. Many webcams
record full range (`yuvj420p`); forcing limited range on such a source darkens
the entire video. The `auto` default preserves what the source used.

## What to expect

**Realistic:** noise largely gone, cleaner edges, an easier picture to watch. It
will look like a better recording — not like different equipment.

**Limitations:** detail never recorded cannot be recovered. Faces and text are
where invention is most visible. Compression blocking, banding and severe motion
blur may persist or be emphasised. Interlacing and rolling shutter are not
addressed.

**No guarantee** that a given damaged source can be made pristine. If a test clip
does not look meaningfully better, a full run will not either.

## A sensible workflow

1. Estimate time, so you know what you are committing to.
2. Render 30 seconds at 2× with the defaults.
3. Looks plastic? Lower denoise to 0.70 and re-test.
4. Looks soft and the source is clean? Try 4× on the same 30 seconds.
5. Choose a test section with faces or text, not a static shot.
6. Only then start the full run.
