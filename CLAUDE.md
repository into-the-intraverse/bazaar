# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Bazaar is a personal Claude Code plugin marketplace. It acts as a catalog that references plugin repos hosted on GitHub. No build system, no runtime — just `marketplace.json`, metadata, and small maintenance tools.

## Structure

- `.claude-plugin/marketplace.json` — the catalog; lists all plugins with their source repos
- `plugins/` — optional directory for inline plugins bundled directly in this repo
- `tools/sync_readme.py` — regenerates the README plugin table from the catalog
- `tools/validate_marketplace.py` — deep check: clones every source and verifies it is installable

## Adding a plugin

1. External repo: add an entry with `"source": {"source": "github", "repo": "owner/repo"}` (pin with `ref`/`sha` if needed). For a plugin living in a subdirectory of a repo, use `"source": {"source": "git-subdir", "url": "...", "path": "..."}`.
2. Repo without `.claude-plugin/plugin.json` (bare skills): add `"strict": false` and, if the skills aren't at a default location (`skills/` dir or root `SKILL.md`), point `"skills"` at the skill directories.
3. Inline: create `plugins/<name>/.claude-plugin/plugin.json` and `plugins/<name>/skills/<name>/SKILL.md`, then add a `"source": "./plugins/<name>"` entry

Then run `uv run python tools/validate_marketplace.py` to verify installability (clones all sources; needs network).

## Hooks

Git hooks live in `hooks/` (tracked) and are activated via `core.hooksPath`. The pre-commit hook runs `claude plugin validate` (offline schema check) and `tools/sync_readme.py` to regenerate the plugin table in README.md from marketplace.json and inline plugins.

After cloning, run: `git config core.hooksPath hooks`

## Key constraint

Each catalog entry must be installable: either the source repo has `.claude-plugin/plugin.json` (the `strict: true` default), or the entry sets `"strict": false` and its skills resolve — via explicit `"skills"` directory paths or default discovery (a `skills/` dir, else a root `SKILL.md` with `name` frontmatter). `tools/validate_marketplace.py` enforces this.
