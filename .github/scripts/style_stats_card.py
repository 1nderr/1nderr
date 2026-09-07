#!/usr/bin/env python3
"""Bring the generated stats card in line with the languages card.

Two things the card cannot express through its own options:

  icons  it accepts a single icon_color, so each icon is given an inline fill
         here (inline style beats the card's `.icon` class rule)
  type   its body text is 600 14px against the languages card's 400 12px

Icons are matched by the label that follows them, so reordering or hiding
stats cannot mis-assign a color.

Usage: style_stats_card.py <svg> <dark|light>
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

# Must stay in step with the .lang rule in build_lang_card.py.
BODY_FONT = "400 12px 'Segoe UI', Ubuntu, Sans-Serif"


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


def restyle_text(svg):
    """Match the languages card's body type: 400 12px, same stack."""
    svg, n = re.subn(
        r"(\.stat\s*\{\s*)font:[^;]+;",
        lambda m: f"{m.group(1)}font: {BODY_FONT};",
        svg,
    )
    # the card shrinks .stat again for Firefox; 12px is already the target
    svg = re.sub(r"(\.stat\s*\{\s*)font-size:\s*[\d.]+px;", r"\g<1>font-size: 12px;", svg)
    return svg, n


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in PALETTES:
        sys.exit(f"usage: {sys.argv[0]} <svg> <{'|'.join(PALETTES)}>")
    path, variant = sys.argv[1], sys.argv[2]

    with open(path, encoding="utf-8") as f:
        svg = f.read()
    svg, colored = recolor(svg, PALETTES[variant])
    svg, restyled = restyle_text(svg)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{path}: colored {colored} icons, restyled {restyled} text rules ({variant})")


if __name__ == "__main__":
    main()
