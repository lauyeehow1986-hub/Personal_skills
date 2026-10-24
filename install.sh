#!/usr/bin/env bash
# Copy every skill into the personal skill folders of skill-aware coding agents.
#   ~/.claude/skills  - Claude Code
#   ~/.agents/skills  - shared location for Codex CLI, Gemini CLI, GitHub Copilot CLI
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
for dest in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
  mkdir -p "$dest"
  for skill in "$here"/skills/*/; do
    name="$(basename "$skill")"
    rm -rf "${dest:?}/$name"
    cp -R "$skill" "$dest/$name"
    echo "installed $name -> $dest/$name"
  done
done
