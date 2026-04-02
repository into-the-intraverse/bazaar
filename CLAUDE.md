# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bazaar is a personal Claude Code plugin marketplace. It acts as a catalog that references plugin repos hosted on GitHub. No build system, no runtime — just `marketplace.json` and metadata.

## Structure

- `.claude-plugin/marketplace.json` — the catalog; lists all plugins with their source repos
- `plugins/` — optional directory for inline plugins bundled directly in this repo

## Adding a plugin

1. External repo: add an entry to `marketplace.json` with `"source": {"source": "github", "repo": "owner/repo"}`
2. Inline: create `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/skills/<name>/SKILL.md`, then add a `"source": "./plugins/<name>"` entry

## Hooks

Git hooks live in `hooks/` (tracked) and are activated via `core.hooksPath`. The pre-commit hook runs `tools/sync_readme.py` to regenerate the plugin table in README.md from marketplace.json and inline plugins.

After cloning, run: `git config core.hooksPath hooks`

## Key constraint

Each referenced plugin repo must have `.claude-plugin/plugin.json` and `skills/<name>/SKILL.md` to be a valid plugin.
