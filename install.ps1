# Copy every skill into the personal skill folders of skill-aware coding agents.
#   ~/.claude/skills  - Claude Code
#   ~/.agents/skills  - shared location for Codex CLI, Gemini CLI, GitHub Copilot CLI
param([string]$Root = $HOME)  # e.g. -Root C:\path to install somewhere else
$ErrorActionPreference = 'Stop'
$skills = Join-Path $PSScriptRoot 'skills'
foreach ($dest in @((Join-Path $Root '.claude\skills'), (Join-Path $Root '.agents\skills'))) {
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($skill in Get-ChildItem -Directory $skills) {
        $target = Join-Path $dest $skill.Name
        if (Test-Path $target) { Remove-Item -Recurse -Force $target }
        Copy-Item -Recurse $skill.FullName $target
        Write-Output "installed $($skill.Name) -> $target"
    }
}
