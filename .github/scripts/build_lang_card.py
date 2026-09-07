#!/usr/bin/env python3
"""Build the "Most Used Languages" card from real lines of code.

Clones every public, non-fork repo owned by the user, counts lines with scc
(code only -- blanks and comments are not counted), and renders an SVG card.

Env:
  GITHUB_OWNER  account to scan (required)
  GITHUB_TOKEN  token for the REST API and for cloning private repos (optional)
  INCLUDE_PRIVATE  "1" to count private repos too; needs a PAT with repo scope
  DRY_RUN       "1" to list repos and stop, without cloning
  SCC_BIN       path to the scc binary (default: scc on PATH)
  OUT           output path (default: profile/top-langs.svg)
  REPO_LIMIT    only scan the first N repos, for local testing (optional)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request

API = "https://api.github.com"
COLORS_URL = "https://raw.githubusercontent.com/ozh/github-colors/master/colors.json"

# File types that are configuration, markup or data rather than something you
# would say you write. Matched case-insensitively against scc's language names.
NOT_A_LANGUAGE = {
    "autoconf", "batch", "bazel", "cmake", "csv", "dockerfile", "dockerignore",
    "docker ignore", "editorconfig", "gitignore", "godot resource",
    "godot scene", "gradle",
    "ini", "json", "jsonl", "license", "m4", "macromedia exponential map",
    "makefile", "markdown", "meson", "module-definition", "msbuild", "nix",
    "org", "patch", "plain text", "properties", "protocol buffers", "readme",
    "restructuredtext", "svg", "text", "toml", "xml", "yaml", "yml",
}

# Repos whose contents are mostly vendored third-party source. behavior-tree-mario
# carries the IDSIA Mario AI Benchmark framework under src/ch/idsia, which is
# ~12k of its ~16k Java lines.
EXCLUDE_REPOS = {
    "behavior-tree-mario",
}

EXCLUDE_DIRS = [
    ".git", "node_modules", "vendor", "third_party", "dist", "build", "out",
    "target", ".venv", "venv", "site-packages", "bower_components", "addons",
    ".godot", ".import", "generated", "gen", "migrations",
]

TOP_N = 8
WIDTH = 300
FONT = "'Segoe UI', Ubuntu, Sans-Serif"

# One SVG cannot follow the viewer's theme, so a variant is rendered for each
# and the README picks between them with prefers-color-scheme. Colors are
# GitHub's own default text and link colors for that theme.
VARIANTS = {
    "dark": {"text": "#ffffff", "title": "#4493f8"},
    "light": {"text": "#1f2328", "title": "#0969da"},
}


def api(path):
    req = urllib.request.Request(f"{API}{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def list_repos(owner):
    # /user/repos sees private repos, but only with a user PAT; the repo-scoped
    # GITHUB_TOKEN can only use the public /users/<owner>/repos listing.
    private = os.environ.get("INCLUDE_PRIVATE") == "1"
    path = ("/user/repos?affiliation=owner&visibility=all" if private
            else f"/users/{owner}/repos?type=owner")
    repos, page = [], 1
    while True:
        batch = api(f"{path}&per_page=100&page={page}")
        if not batch:
            break
        repos += batch
        page += 1
    repos = [r for r in repos if r["owner"]["login"].lower() == owner.lower()]
    return [
        r for r in repos
        if not r["fork"] and not r["archived"] and r["size"] > 0
        and r["name"] not in EXCLUDE_REPOS
    ]


def clone_all(repos, dest):
    token = os.environ.get("GITHUB_TOKEN")
    cloned = 0
    for r in repos:
        target = os.path.join(dest, r["name"])
        url = r["clone_url"]
        if r["private"] and token:
            url = url.replace("https://", f"https://x-access-token:{token}@")
        cmd = ["git", "clone", "--depth", "1", "--single-branch", "--quiet",
               url, target]
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            cloned += 1
        else:
            print(f"  skipped {r['name']} (clone failed)", file=sys.stderr)
    return cloned


def count_lines(root):
    scc = os.environ.get("SCC_BIN", "scc")
    cmd = [scc, "--format", "json", "--no-complexity"]
    for d in EXCLUDE_DIRS:
        cmd += ["--exclude-dir", d]
    cmd.append(root)
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    totals = {}
    for entry in json.loads(out):
        name = entry["Name"]
        # scc splits headers from their language ("C++ Header"); fold them back in
        if name.endswith(" Header"):
            name = name[: -len(" Header")]
        if name.lower() in NOT_A_LANGUAGE:
            continue
        totals[name] = totals.get(name, 0) + entry["Code"]
    return {k: v for k, v in totals.items() if v > 0}


def language_colors():
    try:
        with urllib.request.urlopen(COLORS_URL, timeout=60) as r:
            raw = json.load(r)
        return {k.lower(): (v.get("color") or "#858585") for k, v in raw.items()}
    except Exception as exc:  # a missing palette should not fail the build
        print(f"  color lookup failed ({exc}), falling back to gray", file=sys.stderr)
        return {}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(langs, colors, variant):
    """langs: list of (name, lines), already sorted and truncated."""
    text_color = VARIANTS[variant]["text"]
    title_color = VARIANTS[variant]["title"]
    total = sum(n for _, n in langs)
    rows = (len(langs) + 1) // 2
    height = 78 + rows * 22

    bar, x = [], 25.0
    for name, lines in langs:
        w = 250.0 * lines / total
        color = colors.get(name.lower(), "#858585")
        bar.append(f'<rect x="{x:.2f}" y="45" width="{w:.2f}" height="8" fill="{color}"/>')
        x += w

    items = []
    for i, (name, lines) in enumerate(langs):
        col, row = i % 2, i // 2
        cx, cy = 25 + col * 140, 78 + row * 22
        color = colors.get(name.lower(), "#858585")
        pct = 100.0 * lines / total
        items.append(
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>'
            f'<text x="{cx + 17}" y="{cy}" class="lang">{esc(name)}</text>'
            f'<text x="{cx + 130}" y="{cy}" class="lang pct">{pct:.1f}%</text>'
        )

    return f"""<svg width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" xmlns="http://www.w3.org/2000/svg">
  <style>
    .title {{ font: 600 18px {FONT}; fill: {title_color} }}
    .lang {{ font: 400 12px {FONT}; fill: {text_color} }}
    .pct {{ text-anchor: end }}
    /* the stats card shrinks its header on Firefox; match it */
    @supports(-moz-appearance: auto) {{ .title {{ font-size: 15.5px }} }}
  </style>
  <text x="25" y="32" class="title">Most Used Languages</text>
  <g clip-path="url(#bar)">
    {chr(10).join("    " + b for b in bar).strip()}
  </g>
  <clipPath id="bar"><rect x="25" y="45" width="250" height="8" rx="4"/></clipPath>
  {chr(10).join("  " + i for i in items).strip()}
</svg>
"""


def main():
    owner = os.environ.get("GITHUB_OWNER")
    if not owner:
        sys.exit("GITHUB_OWNER is required")
    out = os.environ.get("OUT", "profile/top-langs.svg")

    repos = list_repos(owner)
    limit = os.environ.get("REPO_LIMIT")
    if limit:
        repos = repos[: int(limit)]
    n_private = sum(1 for r in repos if r["private"])
    print(f"scanning {len(repos)} repos ({n_private} private)")
    if os.environ.get("DRY_RUN") == "1":
        return

    work = tempfile.mkdtemp(prefix="langcard-")
    try:
        cloned = clone_all(repos, work)
        print(f"cloned {cloned}")
        totals = count_lines(work)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    for name, lines in ranked[:15]:
        print(f"  {name:<16}{lines:>9,} lines")

    top = ranked[:TOP_N]
    if not top:
        sys.exit("no languages counted")

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    palette = language_colors()
    base, ext = os.path.splitext(out)
    for variant in VARIANTS:
        path = out if variant == "dark" else f"{base}-{variant}{ext}"
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(top, palette, variant))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
