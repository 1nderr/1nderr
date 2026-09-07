#!/usr/bin/env python3
"""Give each stat icon its own color.

The stats card only accepts a single icon_color, so the generated SVG is
rewritten here: each icon gets an inline fill, which beats the card's
`.icon { fill: ... }` rule. Icons are matched by the label that follows them,
so reordering or hiding stats cannot mis-assign a color.

Usage: color_stat_icons.py <svg> <dark|light>
"""

import re
import sys

# GitHub's own palettes, so the colors read as the meaning they carry there:
# stars gold, commits contribution-green, PRs merged-purple, issues red.
PALETTES = {
    "dark": {
        "stars": "#e3b341", "commits": "#3fb950", "prs": "#a371f7",
        "issues": "#f85149", "contributed": "#4493f8",
    },
    "light": {
        "stars": "#bf8700", "commits": "#1a7f37", "prs": "#8250df",
        "issues": "#cf222e", "contributed": "#0969da",
    },
}

# Matched against the stat label that follows each icon, in order.
LABEL_KEYS = [
    ("star", "stars"),
    ("commit", "commits"),
    ("pr", "prs"),
    ("issue", "issues"),
    ("contributed", "contributed"),
]

ICON_TAG = '<svg data-testid="icon"'


def key_for(label):
    low = label.lower()
    for needle, key in LABEL_KEYS:
        if needle in low:
            return key
    return None


def recolor(svg, palette):
    chunks = svg.split(ICON_TAG)
    out, colored = [chunks[0]], 0
    for chunk in chunks[1:]:
        label = re.search(r'class="stat[^"]*"[^>]*>([^<]+)<', chunk)
        key = key_for(label.group(1)) if label else None
        if key:
            # drop any fill this script added on a previous run, then set ours
            chunk = re.sub(r'^ style="fill:#[0-9a-fA-F]{6}"', "", chunk)
            chunk = f' style="fill:{palette[key]}"' + chunk
            colored += 1
        out.append(chunk)
    return ICON_TAG.join(out), colored


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in PALETTES:
        sys.exit(f"usage: {sys.argv[0]} <svg> <{'|'.join(PALETTES)}>")
    path, variant = sys.argv[1], sys.argv[2]

    with open(path, encoding="utf-8") as f:
        svg = f.read()
    svg, colored = recolor(svg, PALETTES[variant])
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{path}: colored {colored} icons ({variant})")


if __name__ == "__main__":
    main()
