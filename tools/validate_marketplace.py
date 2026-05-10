"""Validate that every plugin entry in marketplace.json is installable.

Checks:
1. JSON parses and has required top-level fields.
2. Each plugin entry has `name`, `description`, `source`.
3. For github / git-subdir sources: clones the source ref and verifies that
   either a `.claude-plugin/plugin.json` exists, or `strict: false` is set
   along with `skills` paths that all resolve to a SKILL.md (file or folder
   containing one) with valid frontmatter.
4. For local `./` sources: the path exists and contains
   `.claude-plugin/plugin.json` or a SKILL.md.

Usage: uv run python tools/validate_marketplace.py [marketplace_path] [repo_root]
Exits non-zero on any failure. Cleans up clone cache by default; pass
--keep-cache to inspect.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


CACHE = Path(tempfile.gettempdir()) / "bazaar-validate-cache"


def fail(msg: str) -> None:
    print(f"  ❌ {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def parse_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from a SKILL.md. Returns dict or None."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body = text[4:end]
    out = {}
    for line in body.splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def clone_source(source: dict, name: str) -> Path | None:
    """Clone the source into the cache. Returns the plugin root path."""
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / name
    if target.exists():
        shutil.rmtree(target)

    src_type = source.get("source")
    if src_type == "github":
        repo = source["repo"]
        url = f"https://github.com/{repo}.git"
        ref = source.get("ref")
        sha = source.get("sha")
        cmd = ["git", "clone", "--depth", "1"]
        if ref:
            cmd += ["--branch", ref]
        cmd += [url, str(target)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"clone failed: {r.stderr.strip()}")
            return None
        if sha:
            # Fetch the specific SHA (--depth 1 may not include it).
            subprocess.run(
                ["git", "-C", str(target), "fetch", "--depth", "1", "origin", sha],
                capture_output=True, text=True,
            )
            r = subprocess.run(
                ["git", "-C", str(target), "checkout", sha],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                fail(f"checkout {sha[:8]} failed: {r.stderr.strip()}")
                return None
        return target
    elif src_type == "git-subdir":
        url = source["url"]
        path = source["path"]
        ref = source.get("ref")
        cmd = ["git", "clone", "--depth", "1"]
        if ref:
            cmd += ["--branch", ref]
        cmd += [url, str(target)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"clone failed: {r.stderr.strip()}")
            return None
        sub = target / path
        if not sub.is_dir():
            fail(f"git-subdir path '{path}' not found in repo")
            return None
        return sub
    else:
        fail(f"unsupported source type: {src_type}")
        return None


def validate_skill_path(plugin_root: Path, skill_path: str) -> bool:
    """Verify a declared skill path resolves to a SKILL.md or skills folder."""
    rel = skill_path.lstrip("./")
    target = plugin_root / rel
    if not target.exists():
        fail(f"skill path not found: {skill_path}")
        return False
    if target.is_file():
        if target.name != "SKILL.md":
            fail(f"skill file must be SKILL.md, got: {target.name}")
            return False
        meta = parse_frontmatter(target.read_text(encoding="utf-8", errors="replace"))
        if not meta or "name" not in meta:
            fail(f"{skill_path}: SKILL.md missing 'name' frontmatter")
            return False
        ok(f"{skill_path} → skill '{meta['name']}'")
        return True
    # Directory: either a single skill folder (contains SKILL.md) or a parent.
    direct = target / "SKILL.md"
    if direct.is_file():
        meta = parse_frontmatter(direct.read_text(encoding="utf-8", errors="replace"))
        if not meta or "name" not in meta:
            fail(f"{skill_path}: SKILL.md missing 'name' frontmatter")
            return False
        ok(f"{skill_path}/ → skill '{meta['name']}'")
        return True
    # Parent of skill folders.
    nested = sorted(target.glob("*/SKILL.md"))
    if not nested:
        fail(f"{skill_path}: no SKILL.md found at this path or one level deep")
        return False
    bad = 0
    for s in nested:
        meta = parse_frontmatter(s.read_text(encoding="utf-8", errors="replace"))
        if not meta or "name" not in meta:
            fail(f"{s.relative_to(plugin_root)}: missing 'name' frontmatter")
            bad += 1
    if bad:
        return False
    ok(f"{skill_path}/ → {len(nested)} skills")
    return True


def validate_plugin(plugin: dict, repo_root: Path) -> list[str]:
    """Return list of error messages; empty if valid."""
    errors = []
    name = plugin.get("name", "<unnamed>")
    print(f"\n→ {name}")
    for field in ("name", "description", "source"):
        if field not in plugin:
            errors.append(f"{name}: missing required field '{field}'")
            fail(f"missing required field '{field}'")
    if errors:
        return errors

    source = plugin["source"]
    strict = plugin.get("strict", True)
    declared_skills = plugin.get("skills", [])

    # Local source.
    if isinstance(source, str):
        local = (repo_root / source).resolve()
        if not local.is_dir():
            errors.append(f"{name}: local source dir not found: {source}")
            fail(f"local source dir not found: {source}")
            return errors
        manifest = local / ".claude-plugin" / "plugin.json"
        if manifest.is_file():
            ok(f"local plugin.json present at {source}/.claude-plugin/")
        else:
            errors.append(f"{name}: local source missing .claude-plugin/plugin.json")
            fail("local source missing .claude-plugin/plugin.json")
        return errors

    # Remote source: clone and inspect.
    plugin_root = clone_source(source, name)
    if plugin_root is None:
        errors.append(f"{name}: source clone/checkout failed")
        return errors

    manifest = plugin_root / ".claude-plugin" / "plugin.json"
    has_manifest = manifest.is_file()

    if strict:
        if not has_manifest:
            errors.append(f"{name}: strict mode but no .claude-plugin/plugin.json in source")
            fail("strict mode but no plugin.json in source — set strict:false or fix upstream")
        else:
            try:
                json.loads(manifest.read_text(encoding="utf-8"))
                ok("upstream plugin.json present and valid JSON")
            except json.JSONDecodeError as e:
                errors.append(f"{name}: upstream plugin.json invalid JSON: {e}")
                fail(f"upstream plugin.json invalid JSON: {e}")
    else:
        if has_manifest:
            warn("strict:false but upstream has plugin.json — Claude Code reports this as a conflict")
        if not declared_skills:
            errors.append(f"{name}: strict:false requires explicit 'skills' paths")
            fail("strict:false requires explicit 'skills' paths")
        else:
            for sp in declared_skills:
                if not validate_skill_path(plugin_root, sp):
                    errors.append(f"{name}: skill path invalid: {sp}")

    return errors


def main(argv: list[str]) -> int:
    keep = "--keep-cache" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    market_path = Path(args[0]) if args else Path(".claude-plugin/marketplace.json")
    repo_root = Path(args[1]) if len(args) > 1 else Path(".")

    print(f"Validating {market_path}")
    try:
        data = json.loads(market_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"❌ cannot load marketplace: {e}")
        return 1

    for field in ("name", "owner", "plugins"):
        if field not in data:
            print(f"❌ marketplace missing top-level '{field}'")
            return 1

    all_errors = []
    seen_names = set()
    for plugin in data["plugins"]:
        n = plugin.get("name")
        if n in seen_names:
            all_errors.append(f"duplicate plugin name: {n}")
            print(f"\n❌ duplicate plugin name: {n}")
            continue
        seen_names.add(n)
        all_errors.extend(validate_plugin(plugin, repo_root))

    print()
    if all_errors:
        print(f"❌ FAILED: {len(all_errors)} error(s)")
        for e in all_errors:
            print(f"   - {e}")
        if not keep:
            shutil.rmtree(CACHE, ignore_errors=True)
        return 1
    print(f"✅ all {len(data['plugins'])} plugins valid")
    if not keep:
        shutil.rmtree(CACHE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
