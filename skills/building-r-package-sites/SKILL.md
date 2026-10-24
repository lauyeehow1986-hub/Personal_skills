---
name: building-r-package-sites
description: Use when creating, redesigning or publishing the GitHub Pages / pkgdown website or README home page of an R package - including when the site looks cluttered or broken on phones, publishes CLAUDE.md / AGENTS.md / MEMORY.md as pages, shows a stale logo, fails check_pkgdown on missing topics, or deploys inconsistently from GitHub Actions and the docs/ folder.
---

# Building R package sites

## Overview
A clean package site is the **default pkgdown Bootstrap 5 template plus a short, structured README**:
no bootswatch theme, no custom navbar, no feature essays on the home page. pkgdown turns the
README into the home page, so most of the work is the README. Add a logo, a reference index that
`check_pkgdown()` accepts, a site free of agent notes, and **one** deployment path.

## The layout (what "done" looks like)
**README.md** (from `templates/README.md`), in this order:
1. `# pkg: Title From DESCRIPTION <img src="man/figures/logo.png" align="right" height="150" alt="pkg hex logo" />`
2. A badges block of at most 3-4 badges. Prefer live workflow badges over static ones.
3. One intro paragraph, 2-3 sentences, with the key phrases in bold.
4. `## Installation`, with the `remotes::install_github()` line and CRAN or r-universe if available.
5. `## Key Features`: bullets of the form `- **Title Case Label**: one sentence naming the function`, nested for groups.
6. `## Quick Start`: one runnable block with numbered comments, 3-4 steps.
7. One closing line, such as a pointer or a disclaimer.

Leave out API tables, option tables, architecture diagrams and emoji tables. They belong in the
reference pages, `?topic` and vignettes, and they wreck the phone layout.

**_pkgdown.yml** (from `templates/_pkgdown.yml`): `url:`, `template: bootstrap: 5`, and a task-grouped
`reference:` index. Nothing else.

## Steps
1. **Inventory:** read DESCRIPTION (Title, URL, BugReports), `NAMESPACE` exports, whether `README.Rmd`
   exists, and what is in `man/figures/`. If `README.Rmd` exists, edit it and run
   `devtools::build_readme()`. Never hand-edit the generated `.md`.
2. **Logo:** if the user gave you raster or AI artwork, **REQUIRED SUB-SKILL:** making-hex-logos-from-ai-images.
   Otherwise put the logo at `man/figures/logo.png`, and delete any stale `logo.svg` (pkgdown prefers the SVG).
3. **README:** write it from the template. **Run the Quick Start code** in a fresh R session; it must work.
4. **Config:** write `_pkgdown.yml`, then loop `pkgdown::check_pkgdown()` until it is clean. Every export
   must be in some `contents:`, and `starts_with()` / `matches()` help.
5. **DESCRIPTION:** set `URL: https://OWNER.github.io/PKG/, https://github.com/OWNER/PKG` and `BugReports:`.
6. **.Rbuildignore:** add `^_pkgdown\.yml$`, `^docs$`, `^pkgdown$` and `^\.github$`, plus every agent-notes file.
7. **Build:** run `Rscript -e "pkgdown::build_site(preview = FALSE)"`. Keep the default
   `install = TRUE`, because `install = FALSE` fails with "there is no package called ..." unless the
   current version is already installed. If Pandoc is missing, set `RSTUDIO_PANDOC` to RStudio's
   bundled copy (on Windows, `C:/Program Files/RStudio/resources/app/bin/quarto/bin/tools`).
8. **Scrub agent notes:** run `Rscript scripts/scrub_site.R docs`. pkgdown renders **every root `*.md`**
   (CLAUDE.md, AGENTS.md, MEMORY.md, GEMINI.md, ...) and ignores `.Rbuildignore`.
9. **Look at it:** run `python -m http.server 8000 --directory docs`, then check the home page,
   `reference/` and one topic at desktop width and at **375 px**. Look for the light navbar, the logo
   beside the title, sections that read on a phone, and code blocks that scroll sideways.
10. **Deploy with exactly ONE path:**

| | Option A: committed `docs/` (simplest) | Option B: GitHub Actions |
|---|---|---|
| Pages source | `gh api -X POST repos/O/R/pages -f "source[branch]=main" -f "source[path]=/docs"` (`-X PUT` if Pages exists) | `gh api -X POST repos/O/R/pages -f build_type=workflow` (`-X PUT` if Pages exists) |
| Repo | commit `docs/` after every rebuild and scrub | `.github/workflows/pkgdown.yaml` from `templates/`; add `docs/` to `.gitignore` |
| Scrub | step 8, locally | built into the template workflow |

   Running both makes two deploys race on every push, and whichever finishes last wins.
11. **Repo metadata:** run `gh repo edit O/R --homepage https://O.github.io/R/ --description "<Title>"`.
    The social preview is a manual upload under Settings > General.
12. **Verify live:** watch `gh run list -L 4` until the runs finish. Then `curl -s -o /dev/null -w "%{http_code}"`
    must return 200 for `/`, `/reference/` and `/logo.png`, and 404 for `/CLAUDE.html` and `/AGENTS.html`.
    View the live home page at phone width once.

## Common mistakes
| Symptom | Cause / fix |
|---|---|
| Agent notes are on the site or in search results | Root `*.md` files are rendered. Scrub (step 8) and remove them from `sitemap.xml` and `search.json` too. |
| Old logo still shows | A stale `man/figures/logo.svg`, or browser cache. Delete it, then hard-refresh. |
| `check_pkgdown()`: "topics missing from index" | A new export was not added to `reference:`. |
| The live site flips between versions | Both Pages paths are active. Pick A or B (step 10). |
| Cramped or overflowing on phones | Bootswatch or custom navbar, wide tables, long badge rows. Go back to the layout above. |
| No search or sitemap | `url:` is missing from `_pkgdown.yml`. |
| Windows: "Total path length must be less than PATH_MAX: 260" | The package sits in a deep folder. Build from a short path (e.g. `C:/src/pkg`). |
| README and site disagree | `README.Rmd` was not re-knit. |
| `search.json` corrupted after a scrub | Rewriting it with jsonlite defaults turns `null` into `{}`. Use the script, which passes `null = "null"`. |
