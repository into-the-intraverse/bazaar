"""Sync the Available plugins table in README.md from marketplace.json + inline plugins/."""

import json
import sys
from pathlib import Path


def collect_plugins(marketplace_path: str, repo_root: str) -> list[dict]:
    """Collect plugins from marketplace.json and inline plugins/ dirs."""
    plugins = []

    # From marketplace.json
    with open(marketplace_path) as f:
        data = json.load(f)
    for p in data.get("plugins", []):
        plugins.append({"name": p["name"], "description": p.get("description", "")})

    # From inline plugins/
    plugins_dir = Path(repo_root) / "plugins"
    if plugins_dir.is_dir():
        for plugin_json in sorted(plugins_dir.glob("*/.claude-plugin/plugin.json")):
            with open(plugin_json) as f:
                pdata = json.load(f)
            name = pdata.get("name", plugin_json.parent.parent.name)
            # Skip if already listed in marketplace.json
            if any(p["name"] == name for p in plugins):
                continue
            plugins.append({"name": name, "description": pdata.get("description", "")})

    plugins.sort(key=lambda p: p["name"])
    return plugins


def build_table(plugins: list[dict]) -> str:
    """Build markdown table."""
    lines = ["| Plugin | Description |", "|---|---|"]
    for p in plugins:
        lines.append(f"| `{p['name']}` | {p['description']} |")
    return "\n".join(lines)


def update_readme(readme_path: str, plugins: list[dict]) -> None:
    """Replace the plugin table between '## Available plugins' and the next '##'."""
    text = Path(readme_path).read_text()
    lines = text.split("\n")

    start = None
    end = None
    for i, line in enumerate(lines):
        if line.strip() == "## Available plugins":
            start = i
        elif start is not None and line.startswith("## ") and i > start:
            end = i
            break

    if start is None:
        return

    # Find table start (first non-blank line after heading)
    table_start = start + 1
    while table_start < len(lines) and lines[table_start].strip() == "":
        table_start += 1

    # Find table end (first blank line after table, or next heading)
    table_end = table_start
    while table_end < len(lines) and lines[table_end].strip() != "" and not lines[table_end].startswith("## "):
        table_end += 1

    # Consume trailing blank lines so we don't accumulate extras
    while table_end < len(lines) and lines[table_end].strip() == "":
        table_end += 1

    new_table = build_table(plugins)
    new_lines = lines[:table_start] + new_table.split("\n") + [""] + lines[table_end:]
    new_text = "\n".join(new_lines)

    if new_text != text:
        Path(readme_path).write_text(new_text)


if __name__ == "__main__":
    marketplace_path, readme_path, repo_root = sys.argv[1], sys.argv[2], sys.argv[3]
    plugins = collect_plugins(marketplace_path, repo_root)
    update_readme(readme_path, plugins)
