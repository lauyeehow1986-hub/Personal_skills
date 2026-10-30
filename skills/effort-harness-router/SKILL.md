---
name: effort-harness-router
description: Use when deciding which coding harness (Claude Code, Antigravity, Codex, Oh My Pi, Pi, Aider, Cursor, Cline), model tier, or reasoning effort level to use for a task, or when asked "which model/effort should I use", "is Opus overkill for this", or how to cut token cost and latency on a coding task.
---

# Effort & Harness Router

## Overview

Agent = Model + Harness + Reasoning Effort. Over-spec (Opus at max effort for a typo) wastes tokens and time; under-spec (Haiku at no effort for a Raft implementation) produces broken code. `jev_router.py` (bundled, stdlib-only, deterministic, no network) scores a task prompt and returns complexity, effort, harness, model and a ready-to-run command.

## When to Use

- User asks which harness, model, or thinking effort fits a task.
- Before delegating work to subagents: pick model/effort per task.
- User wants to minimise cost or latency on a batch of tasks.

Not for: choosing among non-coding tasks, or when the user already specified model and effort.

## How to Run

Run from this skill's directory (stdlib-only Python 3).

```bash
python3 scripts/jev_router.py "<task description>"                 # full report + cross-harness matrix
python3 scripts/jev_router.py "<task>" --harness claude_code       # single-harness answer
python3 scripts/jev_router.py "<task>" --profile legacy            # older model generation
python3 scripts/jev_router.py "<task>" --json                      # machine-readable
python3 scripts/jev_router.py "<task>" --quiet                     # command string only
git diff | python3 scripts/jev_router.py --harness claude_code     # prompt from stdin
```

Harness values: `antigravity claude_code codex grok oh_my_pi pi cursor windsurf aider cline`.

## Quick Reference

| Complexity (score) | Typical task | Effort (budget) | Claude Code model |
|---|---|---|---|
| trivial (≤0.25) | typos, formatting, rename | none→low (0–2k) | haiku-5.5 |
| routine (0.26–0.65) | CRUD endpoint, unit tests, isolated bug | low–medium (1k–8k) | sonnet-5.5 |
| complex (0.66–0.85) | multi-file refactor, races, cache invalidation | high (16k–32k) | sonnet-5.5 / opus-5.5 |
| frontier (≥0.86) | consensus, formal verification, compilers, greenfield architecture | max (64k+) | opus-5.5 |

Models with always-on adaptive thinking (Claude 5.5, Gemini 3.8) clamp `none` to `--effort low`.

Harness picks: Antigravity for huge context or multi-agent/visual work; Claude Code for terminal-centric loops; Codex for algorithmic/math; Oh My Pi for LSP/DAP debugging; Pi for light scripting with local models; Aider for strict git micro-commits; Cursor/Windsurf/Cline for in-IDE work.

## Responding to the User

1. Run the router on the user's task text (not a paraphrase).
2. Report: complexity + score, effort, primary harness/model, the command, and one alternative in another harness.
3. Surface the `destructive_risk` flag if raised (suggest confirmation/backup before running) and `large_context` (favour Antigravity or whole-repo indexing).
4. Treat the output as a heuristic starting point; if the user knows the task is harder or easier than its keywords suggest, adjust one tier and say so.

## Common Mistakes

- Routing a vague one-liner: keyword scoring needs the real task detail; ask for it or pass the issue text.
- Treating model names in the catalog as authoritative for the current environment: check availability before emitting a command.
- Using `--profile legacy` by default: only when the user lacks access to current models.

Source: github.com/lauyeehow1986-hub/effort_harness_router
