"""
archs.py - Self-contained network definitions for the restoration pipeline.

WHY THIS FILE EXISTS
--------------------
Every dependency problem you hit (KeyError: '__version__',
torchvision.transforms.functional_tensor) comes from ONE source: the `basicsr`
package. Real-ESRGAN imports basicsr purely to get the RRDBNet class definition,
and basicsr is an abandoned 2021-era package that breaks on modern toolchains.

The network definitions themselves are ~200 lines of plain PyTorch. They are
reproduced here verbatim in behaviour, so the official .pth checkpoints load
with strict=True. Nothing here imports basicsr, timm, or torchvision.

Dependencies: torch, numpy, einops.  That's it.

Checkpoint compatibility:
  RealESRGAN_x4plus.pth          -> RRDBNet(num_block=23, scale=4)
  RealESRGAN_x4plus_anime_6B.pth -> RRDBNet(num_block=6,  scale=4)
  realesr-general-x4v3.pth       -> SRVGGNetCompact(num_conv=32, upscale=4)
  scunet_color_real_psnr.pth     -> SCUNet(config=[4]*7, dim=64)
  scunet_color_real_gan.pth      -> SCUNet(config=[4]*7, dim=64)
"""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import rearrange
from einops.layers.torch import Rearrange

__all__ = [
    "RRDBNet",
    "SRVGGNetCompact",
    "SCUNet",
    "build_upscaler",
    "build_denoiser",
]


# =============================================================================
# Real-ESRGAN: RRDBNet  (used by RealESRGAN_x4plus / _anime_6B)
# =============================================================================


class ResidualDenseBlock(nn.Module):
    def __init__(self, num_feat: int = 64, num_grow_ch: int = 32):
        super().__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        # Empirically 0.2 residual scaling, per ESRGAN paper.
        return x5 * 0.2 + x


class RRDB(nn.Module):
    """Residual in Residual Dense Block."""

    def __init__(self, num_feat: int, num_grow_ch: int = 32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x):
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


class RRDBNet(nn.Module):
    """ESRGAN generator. Scale 4 is the only path we use, but 1/2 are kept
    so the class stays checkpoint-compatible with the official repo."""

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        scale: int = 4,
        num_feat: int = 64,
        num_block: int = 23,
        num_grow_ch: int = 32,
    ):
        super().__init__()
        self.scale = scale
        if scale == 2:
            num_in_ch = num_in_ch * 4
        elif scale == 1:
            num_in_ch = num_in_ch * 16

        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(
            *[RRDB(num_feat, num_grow_ch) for _ in range(num_block)]
        )
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        if self.scale == 2:
            feat = F.pixel_unshuffle(x, downscale_factor=2)
        elif self.scale == 1:
            feat = F.pixel_unshuffle(x, downscale_factor=4)
        else:
            feat = x

        feat = self.conv_first(feat)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


# =============================================================================
# Real-ESRGAN: SRVGGNetCompact  (used by realesr-general-x4v3)
# =============================================================================


class SRVGGNetCompact(nn.Module):
    """Lightweight VGG-style SR net. ~10x faster than RRDBNet, softer output.
    Useful for fast previews and for the optional WDN denoise-blend model."""

    def __init__(
        self,
        num_in_ch: int = 3,
        num_out_ch: int = 3,
        num_feat: int = 64,
        num_conv: int = 16,
        upscale: int = 4,
    ):
        super().__init__()
        self.upscale = upscale
        self.body = nn.ModuleList()
        self.body.append(nn.Conv2d(num_in_ch, num_feat, 3, 1, 1))
        self.body.append(nn.PReLU(num_parameters=num_feat))
        for _ in range(num_conv):
            self.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
            self.body.append(nn.PReLU(num_parameters=num_feat))
        self.body.append(nn.Conv2d(num_feat, num_out_ch * upscale * upscale, 3, 1, 1))
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)
        out = self.upsampler(out)
        # Residual against a nearest-neighbour upsample of the input.
        return out + F.interpolate(x, scale_factor=self.upscale, mode="nearest")


# =============================================================================
# SCUNet: Swin-Conv-UNet denoiser
# =============================================================================
#
# The upstream cszn/SCUNet implementation imports trunc_normal_ and DropPath
# from timm. Both are training-time-only constructs:
#   - trunc_normal_ initialises a parameter that is immediately overwritten by
#     the checkpoint we load.
#   - DropPath with drop_path_rate=0.0 (inference default) is nn.Identity.
# So we stub them and drop the timm dependency entirely.


def _trunc_normal_(tensor: torch.Tensor, std: float = 0.02) -> torch.Tensor:
    with torch.no_grad():
        return tensor.normal_(0.0, std).clamp_(-2 * std, 2 * std)


class WMSA(nn.Module):
    """(Shifted) window multi-head self-attention."""

    def __init__(self, input_dim, output_dim, head_dim, window_size, type):
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.head_dim = head_dim
        self.scale = self.head_dim ** -0.5
        self.n_heads = input_dim // head_dim
        self.window_size = window_size
        self.type = type

        self.embedding_layer = nn.Linear(self.input_dim, 3 * self.input_dim, bias=True)
        self.linear = nn.Linear(self.input_dim, self.output_dim)

        rpp = torch.zeros((2 * window_size - 1) * (2 * window_size - 1), self.n_heads)
        _trunc_normal_(rpp, std=0.02)
        rpp = rpp.view(2 * window_size - 1, 2 * window_size - 1, self.n_heads)
        rpp = rpp.transpose(1, 2).transpose(0, 1)
        self.relative_position_params = nn.Parameter(rpp)

        # Relative-position index table is constant; register once instead of
        # rebuilding it on every forward (upstream rebuilds it per call).
        cord = torch.tensor(
            [[i, j] for i in range(window_size) for j in range(window_size)]
        )
        relation = cord[:, None, :] - cord[None, :, :] + window_size - 1
        self.register_buffer("rel_idx_h", relation[:, :, 0].long(), persistent=False)
        self.register_buffer("rel_idx_w", relation[:, :, 1].long(), persistent=False)

    def generate_mask(self, h, w, p, shift):
        attn_mask = torch.zeros(
            h, w, p, p, p, p,
            dtype=torch.bool,
            device=self.relative_position_params.device,
        )
        if self.type == "W":
            return attn_mask
        s = p - shift
        attn_mask[-1, :, :s, :, s:, :] = True
        attn_mask[-1, :, s:, :, :s, :] = True
        attn_mask[:, -1, :, :s, :, s:] = True
        attn_mask[:, -1, :, s:, :, :s] = True
        return rearrange(attn_mask, "w1 w2 p1 p2 p3 p4 -> 1 1 (w1 w2) (p1 p2) (p3 p4)")

    def relative_embedding(self):
        return self.relative_position_params[:, self.rel_idx_h, self.rel_idx_w]

    def forward(self, x):
        if self.type != "W":
            shift = -(self.window_size // 2)
            x = torch.roll(x, shifts=(shift, shift), dims=(1, 2))

        x = rearrange(
            x, "b (w1 p1) (w2 p2) c -> b w1 w2 p1 p2 c",
            p1=self.window_size, p2=self.window_size,
        )
        h_windows, w_windows = x.size(1), x.size(2)
        x = rearrange(x, "b w1 w2 p1 p2 c -> b (w1 w2) (p1 p2) c")

        qkv = self.embedding_layer(x)
        q, k, v = rearrange(
            qkv, "b nw np (threeh c) -> threeh b nw np c", c=self.head_dim
        ).chunk(3, dim=0)

        sim = torch.einsum("hbwpc,hbwqc->hbwpq", q, k) * self.scale
        sim = sim + rearrange(self.relative_embedding(), "h p q -> h 1 1 p q")

        if self.type != "W":
            mask = self.generate_mask(
                h_windows, w_windows, self.window_size, shift=self.window_size // 2
            )
            # -inf in fp16 overflows; use the dtype's most-negative finite value.
            sim = sim.masked_fill(mask, torch.finfo(sim.dtype).min)

        probs = F.softmax(sim, dim=-1)
        out = torch.einsum("hbwij,hbwjc->hbwic", probs, v)
        out = rearrange(out, "h b w p c -> b w p (h c)")
        out = self.linear(out)
        out = rearrange(
            out, "b (w1 w2) (p1 p2) c -> b (w1 p1) (w2 p2) c",
            w1=h_windows, p1=self.window_size,
        )

        if self.type != "W":
            shift = self.window_size // 2
            out = torch.roll(out, shifts=(shift, shift), dims=(1, 2))
        return out


class SwinBlock(nn.Module):
    def __init__(self, input_dim, output_dim, head_dim, window_size,
                 drop_path, type="W", input_resolution=None):
        super().__init__()
        assert type in ("W", "SW")
        self.type = "W" if (input_resolution is not None
                            and input_resolution <= window_size) else type
        self.ln1 = nn.LayerNorm(input_dim)
        self.msa = WMSA(input_dim, input_dim, head_dim, window_size, self.type)
        self.ln2 = nn.LayerNorm(input_dim)
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, 4 * input_dim),
            nn.GELU(),
            nn.Linear(4 * input_dim, output_dim),
        )
        # drop_path is identity at inference (drop_path_rate=0.0).

    def forward(self, x):
        x = x + self.msa(self.ln1(x))
        x = x + self.mlp(self.ln2(x))
        return x


class ConvTransBlock(nn.Module):
    """Half the channels go through a conv branch, half through a Swin branch."""

    def __init__(self, conv_dim, trans_dim, head_dim, window_size,
                 drop_path, type="W", input_resolution=None):
        super().__init__()
        self.conv_dim = conv_dim
        self.trans_dim = trans_dim
        assert type in ("W", "SW")
        self.type = "W" if (input_resolution is not None
                            and input_resolution <= window_size) else type

        self.trans_block = SwinBlock(
            trans_dim, trans_dim, head_dim, window_size,
            drop_path, self.type, input_resolution,
        )
        self.conv1_1 = nn.Conv2d(conv_dim + trans_dim, conv_dim + trans_dim, 1, 1, 0, bias=True)
        self.conv1_2 = nn.Conv2d(conv_dim + trans_dim, conv_dim + trans_dim, 1, 1, 0, bias=True)
        self.conv_block = nn.Sequential(
            nn.Conv2d(conv_dim, conv_dim, 3, 1, 1, bias=False),
            nn.ReLU(True),
            nn.Conv2d(conv_dim, conv_dim, 3, 1, 1, bias=False),
        )

    def forward(self, x):
        conv_x, trans_x = torch.split(
            self.conv1_1(x), (self.conv_dim, self.trans_dim), dim=1
        )
        conv_x = self.conv_block(conv_x) + conv_x
        trans_x = Rearrange("b c h w -> b h w c")(trans_x)
        trans_x = self.trans_block(trans_x)
        trans_x = Rearrange("b h w c -> b c h w")(trans_x)
        res = self.conv1_2(torch.cat((conv_x, trans_x), dim=1))
        return x + res


class SCUNet(nn.Module):
    def __init__(self, in_nc=3, config=None, dim=64,
                 drop_path_rate=0.0, input_resolution=256):
        super().__init__()
        config = config if config is not None else [4, 4, 4, 4, 4, 4, 4]
        self.config = config
        self.dim = dim
        self.head_dim = 32
        self.window_size = 8
        d = dim
        ws, hd = self.window_size, self.head_dim

        def ctb(c, res, i):
            return ConvTransBlock(c, c, hd, ws, 0.0, "W" if not i % 2 else "SW", res)

        self.m_head = nn.Sequential(nn.Conv2d(in_nc, d, 3, 1, 1, bias=False))

        self.m_down1 = nn.Sequential(
            *[ctb(d // 2, input_resolution, i) for i in range(config[0])],
            nn.Conv2d(d, 2 * d, 2, 2, 0, bias=False),
        )
        self.m_down2 = nn.Sequential(
            *[ctb(d, input_resolution // 2, i) for i in range(config[1])],
            nn.Conv2d(2 * d, 4 * d, 2, 2, 0, bias=False),
        )
        self.m_down3 = nn.Sequential(
            *[ctb(2 * d, input_resolution // 4, i) for i in range(config[2])],
            nn.Conv2d(4 * d, 8 * d, 2, 2, 0, bias=False),
        )
        self.m_body = nn.Sequential(
            *[ctb(4 * d, input_resolution // 8, i) for i in range(config[3])]
        )
        self.m_up3 = nn.Sequential(
            nn.ConvTranspose2d(8 * d, 4 * d, 2, 2, 0, bias=False),
            *[ctb(2 * d, input_resolution // 4, i) for i in range(config[4])],
        )
        self.m_up2 = nn.Sequential(
            nn.ConvTranspose2d(4 * d, 2 * d, 2, 2, 0, bias=False),
            *[ctb(d, input_resolution // 2, i) for i in range(config[5])],
        )
        self.m_up1 = nn.Sequential(
            nn.ConvTranspose2d(2 * d, d, 2, 2, 0, bias=False),
            *[ctb(d // 2, input_resolution, i) for i in range(config[6])],
        )
        self.m_tail = nn.Sequential(nn.Conv2d(d, in_nc, 3, 1, 1, bias=False))

    def forward(self, x0):
        h, w = x0.size()[-2:]
        # Three 2x downsamples + 8px windows => input must be a multiple of 64.
        pad_b = int(np.ceil(h / 64) * 64 - h)
        pad_r = int(np.ceil(w / 64) * 64 - w)
        if pad_b or pad_r:
            x0 = nn.ReplicationPad2d((0, pad_r, 0, pad_b))(x0)

        x1 = self.m_head(x0)
        x2 = self.m_down1(x1)
        x3 = self.m_down2(x2)
        x4 = self.m_down3(x3)
        x = self.m_body(x4)
        x = self.m_up3(x + x4)
        x = self.m_up2(x + x3)
        x = self.m_up1(x + x2)
        x = self.m_tail(x + x1)
        return x[..., :h, :w]


# =============================================================================
# Checkpoint loading
# =============================================================================


def _extract_state_dict(ckpt):
    """Official weights are wrapped inconsistently: Real-ESRGAN uses
    'params_ema' or 'params', SCUNet ships a bare state_dict."""
    if isinstance(ckpt, dict):
        for key in ("params_ema", "params", "state_dict", "model"):
            if key in ckpt and isinstance(ckpt[key], dict):
                return ckpt[key]
    return ckpt


def _load(model: nn.Module, path, device):
    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError:
        # weights_only kwarg only exists on torch >= 1.13
        ckpt = torch.load(path, map_location="cpu")
    sd = _extract_state_dict(ckpt)
    # Strip DataParallel prefixes if present.
    if any(k.startswith("module.") for k in sd):
        sd = {k.replace("module.", "", 1): v for k, v in sd.items()}
    model.load_state_dict(sd, strict=True)
    return model.eval().to(device)


def build_upscaler(path, device, model_name: str | None = None) -> nn.Module:
    """Instantiate the right Real-ESRGAN architecture for a checkpoint."""
    name = (model_name or str(path)).lower()
    if "anime" in name or "6b" in name:
        net = RRDBNet(scale=4, num_block=6)
    elif "general" in name or "v3" in name:
        net = SRVGGNetCompact(num_conv=32, upscale=4)
    else:
        net = RRDBNet(scale=4, num_block=23)
    for p in net.parameters():
        p.requires_grad_(False)
    return _load(net, path, device)


def build_denoiser(path, device) -> nn.Module:
    net = SCUNet(in_nc=3, config=[4] * 7, dim=64)
    for p in net.parameters():
        p.requires_grad_(False)
    return _load(net, path, device)
