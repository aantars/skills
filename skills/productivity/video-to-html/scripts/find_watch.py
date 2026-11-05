#!/usr/bin/env python3
"""Locate the `watch` skill (bradautomates/claude-video) that video-to-html depends on.

Prints one JSON object:
  {"found": true, "skill_dir": "...", "watch_py": "...", "setup_py": "...", "source": "..."}
or
  {"found": false, "searched": [...], "install": {...}}

Exit code 0 when found, 2 when missing. Standard library only.
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

INSTALL = {
    "claude-code": [
        "claude plugin marketplace add bradautomates/claude-video",
        "claude plugin install watch@claude-video",
    ],
    "other-agents": ["npx skills@latest add bradautomates/claude-video -g --skill watch"],
    "docs": "https://github.com/bradautomates/claude-video#readme",
}


def version_key(path: str):
    """Sort plugin cache dirs like .../watch/0.3.10/... after .../watch/0.3.2/..."""
    m = re.search(r"[\\/]watch[\\/](\d+(?:\.\d+)*)[\\/]", path)
    if not m:
        return (0,)
    return tuple(int(p) for p in m.group(1).split("."))


def candidates():
    home = Path.home()
    env = os.environ.get("WATCH_SKILL_DIR")
    if env:
        yield "env:WATCH_SKILL_DIR", [env]
    # A glob with no hits yields the pattern itself, so the "searched" report still lists it.
    cache_pattern = str(home / ".claude/plugins/cache/*/watch/*/skills/watch")
    plugin_hits = sorted(glob.glob(cache_pattern), key=version_key, reverse=True)
    yield "claude-plugin-cache", plugin_hits or [cache_pattern]
    market_pattern = str(home / ".claude/plugins/marketplaces/*/skills/watch")
    yield "claude-plugin-marketplace", glob.glob(market_pattern) or [market_pattern]
    for label, base in (
        ("claude-user-skills", home / ".claude/skills/watch"),
        ("agents-user-skills", home / ".agents/skills/watch"),
        ("codex-user-skills", home / ".codex/skills/watch"),
        ("project-claude-skills", Path.cwd() / ".claude/skills/watch"),
        ("project-agents-skills", Path.cwd() / ".agents/skills/watch"),
    ):
        yield label, [str(base)]


def main() -> int:
    searched = []
    for label, dirs in candidates():
        for d in dirs:
            searched.append(d)
            watch_py = Path(d) / "scripts" / "watch.py"
            if watch_py.is_file():
                print(json.dumps({
                    "found": True,
                    "source": label,
                    "skill_dir": str(Path(d).resolve()),
                    "watch_py": str(watch_py.resolve()),
                    "setup_py": str((Path(d) / "scripts" / "setup.py").resolve()),
                }, indent=2))
                return 0
    print(json.dumps({"found": False, "searched": searched, "install": INSTALL}, indent=2))
    return 2


if __name__ == "__main__":
    sys.exit(main())
