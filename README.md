# Personal skills

Reusable skills for coding agents, in the open [Agent Skills](https://agentskills.io/specification)
format. Each skill is a folder with a `SKILL.md` (YAML `name` + `description`, then instructions)
and optional `scripts/` and `templates/`. They are plain Markdown plus small scripts, so any agent
that can read files can use them.

| Skill | Use it when |
|---|---|
| [building-r-package-sites](skills/building-r-package-sites/SKILL.md) | Creating or redesigning an R package's pkgdown / GitHub Pages site and README home page |
| [making-hex-logos-from-ai-images](skills/making-hex-logos-from-ai-images/SKILL.md) | Turning AI-generated hex-sticker art (Gemini, ChatGPT, ...) into a package logo, favicons and a social card |

## Install

**Claude Code, Codex CLI, Gemini CLI, GitHub Copilot CLI** (skill-aware agents):

```bash
git clone https://github.com/lauyeehow1986-hub/Personal_skills.git
cd Personal_skills
bash install.sh            # macOS / Linux / Git Bash
```

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1   # Windows PowerShell
```

The script copies every skill into `~/.claude/skills/` (Claude Code) and `~/.agents/skills/`
(the shared location read by Codex, Gemini CLI and Copilot CLI). Re-run it after `git pull`.
To scope skills to one project instead, copy the folders into that repo's `.claude/skills/` or
`.agents/skills/`.

**Any other agent** (Cursor, Windsurf, Aider, Cline, a chat model, ...): add this repo's
[AGENTS.md](AGENTS.md) to the agent's rules or context, or say *"Read
skills/<name>/SKILL.md from https://github.com/lauyeehow1986-hub/Personal_skills and follow it."*

## Requirements
- `building-r-package-sites`: R with `pkgdown`, `jsonlite` and (for GitHub steps) the `gh` CLI.
- `making-hex-logos-from-ai-images`: Python 3.8+ with Pillow (`pip install pillow`). No network access needed.

## Layout
```
skills/
  <skill-name>/
    SKILL.md        # when to use + the procedure
    scripts/        # tools the procedure runs
    templates/      # files the procedure copies into a project
```
