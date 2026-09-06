#!/usr/bin/env python3
"""Generate the editorial stats card (light + dark) from live GitHub data.

stdlib only — runs locally and inside the gen-stats workflow.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

USER = "Shinzo27"
API = f"https://api.github.com/users/{USER}"
REPOS = f"https://api.github.com/users/{USER}/repos?per_page=100&sort=pushed"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-stats-gen"})
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def count_commits() -> int | None:
    """Lifetime public commits via the commit search API (None on failure)."""
    try:
        data = fetch(
            f"https://api.github.com/search/commits?q=author:{USER}&per_page=1"
        )
        return int(data.get("total_count", 0))
    except Exception as e:
        print(f"commit count failed: {e}", file=sys.stderr)
        return None


def collect() -> dict:
    user = fetch(API)
    repos = fetch(REPOS)
    followers = user.get("followers", 0)
    public_repos = user.get("public_repos", len(repos))
    commits = count_commits()
    recent = sorted(
        (r for r in repos if r["name"] != USER),
        key=lambda r: r.get("pushed_at", ""),
        reverse=True,
    )[:3]
    return {
        "repos": public_repos,
        "commits": commits,
        "followers": followers,
        "recent": [(r["name"], (r.get("pushed_at", "") or "")[:10]) for r in recent],
    }


PALETTES = {
    "light": {
        "bg": "#FAFAF6", "ink": "#101010", "muted": "#6E6D66", "hair": "#E7E6DF",
        "accent": "#1D33D8", "mark_bg": "#1D33D8", "mark_fg": "#FAFAF6",
    },
    "dark": {
        "bg": "#0E0E0C", "ink": "#F2F1EA", "muted": "#8F8E83", "hair": "#232320",
        "accent": "#8B9CFF", "mark_bg": "#8B9CFF", "mark_fg": "#0E0E0C",
    },
}


def fmt(n: int) -> str:
    return f"{n:,}"


def render(d: dict, p: dict, generated: str) -> str:
    commits = fmt(d["commits"]) if d["commits"] is not None else "—"
    rows = "".join(
        f'<text x="612" y="{214 + i * 40}" font-family="Menlo,Consolas,monospace" '
        f'font-size="15" fill="{p["ink"]}">· {name}</text>'
        f'<text x="944" y="{214 + i * 40}" text-anchor="end" font-family="Georgia,serif" '
        f'font-size="16" font-style="italic" fill="{p["accent"]}">{date}</text>'
        for i, (name, date) in enumerate(d["recent"])
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420" fill="none">
  <rect width="1000" height="420" rx="10" fill="{p["bg"]}"/>
  <rect x="24" y="24" width="952" height="372" rx="6" fill="none" stroke="{p["hair"]}" stroke-width="1"/>

  <text x="56" y="76" font-family="Menlo,Consolas,monospace" font-size="12" letter-spacing="3" fill="{p["muted"]}">GITHUB — THE NUMBERS</text>
  <text x="944" y="76" text-anchor="end" font-family="Menlo,Consolas,monospace" font-size="12" fill="{p["muted"]}">generated {generated}</text>
  <rect x="56" y="94" width="888" height="1" fill="{p["hair"]}"/>

  <!-- big numbers -->
  <text x="56" y="192" font-family="Georgia,serif" font-size="64" fill="{p["ink"]}">{fmt(d["repos"])}</text>
  <text x="56" y="224" font-family="Menlo,Consolas,monospace" font-size="11" letter-spacing="2.5" fill="{p["muted"]}">REPOSITORIES</text>

  <text x="286" y="192" font-family="Georgia,serif" font-size="64" fill="{p["ink"]}">{commits}</text>
  <text x="286" y="224" font-family="Menlo,Consolas,monospace" font-size="11" letter-spacing="2.5" fill="{p["muted"]}">COMMITS · PUBLIC</text>

  <text x="486" y="192" font-family="Georgia,serif" font-size="64" fill="{p["ink"]}">{fmt(d["followers"])}</text>
  <text x="486" y="224" font-family="Menlo,Consolas,monospace" font-size="11" letter-spacing="2.5" fill="{p["muted"]}">FOLLOWERS</text>

  <!-- now shipping strip -->
  <text x="56" y="290" font-family="Menlo,Consolas,monospace" font-size="11" letter-spacing="2.5" fill="{p["accent"]}">NOW SHIPPING</text>
  <text x="56" y="318" font-family="Menlo,Consolas,monospace" font-size="15" fill="{p["ink"]}">intervue-ai <tspan fill="{p["muted"]}">·</tspan> nirvitta <tspan fill="{p["muted"]}">·</tspan> rag-platform <tspan fill="{p["muted"]}">·</tspan> rn-habit-tracker</text>

  <!-- recent activity -->
  <text x="612" y="164" font-family="Menlo,Consolas,monospace" font-size="11" letter-spacing="2.5" fill="{p["accent"]}">RECENTLY PUSHED</text>
  <rect x="612" y="176" width="332" height="1" fill="{p["hair"]}"/>
  {rows}

  <!-- footer -->
  <rect x="56" y="368" width="888" height="1" fill="{p["hair"]}"/>
  <text x="56" y="392" font-family="Menlo,Consolas,monospace" font-size="11" letter-spacing="1.5" fill="{p["muted"]}">github.com/{USER}</text>
  <rect x="918" y="376" width="26" height="26" rx="7" fill="{p["mark_bg"]}"/>
  <text x="931" y="394" text-anchor="middle" font-family="Georgia,serif" font-size="15" font-style="italic" fill="{p["mark_fg"]}">P.</text>
</svg>'''


def main() -> None:
    data = collect()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(OUT_DIR, exist_ok=True)
    for variant, palette in PALETTES.items():
        svg = render(data, palette, generated)
        path = os.path.abspath(os.path.join(OUT_DIR, f"stats-{variant}.svg"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {path}")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # keep the workflow green; keep last-good SVGs
        print(f"stats generation failed: {e}", file=sys.stderr)
        sys.exit(0)
