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
| `database-skills` | PlanetScale database skills — MySQL, Postgres, Vitess, and Neki schema design, query tuning, replication, and operations |
| `excalidraw-diagram` | Create Excalidraw diagram JSON files that make visual arguments — workflows, architectures, concepts |
| `googleworkspace` | Google Workspace CLI skills — Calendar, Drive, Docs, Sheets, Chat, Gmail, Classroom, Admin Reports (95 skills) |
| `impeccable` | Design fluency for frontend development — polish, audit, critique commands with curated anti-pattern detection |
| `loki-mode` | Multi-agent autonomous startup system — takes a spec (PRD, GitHub issue, OpenAPI doc) to deployed product with minimal human intervention |
| `playwright-cli` | Browser automation skills via Playwright CLI — token-efficient alternative to Playwright MCP |
| `product-manager-skills` | Product manager skill — diagnoses SaaS metrics, critiques PRDs, plans roadmaps, runs discovery, coaches PM career transitions |
| `remotion` | Remotion video production skill — code-first React animations, captions, 3D, charts, and rendering |
| `shannon` | Autonomous AI pentester for web apps and APIs — white-box security assessments with real exploit execution |
| `skill-seekers` | Transform 17 source types (docs, GitHub, PDFs, videos, Jupyter, Confluence, Notion, Slack) into AI-ready skills and RAG knowledge |
| `ui-ux-pro-max` | UI/UX design intelligence — styles, palettes, typography, component patterns for building polished interfaces |
| `valyu-search` | Valyu API toolkit — real-time search across web, academic, financial, healthcare, news, and more, with AI-synthesized answers and deep research reports |
| `youread` | Extract and analyze YouTube video content via subtitles |

## Adding plugins

Add inline plugins under `plugins/` or reference external repos in `.claude-plugin/marketplace.json`.
