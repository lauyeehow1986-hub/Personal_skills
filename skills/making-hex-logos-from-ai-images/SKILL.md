---
name: making-hex-logos-from-ai-images
description: Use when a user supplies AI-generated artwork (Gemini, ChatGPT/DALL-E, Midjourney, Imagen) or any raster image of a hex sticker and wants it as a package logo, README logo, pkgdown/GitHub Pages favicon set or GitHub social preview card - including when the image has a solid, gridded, glowing or fake-checkerboard "transparent" background, a watermark, or a caption outside the hexagon.
---

# Making hex logos from AI images

## Overview
AI image generators never return a usable logo: the hexagon sits on an opaque (often fake
"transparent" checkerboard) background, with glows, grid lines, watermarks or captions around it.
The fix is to **fit the hexagon geometrically and cut along it**, not to colour-key the background
(colour keys eat dark rims and leave fringes). `scripts/make_hex_logo.py` (Pillow only, offline)
detects the hexagon, cuts it with an anti-aliased mask and writes every asset a package site needs.

## When to use
- "Use this image as the logo / for the GitHub page / favicon / social preview."
- The source is a JPG/PNG/WebP of a hex sticker, pointy-top (R convention) or flat-top.
- **Not** for vector logos (an SVG that already has transparency): use it directly.
- **Not** for non-hexagonal logos: the cut is a hexagon. Crop those by hand.

## Quick reference

| Output (relative to `--out`) | Size | Used by |
|---|---|---|
| `man/figures/logo.png` (`--logo`) | 600x693, 256 colours, ~60 KB | README `<img>`, pkgdown navbar + home |
| `pkgdown/favicon/favicon.ico`, `favicon-96x96.png`, `favicon.svg` | transparent | browser tabs |
| `pkgdown/favicon/apple-touch-icon.png`, `web-app-manifest-{192,512}.png` | opaque, artwork bg colour | home-screen / PWA icons |
| `pkgdown/favicon/site.webmanifest` | | names the site, sets `background_color` |
| `--social card.png` | 1280x640 | GitHub repo social preview (uploaded by hand) |

The favicon file names are exactly what `pkgdown::build_favicons()` produces, so pkgdown copies
them into the site without calling the realfavicongenerator web API.

## Steps
1. Save the image the user gave you to a file **outside the repo** (never commit the raw art).
2. Detect and look before writing anything:
   ```bash
   python scripts/make_hex_logo.py art.jpg --name mypkg --detect-only --preview hex_preview.png
   ```
   Open `hex_preview.png` and check the red outline sits on the hexagon's outer edge. The script
   prints the box and its aspect (a regular hexagon is 0.866). If the outline is wrong, pass
   `--bbox x0,y0,x1,y1` (and `--orientation pointy|flat` if needed) and re-check.
3. Generate everything from the package root:
   ```bash
   python scripts/make_hex_logo.py art.jpg --name mypkg --out . \
     --social /tmp/social-preview.png \
     --tagline "One-sentence pitch." --tagline "Second paragraph (optional)." \
     --url "user.github.io/mypkg"
   ```
4. Delete any old `man/figures/logo.svg` (the script warns). pkgdown prefers an SVG over the PNG.
5. Reference the logo in the README title line:
   `# mypkg: Title <img src="man/figures/logo.png" align="right" height="150" alt="mypkg hex logo" />`
6. Rebuild the site (see the building-r-package-sites skill) and check the navbar logo, the tab
   icon and `<pkg>/logo.png` on the live site. Hard-refresh first, because browsers cache favicons hard.
7. Give the user the social card file. It is **not** committed. They upload it under GitHub repo
   **Settings > General > Social preview**, since there is no API for this.

## Asking for artwork (when the user has none yet)
Prompt the generator with: *"Hex sticker logo for an R package called `<name>`: a pointy-top
hexagon with a thick contrasting border, `<motif>`, the word `<name>` inside the hexagon,
centred, on a plain solid dark background with no shadow, no text outside the hexagon, square 1:1."*
A plain background and nothing outside the hexagon make detection trivial.

## Common mistakes
| Mistake | Fix |
|---|---|
| Skipping the preview | Glows, drop shadows and captions can pull the box outward. Always look. |
| Colour-keying the background (flood fill / "remove bg") | Dark outer rims and anti-aliased edges vanish or leave halos. Cut the geometric hexagon. |
| Committing a 400 KB full-colour logo | Keep `--colors 256`. It looks identical at 150 px and loads 6x faster. |
| Embedding the full-size PNG in `favicon.svg` | It ships on every page. The script embeds 64 px. |
| Leaving `logo.svg` next to the new `logo.png` | pkgdown shows the stale SVG. |
| Expecting the social card to appear after a push | It is a manual upload in repo settings. |
| Hex touches the image border, or the background is busy | Detection needs a margin. Pass `--bbox`. |

Requires Python 3.8+ and Pillow (`pip install pillow`). Run `python scripts/make_hex_logo.py --help` for every option.
