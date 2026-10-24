# Remove agent/dev-note pages from a built pkgdown site.
#
# pkgdown renders every root *.md (and .github/*.md) except README, LICENSE, NEWS,
# cran-comments and the GitHub templates, and it ignores .Rbuildignore. So CLAUDE.md,
# AGENTS.md, MEMORY.md, GEMINI.md, ... become public pages, sitemap entries and search hits.
#
# Usage (from the package root, after pkgdown::build_site()):
#   Rscript scrub_site.R                    # docs/, default note names
#   Rscript scrub_site.R docs CLAUDE AGENTS # custom folder and stems

args  <- commandArgs(trailingOnly = TRUE)
docs  <- if (length(args) >= 1) args[[1]] else "docs"
stems <- if (length(args) >= 2) args[-1] else
  c("CLAUDE", "AGENTS", "MEMORY", "GEMINI", "COPILOT", "CURSOR", "TODO")

if (!dir.exists(docs)) stop("No site folder at ", docs, call. = FALSE)
pattern <- paste0("/(", paste(stems, collapse = "|"), ")\\.html")

pages <- file.path(docs, paste0(rep(stems, each = 2), c(".html", ".md")))
removed <- pages[file.exists(pages)]
unlink(removed)

sitemap <- file.path(docs, "sitemap.xml")
if (file.exists(sitemap)) {
  lines <- readLines(sitemap, warn = FALSE)
  writeLines(lines[!grepl(pattern, lines)], sitemap)
}

search <- file.path(docs, "search.json")
if (file.exists(search)) {
  idx  <- jsonlite::read_json(search, simplifyVector = FALSE)
  # `path` can be a string or a list, so match on its JSON text.
  keep <- vapply(idx, function(x) !grepl(pattern, jsonlite::toJSON(x$path, auto_unbox = TRUE)), logical(1))
  # null = "null" and digits = NA leave the remaining entries unchanged (no {} for null, no rounding).
  jsonlite::write_json(idx[keep], search, auto_unbox = TRUE, null = "null", digits = NA)
}

left <- unlist(lapply(c(sitemap, search)[file.exists(c(sitemap, search))], function(f)
  grep(pattern, readLines(f, warn = FALSE), value = TRUE)))
cat("Removed:", if (length(removed)) basename(removed) else "nothing", "\n")
if (length(left)) stop("Still referenced: ", paste(left, collapse = " | "), call. = FALSE)
cat("Site is clean of:", paste(stems, collapse = ", "), "\n")
