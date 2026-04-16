# Bazaar

Personal Claude Code skill marketplace.

## Usage

```bash
/plugin marketplace add into-the-intraverse/bazaar
```

Then install individual skills:

```bash
/plugin install <skill-name>@bazaar
```

## Available plugins

| Plugin | Description |
|---|---|
| `burn` | Show Claude Code usage costs by model, project, and time period |
| `claude-perfectionist` | Audit and improve CLAUDE.md instruction harnesses |
| `playwright-cli` | Browser automation skills via Playwright CLI — token-efficient alternative to Playwright MCP |
| `youread` | Extract and analyze YouTube video content via subtitles |

## Adding plugins

Add inline plugins under `plugins/` or reference external repos in `.claude-plugin/marketplace.json`.
