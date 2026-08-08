# Bazaar

Personal Claude Code plugin marketplace.

## Usage

```bash
/plugin marketplace add into-the-intraverse/bazaar
```

Then install individual plugins:

```bash
/plugin install <plugin-name>@bazaar
```

## Available plugins

| Plugin | Description |
|---|---|
| `atomic-wiki` | Ingest -> atoms -> compile -> wiki -> query pipeline with automated lint maintenance |
| `claude-perfectionist` | Audit and improve Claude Code instruction harnesses — CLAUDE.md, rules, hooks, skills, settings, MCP config |
| `context7` | Upstash Context7 — pull version-specific docs and code examples from source repositories into LLM context |
| `database-skills` | PlanetScale database skills — MySQL, Postgres, Vitess, and Neki schema design, query tuning, replication, and operations |
| `googleworkspace` | Google Workspace CLI skills — Calendar, Drive, Docs, Sheets, Chat, Gmail, Classroom, Admin Reports (95 skills) |
| `grill` | Idea interrogation that ends in a document — grill-style interview with one question at a time, decisions recorded as they land, final ADR/design doc for the knowledge base |
| `impeccable` | Design fluency for frontend development — polish, audit, critique commands with curated anti-pattern detection |
| `loki-mode` | Multi-agent autonomous startup system — takes a spec (PRD, GitHub issue, OpenAPI doc) to deployed product with minimal human intervention |
| `playwright-cli` | Browser automation skills via Playwright CLI — token-efficient alternative to Playwright MCP |
| `product-manager-skills` | Product manager skill — diagnoses SaaS metrics, critiques PRDs, plans roadmaps, runs discovery, coaches PM career transitions |
| `remotion` | Remotion video production skills — code-first React animations, captions, 3D, charts, and rendering |
| `retell` | Recall quiz that ends in atoms — extract a source into atoms and check the source holds up, interview the user on what they remember without revealing the atoms, then rewrite them in the user's own voice |
| `ui-ux-pro-max` | UI/UX design intelligence — styles, palettes, typography, component patterns for building polished interfaces |
| `valyu-search` | Valyu API toolkit — real-time search across web, academic, financial, healthcare, news, and more, with AI-synthesized answers and deep research reports |
| `youread` | Extract YouTube content — subtitles plus on-screen slides, figures, and paper citations — into Markdown source notes for a wiki |

## Adding plugins

Add inline plugins under `plugins/` or reference external repos in `.claude-plugin/marketplace.json`.
