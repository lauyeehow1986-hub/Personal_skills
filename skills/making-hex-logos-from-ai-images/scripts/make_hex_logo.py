#!/usr/bin/env python3
"""Turn an AI-generated hex-sticker image (Gemini, ChatGPT, Midjourney, ...) into
a transparent package logo, a pkgdown-ready favicon set and a GitHub social card.

Only needs Pillow (pip install pillow). No network calls.

    python make_hex_logo.py artwork.jpg --name mypkg --out path/to/package \
        --preview hex_preview.png --social social-preview.png \
        --tagline "One-line pitch." --url "user.github.io/mypkg"

Run with --help for every option.
"""
import argparse
import base64
import io
import json
import math
import os
import sys
from collections import Counter, deque

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("image", help="source artwork (jpg/png/webp)")
    p.add_argument("--name", required=True, help="package name (manifest + social card title)")
    p.add_argument("--out", default=".", help="package root; output paths below are relative to it")
    p.add_argument("--logo", default="man/figures/logo.png", help="logo path ('' to skip)")
    p.add_argument("--favicon-dir", default="pkgdown/favicon", help="favicon folder ('' to skip)")
    p.add_argument("--social", default="", help="1280x640 social card path ('' to skip)")
    p.add_argument("--tagline", action="append", default=[], help="social card paragraph (repeatable)")
    p.add_argument("--url", default="", help="footer text on the social card, e.g. user.github.io/pkg")
    p.add_argument("--preview", default="", help="write the source with the detected hexagon drawn on it")
    p.add_argument("--orientation", choices=["auto", "pointy", "flat"], default="auto",
                   help="pointy-top (R hex stickers) or flat-top; auto picks from the aspect ratio")
    p.add_argument("--bbox", default="", help="x0,y0,x1,y1 of the hexagon; skips auto-detection")
    p.add_argument("--inset", type=float, default=1.5,
                   help="px trimmed inside the hex edge so no background fringe survives")
    p.add_argument("--tolerance", type=int, default=None,
                   help="max per-channel difference still counted as background (0-255); "
                        "default sweeps 10-60 and keeps the largest regular hexagon")
    p.add_argument("--logo-height", type=int, default=693, help="logo height in px (R convention ~ 600x693)")
    p.add_argument("--colors", type=int, default=256,
                   help="palette size for logo.png (keeps it ~60 KB); 0 keeps full colour")
    p.add_argument("--icon-bg", default="", help="hex colour behind opaque icons; default = artwork background")
    p.add_argument("--detect-only", action="store_true", help="print the detected bbox and stop")
    return p.parse_args(argv)


# ---------------------------------------------------------------- detection

def background_colours(img):
    """Colours that cover >= 5% of the image border. Handles flat backgrounds and the
    fake 'transparent' checkerboards some generators paint."""
    w, h = img.size
    px = img.load()
    border = ([px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)] +
              [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)])
    buckets = {}
    for c in border:
        buckets.setdefault((c[0] // 24, c[1] // 24, c[2] // 24), []).append(c)
    keep = [v for v in buckets.values() if len(v) >= 0.05 * len(border)]
    keep.sort(key=len, reverse=True)
    return [tuple(sum(ch) // len(v) for ch in zip(*v)) for v in keep] or [px[0, 0]]


def foreground_mask(img, bgs, tol):
    """255 where a pixel differs from every background colour by more than tol in some channel."""
    mask = None
    for bg in bgs:
        diff = ImageChops.difference(img, Image.new("RGB", img.size, bg))
        r, g, b = diff.split()
        far = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v > tol else 0)
        mask = far if mask is None else ImageChops.darker(mask, far)
    return mask


def largest_component_bbox(mask):
    """Bounding box of the biggest 4-connected blob (drops watermarks, stray text, sparkles)."""
    w, h = mask.size
    data = mask.load()
    seen = bytearray(w * h)
    best, best_n = None, 0
    for y0 in range(h):
        for x0 in range(w):
            if data[x0, y0] == 0 or seen[y0 * w + x0]:
                continue
            q = deque([(x0, y0)])
            seen[y0 * w + x0] = 1
            n, bx0, by0, bx1, by1 = 0, x0, y0, x0, y0
            while q:
                x, y = q.popleft()
                n += 1
                bx0, by0, bx1, by1 = min(bx0, x), min(by0, y), max(bx1, x), max(by1, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and data[nx, ny] and not seen[ny * w + nx]:
                        seen[ny * w + nx] = 1
                        q.append((nx, ny))
            if n > best_n:
                best, best_n = (bx0, by0, bx1, by1), n
    return best


def bbox_at_tolerance(img, bgs, tol):
    mask = foreground_mask(img, bgs, tol)
    # Work on a <= 400 px copy, opened to cut thin grid lines, noise and sparkles.
    s = max(1.0, max(img.size) / 400)
    small = mask.resize((round(img.width / s), round(img.height / s)), Image.BILINEAR)
    small = small.point(lambda v: 255 if v > 127 else 0)
    small = small.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    bb = largest_component_bbox(small)
    if bb is None:
        return None
    # Refine at full resolution inside the coarse box (plus a margin).
    m = math.ceil(3 * s)
    box = (max(0, int(bb[0] * s) - m), max(0, int(bb[1] * s) - m),
           min(img.width, int((bb[2] + 1) * s) + m), min(img.height, int((bb[3] + 1) * s) + m))
    inner = mask.crop(box).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3)).getbbox()
    if inner is None:
        return box
    return (box[0] + inner[0], box[1] + inner[1], box[0] + inner[2], box[1] + inner[3])


def aspect(bb):
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    return min(w, h) / max(w, h)


def detect_hex_bbox(img, tol=None):
    """With tol=None, sweep tolerances and keep the LARGEST box that is still a regular
    hexagon (aspect 0.866): low tolerances catch dark outer rims, while the regularity
    check rejects boxes swollen by glows, grid lines or captions."""
    bgs = background_colours(img)
    tols = [tol] if tol is not None else [10, 12, 15, 18, 22, 27, 33, 40, 50, 60]
    found = [(t, bb) for t in tols if (bb := bbox_at_tolerance(img, bgs, t))]
    if not found:
        sys.exit("No foreground found: pass --bbox x0,y0,x1,y1 or adjust --tolerance.")
    regular = [(t, bb) for t, bb in found if abs(aspect(bb) - 0.866) <= 0.015]
    if regular:
        t, bb = max(regular, key=lambda f: (f[1][2] - f[1][0]) * (f[1][3] - f[1][1]))
    else:
        t, bb = min(found, key=lambda f: abs(aspect(f[1]) - 0.866))
    return bb, bgs, t


def hex_points(bbox, orientation, inset):
    x0, y0, x1, y1 = bbox
    w, h = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if orientation == "auto":
        orientation = "pointy" if w < h else "flat"
    if orientation == "pointy":
        pts = [(cx, y0), (x1, y0 + h / 4), (x1, y1 - h / 4),
               (cx, y1), (x0, y1 - h / 4), (x0, y0 + h / 4)]
    else:
        pts = [(x0, cy), (x0 + w / 4, y0), (x1 - w / 4, y0),
               (x1, cy), (x1 - w / 4, y1), (x0 + w / 4, y1)]
    out = []
    for x, y in pts:  # pull every vertex toward the centre by `inset` px
        d = math.hypot(x - cx, y - cy) or 1
        k = (d - inset) / d
        out.append((cx + (x - cx) * k, cy + (y - cy) * k))
    return out, orientation


# ---------------------------------------------------------------- outputs

def cut_hex(src, pts, bbox):
    ss = 4  # supersampled mask for smooth anti-aliased edges
    big = Image.new("L", (src.width * ss, src.height * ss), 0)
    ImageDraw.Draw(big).polygon([(x * ss, y * ss) for x, y in pts], fill=255)
    rgba = src.convert("RGBA")
    rgba.putalpha(big.resize(src.size, Image.LANCZOS))
    x0, y0, x1, y1 = bbox
    return rgba.crop((math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1)))


def fit(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), h), Image.LANCZOS)


def on_square(hexlogo, size, frac, bg=None):
    canvas = Image.new("RGBA", (size, size), (bg + (255,)) if bg else (0, 0, 0, 0))
    icon = fit(hexlogo, round(size * frac))
    canvas.alpha_composite(icon, ((size - icon.width) // 2, (size - icon.height) // 2))
    return canvas


def write_favicons(hexlogo, folder, name, bg):
    os.makedirs(folder, exist_ok=True)
    j = lambda f: os.path.join(folder, f)
    on_square(hexlogo, 96, 1.0).save(j("favicon-96x96.png"), optimize=True)
    on_square(hexlogo, 256, 1.0).save(j("favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    on_square(hexlogo, 180, 0.86, bg).convert("RGB").save(j("apple-touch-icon.png"), optimize=True)
    # Maskable icons keep the artwork inside the central 80% safe zone.
    on_square(hexlogo, 192, 0.78, bg).convert("RGB").save(j("web-app-manifest-192x192.png"), optimize=True)
    on_square(hexlogo, 512, 0.78, bg).convert("RGB").save(j("web-app-manifest-512x512.png"), optimize=True)
    # favicon.svg wraps a small PNG: the artwork is raster, and a big embed bloats every page load.
    small = fit(hexlogo, 64)
    buf = io.BytesIO()
    small.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    w = small.width * 3
    with open(j("favicon.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'viewBox="0 0 {w} 192" width="{w}" height="192"><image width="{w}" height="192" '
                f'xlink:href="data:image/png;base64,{b64}" href="data:image/png;base64,{b64}"/></svg>\n')
    manifest = {
        "name": name, "short_name": name,
        "icons": [{"src": f"/web-app-manifest-{s}x{s}.png", "sizes": f"{s}x{s}",
                   "type": "image/png", "purpose": "maskable"} for s in (192, 512)],
        "theme_color": "#ffffff", "background_color": "#%02x%02x%02x" % bg, "display": "standalone",
    }
    with open(j("site.webmanifest"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


FONT_DIRS = ["C:/Windows/Fonts", "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
             "/Library/Fonts", os.path.expanduser("~/Library/Fonts"), "/usr/share/fonts",
             "/usr/local/share/fonts", os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts")]
BOLD = ["bahnschrift.ttf", "segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf",
        "LiberationSans-Bold.ttf", "NotoSans-Bold.ttf", "Helvetica.ttc"]
REGULAR = ["segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf",
           "NotoSans-Regular.ttf", "Helvetica.ttc"]


def find_font(names, size):
    for d in FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for n in names:
                if n in files:
                    try:
                        return ImageFont.truetype(os.path.join(root, n), size)
                    except OSError:
                        pass
    try:
        return ImageFont.load_default(size)  # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def luminance(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def accent_colour(hexlogo, fallback):
    """Most common bright, saturated colour in the artwork (used for the card title)."""
    counts = Counter()
    raw = fit(hexlogo, 120).tobytes()  # RGBA bytes; getdata() is deprecated in Pillow 12
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i:i + 4]
        mx, mn = max(r, g, b), min(r, g, b)
        if a > 200 and mx > 140 and (mx - mn) / mx > 0.35:
            counts[(r // 32 * 32 + 16, g // 32 * 32 + 16, b // 32 * 32 + 16)] += 1
    return counts.most_common(1)[0][0] if counts else fallback


def social_card(hexlogo, path, name, taglines, url, bg):
    W, H = 1280, 640
    dark = luminance(bg) < 128
    text = (226, 232, 240) if dark else (30, 41, 59)
    muted = (148, 163, 184) if dark else (71, 85, 105)
    card = Image.new("RGBA", (W, H), bg + (255,))
    big = fit(hexlogo, 540)
    if dark:  # soft glow behind the hex
        glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        glow.alpha_composite(big, (70, 50))
        card.alpha_composite(Image.eval(glow.filter(ImageFilter.GaussianBlur(18)), lambda v: v // 3))
    card.alpha_composite(big, (70, 50))
    d = ImageDraw.Draw(card)
    tx = 70 + big.width + 60
    max_w = W - tx - 50
    title = find_font(BOLD, 92)
    while d.textlength(name, font=title) > max_w and title.size > 40:
        title = find_font(BOLD, title.size - 6)
    body, small = find_font(REGULAR, 32), find_font(REGULAR, 26)
    d.text((tx, 140), name, font=title, fill=accent_colour(hexlogo, text) + (255,))
    y = 270
    for para in taglines:
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if d.textlength(trial, font=body) <= max_w:
                line = trial
            else:
                d.text((tx, y), line, font=body, fill=text + (255,))
                y, line = y + 44, word
        d.text((tx, y), line, font=body, fill=text + (255,))
        y += 64
    if url:
        d.text((tx, 545), url, font=small, fill=muted + (255,))
    card.convert("RGB").save(path, optimize=True)


def parse_colour(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def main(argv=None):
    a = parse_args(argv)
    src = Image.open(a.image).convert("RGB")
    if a.bbox:
        bbox = tuple(float(v) for v in a.bbox.split(","))
        bgs = background_colours(src)
    else:
        bbox, bgs, tol = detect_hex_bbox(src, a.tolerance)
        print(f"tolerance {tol}")
    pts, orient = hex_points(bbox, a.orientation, a.inset)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    ratio = min(w, h) / max(w, h)
    print(f"source {src.size}  background {bgs[0]}  hex bbox {tuple(round(v) for v in bbox)}  "
          f"{orient}-top  aspect {ratio:.3f} (regular hex = 0.866)")
    if abs(ratio - 0.866) > 0.04:
        print("WARNING: aspect is far from a regular hexagon - check --preview; the box may include "
              "a shadow, glow, watermark or text. Pass --bbox to override.")
    if a.preview:
        pv = src.copy()
        dr = ImageDraw.Draw(pv)
        dr.polygon(pts, outline=(255, 0, 64), width=max(2, src.width // 300))
        dr.rectangle(bbox, outline=(255, 210, 0), width=1)
        pv.save(a.preview)
        print("preview", a.preview)
    if a.detect_only:
        return
    hexlogo = cut_hex(src, pts, bbox)
    icon_bg = parse_colour(a.icon_bg) if a.icon_bg else bgs[0]
    root = a.out
    if a.logo:
        path = os.path.join(root, a.logo)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        logo = fit(hexlogo, a.logo_height)
        if a.colors:
            logo = logo.quantize(colors=a.colors, method=Image.Quantize.FASTOCTREE,
                                 dither=Image.Dither.FLOYDSTEINBERG)
        logo.save(path, optimize=True)
        print("logo", path, logo.size, f"{os.path.getsize(path) // 1024} KB")
        svg = os.path.splitext(path)[0] + ".svg"
        if os.path.exists(svg):
            print(f"WARNING: {svg} exists and pkgdown prefers it over the PNG - delete it.")
    if a.favicon_dir:
        write_favicons(hexlogo, os.path.join(root, a.favicon_dir), a.name, icon_bg)
        print("favicons", os.path.join(root, a.favicon_dir))
    if a.social:
        social_card(hexlogo, a.social, a.name, a.tagline, a.url, icon_bg)
        print("social card", a.social)


if __name__ == "__main__":
    main()
