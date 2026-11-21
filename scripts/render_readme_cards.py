#!/usr/bin/env python3
"""Render the GitHub profile README as animated SVG cards.

Every card is a self-contained SVG: no scripts, no external requests. Type is
embedded as a base64 WOFF2 subset so the cards look identical inside an <img>,
and the animation lives in one <style> block of CSS keyframes (with SMIL-free
counters), so `prefers-reduced-motion` can switch all of it off.

    python scripts/render_readme_cards.py            # light + dark
    THEME=dark python scripts/render_readme_cards.py # one theme
    STATIC=1 python scripts/render_readme_cards.py   # final frame only

Layout is measured, not guessed: every string is checked against the width of
its box using the real (subset) font metrics, and the run fails if it overflows
or two labels collide, so a bad data value can never ship a broken card.

Where to edit:
  P       the name, links, and copy that appear inside the cards
  TILES   the three linked tiles (label, counter, caption, destination)
  PROJECTS the three project cards under the toolkit
  THEMES  the palette — it mirrors --bg/--fg/--accent in the portfolio
The README markdown holds the layout: one <picture> per full-width card and
three `<a><img width="32.5%"></a>` per row, light and dark.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from datetime import date, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = os.path.join(ROOT, "cards")
FONT_DIR = os.path.join(ROOT, "fonts")
DATA = os.path.join(ROOT, "data", "contributions.json")

STATIC = os.environ.get("STATIC") == "1"
ONLY_THEME = os.environ.get("THEME")

# ── palette: mirrors app/globals.css from the portfolio ───────────────────────
THEMES = {
    # borders and empty cells carry the card on their own: GitHub's dark page is
    # #0d1117, so a near-black card needs a frame that reads (≈1.7:1) and an
    # empty grid cell that is visibly a cell, not page showing through.
    "light": dict(
        bg="#FAFAF6", ink="#101010", muted="#6E6D66", border="#DDDBD2",
        surface="#FFFFFF", accent="#1D33D8", on_accent="#FAFAF6",
        tile_ink_bg="#101010", tile_ink_fg="#FAFAF6",
        ramp=["#E3E0D6", "#B9C2F2", "#7E8DEA", "#4256E2", "#1D33D8"],
    ),
    "dark": dict(
        bg="#0E0E0C", ink="#F2F1EA", muted="#9A998D", border="#3B3B33",
        surface="#1B1B17", accent="#8B9CFF", on_accent="#0E0E0C",
        tile_ink_bg="#F2F1EA", tile_ink_fg="#0E0E0C",
        ramp=["#2E2E28", "#38428A", "#5566C8", "#7285F2", "#8B9CFF"],
    ),
}

# ── content ──────────────────────────────────────────────────────────────────
P = {
    "name1": "Pratham",
    "name2": "Patel",
    "email": "prathampatel5553@gmail.com",
    "site": "prathampatel.in",
    "site_url": "https://www.prathampatel.in",
    "github": "https://github.com/Shinzo27",
    "linkedin": "https://www.linkedin.com/in/prathamm27",
    "x": "https://x.com/Pratham68410619",
    "resume": "https://www.prathampatel.in/Pratham_Patel.pdf",
    "location": "Surat, Gujarat, India",
    "coords": "21.17°N 72.83°E",
}

TILES = [
    dict(
        file="tile-build", kind="accent", index="01", label="BUILD",
        count=2, caption=["products in", "production"], foot="NIRVITTA · INTERVUE-AI",
        href=P["site_url"] + "/#projects",
    ),
    dict(
        file="tile-craft", kind="paper", index="02", label="AI-NATIVE",
        count=4, caption=["steps: frame, delegate,", "review, ship"], foot="CURSOR · CLAUDE CODE · CODEX",
        href=P["site_url"] + "/#workflow",
    ),
    dict(
        file="tile-learn", kind="ink", index="03", label="LEARNING",
        count=None, caption=["MCP tool design, RAG", "retrieval and evals"],
        foot="AGENTS · MCP · EVALS",
        href=P["site_url"] + "/#now",
    ),
]

PROJECTS = [
    dict(
        file="proj-shiftora", tag="SAAS", year="2026", name="Shiftora",
        desc=["Auto-filled clinic rosters in 2s,", "attendance, swaps, RLS tenancy."],
        href=P["site_url"] + "/#projects",
    ),
    dict(
        file="proj-intervue", tag="AI SAAS", year="2026", name="Intervue AI",
        desc=["AI interviewer, permission-checked", "MCP tools, two-model scoring."],
        href=P["site_url"] + "/#projects",
    ),
    dict(
        file="proj-syncstream", tag="REALTIME", year="2024", name="SyncStream",
        desc=["Music rooms synced over Redis", "pub/sub and Socket.IO."],
        href=P["site_url"] + "/#projects",
    ),
]

# ── fonts ────────────────────────────────────────────────────────────────────
CHARSET = "".join(chr(c) for c in range(32, 127)) + "·—–→↗★▸°’“”…×"

FACES: dict[str, dict] = {}
_CACHE: dict[str, str] = {}
CSS_CACHE: dict[str, str] = {}


def _subset(src: str, family: str, text: str, weight: int | None = None,
            axes: dict | None = None) -> str:
    """Subset to the glyphs one card actually uses, as an embedded WOFF2."""
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    chars = "".join(sorted(set(text + " ")))
    key = f"{os.path.basename(src)}|{weight}|{axes}|{chars}"
    if key in _CACHE:
        return _CACHE[key]

    # recalcTimestamp=False keeps the embedded bytes identical between runs,
    # so the nightly Action only commits when the data actually changed.
    font = TTFont(src, recalcTimestamp=False)
    if axes:
        font = instantiateVariableFont(font, axes, inplace=True, updateFontNames=False)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga", "calt", "ccmp", "locl"]
    opts.name_IDs = [1, 2, 4, 6]
    opts.notdef_outline = True
    opts.desubroutinize = False
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)

    tmp = os.path.join(FONT_DIR, f".{abs(hash(key))}.woff2")
    font.flavor = "woff2"
    font.save(tmp)
    b64 = base64.b64encode(open(tmp, "rb").read()).decode()
    os.remove(tmp)
    _CACHE[key] = b64
    return b64


def _metrics(src: str, family: str, weight: int | None, axes: dict | None) -> None:
    """Load metrics from the full font once; measurement never needs the subset."""
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    font = TTFont(src, recalcTimestamp=False)
    if axes:
        font = instantiateVariableFont(font, axes, inplace=True, updateFontNames=False)
    FACES[family] = dict(weight=weight or 400, upem=font["head"].unitsPerEm,
                         cmap=font.getBestCmap(), widths={g: font["hmtx"][g][0]
                                                         for g in font["hmtx"].metrics})


SOURCES = {
    "serif": (os.path.join(FONT_DIR, "serif.ttf"), 400, None),
    "mono": (os.path.join(FONT_DIR, "mono.ttf"), 500, {"wght": 500}),
}


def load_fonts() -> None:
    for fam, (src, weight, axes) in SOURCES.items():
        _metrics(src, fam, weight, axes)


def font_css(text: str) -> str:
    chars = "".join(sorted(set(text + " ")))
    if chars in CSS_CACHE:
        return CSS_CACHE[chars]
    out = []
    for fam, (src, weight, axes) in SOURCES.items():
        b64 = _subset(src, fam, chars, weight, axes)
        out.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:%d;font-display:block;"
            "src:url(data:font/woff2;base64,%s) format('woff2')}"
            % (fam, weight, b64)
        )
    CSS_CACHE[chars] = "".join(out)
    return CSS_CACHE[chars]


def _glyph_advance(fam: str, ch: str) -> float:
    meta = FACES[fam]
    name = meta["cmap"].get(ord(ch))
    if name is None:
        return meta["widths"].get("space", 600)
    return meta["widths"].get(name, 600)


def _md(iso: str) -> str:
    """'%b %-d' is glibc-only; build the short label portably."""
    dt = datetime.strptime(iso, "%Y-%m-%d")
    return f"{dt:%b} {dt.day}".upper()


def measure(text: str, fam: str, size: float, tracking: float = 0.0) -> float:
    """Advance width in px, including letter-spacing applied after each glyph."""
    meta = FACES[fam]
    units = sum(_glyph_advance(fam, c) for c in text)
    return units / meta["upem"] * size + tracking * max(0, len(text) - 1)


def wrap(text: str, fam: str, size: float, maxw: float, tracking: float = 0.0) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if measure(trial, fam, size, tracking) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


OVERFLOWS: list[str] = []
OVERLAPS: list[str] = []


def fits(text: str, fam: str, size: float, maxw: float, tracking: float = 0.0, where: str = "") -> float:
    w = measure(text, fam, size, tracking)
    if w > maxw:
        OVERFLOWS.append(f"{where}: '{text}' {w:.1f}px > {maxw:.1f}px")
    return w


# ── svg helpers ──────────────────────────────────────────────────────────────
def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


class Svg:
    def __init__(self, w: int, h: int, t: dict):
        self.w, self.h, self.t = w, h, t
        self.body: list[str] = []
        self.defs: list[str] = []
        self.extra_css: list[str] = []
        self.boxes: list[tuple[float, float, float, float, str]] = []
        self.texts: list[str] = []

    # -- drawing
    def rect(self, x, y, w, h, fill="none", rx=0, stroke=None, sw=1, cls="", style="", extra=""):
        s = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"'
        if rx:
            s += f' rx="{rx}"'
        s += f' fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw}"'
        if cls:
            s += f' class="{cls}"'
        if style:
            s += f' style="{style}"'
        if extra:
            s += " " + extra
        self.body.append(s + "/>")

    def line(self, x1, y1, x2, y2, stroke, sw=1, cls="", style="", extra=""):
        s = (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
             f'stroke="{stroke}" stroke-width="{sw}"')
        if cls:
            s += f' class="{cls}"'
        if style:
            s += f' style="{style}"'
        if extra:
            s += " " + extra
        self.body.append(s + "/>")

    def text(self, x, y, s, fam, size, fill, *, tracking=0.0, weight=None, anchor="start",
             cls="", style="", extra="", maxw=None, where="text"):
        if maxw is not None:
            fits(s, fam, size, maxw, tracking, where)
        self.texts.append(s)
        wpx = measure(s, fam, size, tracking)
        bx = x - (wpx if anchor == "end" else wpx / 2 if anchor == "middle" else 0)
        self.boxes.append((bx, y - size * 0.74, wpx, size * 0.94, s))
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        tr = f' letter-spacing="{tracking:.3f}"' if tracking else ""
        w = f' font-weight="{weight}"' if weight else ""
        c = f' class="{cls}"' if cls else ""
        st = f' style="{style}"' if style else ""
        ex = (" " + extra) if extra else ""
        self.body.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
            f'fill="{fill}"{a}{tr}{w}{c}{st}{ex}>{esc(s)}</text>'
        )
        return measure(s, fam, size, tracking)

    def raw(self, s: str):
        self.body.append(s)

    def track(self, text: str):
        """Register glyphs that are emitted via raw() so they get embedded."""
        self.texts.append(text)

    def add_def(self, s: str):
        self.defs.append(s)

    def css(self, s: str):
        self.extra_css.append(s)

    def check(self, name: str) -> None:
        """Two pieces of text on one card must not sit on top of each other."""
        for i in range(len(self.boxes)):
            for j in range(i + 1, len(self.boxes)):
                ax, ay, aw, ah, at = self.boxes[i]
                bx, by, bw, bh, bt = self.boxes[j]
                ox = min(ax + aw, bx + bw) - max(ax, bx)
                oy = min(ay + ah, by + bh) - max(ay, by)
                if ox > 1.5 and oy > 1.5:
                    OVERLAPS.append(f"{name}: '{at}' x '{bt}' ({ox:.1f}x{oy:.1f}px)")

    def render(self, name: str, title: str) -> str:
        t = self.t
        style_blocks = "" if STATIC else BASE_CSS
        extra = "".join(self.extra_css)
        defs = "".join(self.defs)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{esc(title)}">\n'
            f"<title>{esc(title)}</title>\n"
            f"<style>{font_css(''.join(self.texts))}{style_blocks}{extra}</style>\n"
            f"<defs>{defs}</defs>\n"
            f'<rect width="{self.w}" height="{self.h}" rx="8" fill="{t["bg"]}"/>\n'
            f'<rect x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="8" '
            f'fill="none" stroke="{t["border"]}"/>\n'
            + "\n".join(self.body) + "\n</svg>\n"
        )


BASE_CSS = """
text{transform-box:fill-box;}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes riseSm{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{0%{opacity:0;transform:scale(.82)}60%{opacity:1;transform:scale(1.04)}100%{opacity:1;transform:scale(1)}}
@keyframes draw{from{stroke-dashoffset:var(--len)}to{stroke-dashoffset:0}}
@keyframes sweep{0%{transform:translateX(-260px)}55%,100%{transform:translateX(760px)}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes swing{0%{opacity:0;transform:translateY(22px) rotate(-3.5deg)}62%{opacity:1;transform:translateY(-4px) rotate(1.1deg)}86%{transform:translateY(1px) rotate(-.3deg)}100%{opacity:1;transform:translateY(0) rotate(0)}}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.28;transform:scale(.72)}}
@keyframes ring{0%{opacity:.55;transform:scale(.35)}70%{opacity:0;transform:scale(1.5)}100%{opacity:0;transform:scale(1.5)}}
@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(3.5px)}}
@keyframes count{from{transform:translateY(0)}to{transform:translateY(var(--roll))}}
@keyframes cellIn{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}
.rise{animation:rise .78s cubic-bezier(.22,.68,.32,1) both}
.riseSm{animation:riseSm .6s cubic-bezier(.22,.68,.32,1) both}
.fade{animation:fade .7s ease both}
.pop{animation:pop .68s cubic-bezier(.2,.8,.3,1) both;transform-origin:center}
.cell{transform-origin:center}
.grow{transform-origin:bottom;transform-box:fill-box}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""

# ── cards ────────────────────────────────────────────────────────────────────
# Cards are drawn at the width GitHub actually renders them: the markdown
# column is 815–1012px, and three cards at 33.33% are 270–337px. So type is
# sized against ~860 / ~270 and arrives close to 1:1 instead of being shrunk
# into illegibility.
#
# One spacing token: PAD top/left/right, 24 below the last baseline. One mono
# size for micro-labels (9.5), one for section heads (10.5).
W = 860
PAD = 34
BOTTOM = 24
TILE_W, TILE_H, GUTTER = 276, 218, 6
REPO_W, REPO_H = 276, 130
MONO_SM, MONO = 9.5, 10.5


def card_hero(t: dict, d: dict) -> Svg:
    s = Svg(W, 348, t)
    NAME = 96
    left_w = 430

    s.raw(
        f'<g class="fade" style="animation-delay:.05s">'
        f'<circle cx="{PAD + 4}" cy="42" r="3.4" fill="{t["accent"]}"/>'
        f'<circle cx="{PAD + 4}" cy="42" r="3.4" fill="{t["accent"]}" opacity=".35" '
        f'style="transform-origin:center;animation:pulse 2.6s ease-in-out 1.4s infinite"/>'
        f"</g>"
    )
    s.text(PAD + 15, 46, "SURAT, GUJARAT · IST · OPEN TO AI-NATIVE ROLES", "mono", MONO,
           t["muted"], tracking=1.6, cls="fade", style="animation-delay:.15s",
           maxw=left_w, where="hero/eyebrow")

    # the name rises one line at a time; a blue band sweeps the surname
    name_w = measure(P["name1"], "serif", NAME, -1.2)
    s.text(PAD - 3, 144, P["name1"], "serif", NAME, t["ink"], tracking=-1.2,
           cls="rise", style="animation-delay:.22s", maxw=left_w + 40, where="hero/name1")
    s.add_def(
        f'<clipPath id="clipname"><text x="{PAD - 3}" y="240" font-family="serif" '
        f'font-size="{NAME}" letter-spacing="-1.2">{P["name2"]}</text></clipPath>'
        f'<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{t["accent"]}" stop-opacity="0"/>'
        f'<stop offset=".42" stop-color="{t["accent"]}" stop-opacity=".55"/>'
        f'<stop offset=".58" stop-color="{t["accent"]}" stop-opacity=".95"/>'
        f'<stop offset="1" stop-color="{t["accent"]}" stop-opacity="0"/></linearGradient>'
    )
    s.raw(
        f'<g class="rise" style="animation-delay:.38s">'
        f'<text x="{PAD - 3}" y="240" font-family="serif" font-size="{NAME}" '
        f'letter-spacing="-1.2" fill="{t["ink"]}">{P["name2"]}</text></g>'
    )
    s.raw(
        f'<g clip-path="url(#clipname)">'
        f'<rect x="{PAD - 240}" y="152" width="220" height="118" fill="url(#shine)" '
        f'style="animation:sweep 5.6s cubic-bezier(.5,0,.3,1) 2.2s infinite"/></g>'
    )

    # the rule is the width of the name, so it measures something
    s.line(PAD, 270, PAD + name_w, 270, t["ink"], 1.4, cls="draw",
           style=f"--len:{name_w:.0f};animation-delay:.7s",
           extra=f'stroke-dasharray="{name_w:.0f}"')
    s.text(PAD, 300, "AI-native full-stack developer.", "serif", 23, t["ink"],
           cls="riseSm", style="animation-delay:.8s", maxw=left_w, where="hero/tagline")
    s.text(PAD, 320, "SPEC → DELEGATE → REVIEW → SHIP", "mono", MONO_SM, t["muted"],
           tracking=1.5, cls="riseSm", style="animation-delay:.92s",
           maxw=left_w, where="hero/flow")

    # colophon: top aligned to the eyebrow's cap height, bottom to the flow line
    px, py, pw, ph = 500, 34, W - PAD - 500, 286
    s.rect(px, py, pw, ph, fill=t["surface"], rx=6, stroke=t["border"], sw=1,
           cls="fade", style="animation-delay:.5s")
    ix, iw = px + 24, pw - 48
    s.text(ix, 46, "COLOPHON", "mono", MONO, t["muted"], tracking=2.2,
           cls="fade", style="animation-delay:.62s")
    s.text(ix, py + 52, "Full-stack developer,", "serif", 19, t["ink"],
           cls="riseSm", style="animation-delay:.7s", maxw=iw, where="hero/col1")
    s.text(ix, py + 76, "backend lead.", "serif", 19, t["ink"],
           cls="riseSm", style="animation-delay:.76s", maxw=iw, where="hero/col2")
    for i, y in enumerate((132, 224)):
        s.line(ix, py + y, ix + iw, py + y, t["border"], 1, cls="draw",
               style=f"--len:{iw};animation-delay:{.85 + i * .1:.2f}s",
               extra=f'stroke-dasharray="{iw}"')
    y = py + 126
    for txt in ("PATOLIYA INFOTECH · SINCE JUN 2025", "MSC CS & IT · JAIN UNIVERSITY",
                "REMOTE-FRIENDLY · 30-DAY NOTICE"):
        s.text(ix, y, txt, "mono", MONO_SM, t["muted"], tracking=1.15,
               cls="fade", style="animation-delay:.95s", maxw=iw, where="hero/colophon")
        y += 21
    s.text(ix, py + 214, f'{d["total"]} CONTRIBUTIONS / YR', "mono", MONO_SM, t["muted"],
           tracking=1.1, cls="fade", style="animation-delay:1.0s", maxw=iw,
           where="hero/total")
    s.text(ix, py + 262, P["site"] + " ↗", "mono", MONO, t["accent"], tracking=1.2,
           cls="riseSm", style="animation-delay:1.1s", maxw=iw, where="hero/site")
    return s


def card_graph(t: dict, d: dict) -> Svg:
    days: dict[str, int] = d["days"]
    keys = sorted(days)
    s = Svg(W, 248, t)

    s.text(PAD, 40, "CONTRIBUTIONS · LAST 12 MONTHS", "mono", MONO, t["muted"],
           tracking=2.0, cls="fade", style="animation-delay:.1s", maxw=420, where="graph/head")

    cell, gap = 10.8, 4.14
    pitch = cell + gap
    cols = 53
    first = datetime.strptime(keys[0], "%Y-%m-%d").toordinal()
    grid_x, grid_y = PAD, 58

    buckets: dict[tuple[int, int], int] = {}
    for k in keys:
        dt = datetime.strptime(k, "%Y-%m-%d")
        buckets[(min((dt.toordinal() - first) // 7, cols - 1), dt.weekday())] = days[k]

    maxv = max(days.values()) or 1
    for (col, row), v in sorted(buckets.items()):
        lvl = 0 if v == 0 else min(4, 1 + int((v / maxv) ** 0.45 * 3.4))
        delay = 0.18 + col * 0.011 + row * 0.004
        s.raw(
            f'<rect x="{grid_x + col * pitch:.1f}" y="{grid_y + row * pitch:.1f}" '
            f'width="{cell}" height="{cell}" rx="2.2" fill="{t["ramp"][lvl]}" '
            f'class="cell" style="animation:cellIn .42s ease-out {delay:.3f}s both"/>'
        )

    # legend drawn at the same scale as the grid it explains
    lx = W - PAD - 5 * pitch + gap - 46
    s.text(lx - 10, 40, "LESS", "mono", MONO_SM, t["muted"], tracking=1.3, anchor="end",
           cls="fade", style="animation-delay:.9s")
    for i in range(5):
        s.raw(
            f'<rect x="{lx + i * pitch:.1f}" y="31" width="{cell}" height="{cell}" '
            f'rx="2.2" fill="{t["ramp"][i]}" class="fade" '
            f'style="animation-delay:{.9 + i * .05:.2f}s"/>'
        )
    s.text(lx + 5 * pitch - gap + 4, 40, "MORE", "mono", MONO_SM, t["muted"], tracking=1.3,
           cls="fade", style="animation-delay:1.2s")

    # four stats on one baseline, spread across the full column
    y = 204
    step = (W - 2 * PAD) / 4
    stats = [
        (f'{d["total"]}', "CONTRIBUTIONS"),
        (f'{d["active_days"]}', "ACTIVE DAYS"),
        (f'{d["longest"]}', "DAY STREAK"),
        (f'{d["busiest_count"]}', "BEST DAY · " + _md(d["busiest_day"])),
    ]
    for i, (val, label) in enumerate(stats):
        s.text(PAD + i * step, y, val, "serif", 30, t["ink"], cls="riseSm",
               style=f"animation-delay:{1.05 + i * .08:.2f}s")
        s.text(PAD + i * step, y + 17, label, "mono", MONO_SM, t["muted"], tracking=1.4,
               cls="fade", style=f"animation-delay:{1.15 + i * .08:.2f}s")
    return s


def card_activity(t: dict, d: dict) -> Svg:
    months = d["months"][-12:]
    s = Svg(W, 247, t)
    s.text(PAD, 40, "BY MONTH", "mono", MONO, t["muted"], tracking=2.0,
           cls="fade", style="animation-delay:.1s")
    best = max(months, key=lambda m: m["value"])
    s.text(W - PAD, 40, f"BEST · {best['label'].upper()} · {best['value']}", "mono", MONO,
           t["muted"], tracking=2.0, anchor="end", cls="fade", style="animation-delay:.1s")

    bx0, bw, bgap = PAD, 28, 15.8
    pitch = bw + bgap
    baseline, maxh = 200, 118
    top_v = best["value"] or 1
    for i, m in enumerate(months):
        h = max(2.5, m["value"] / top_v * maxh)
        x = bx0 + i * pitch
        best_here = m["month"] == best["month"]
        delay = 0.3 + i * 0.055
        # the rect is already its true height: with motion off (or reduced) the
        # chart still reads correctly, the animation only grows it into place
        s.raw(
            f'<rect x="{x:.1f}" y="{baseline - h:.1f}" width="{bw}" height="{h:.1f}" '
            f'rx="2" fill="{t["accent"] if best_here else t["border"]}" class="grow" '
            f'style="animation:grow .62s cubic-bezier(.2,.75,.3,1) {delay:.3f}s both"/>'
        )
        s.text(x + bw / 2, baseline + 20, m["label"], "mono", MONO_SM,
               t["ink"] if best_here else t["muted"], tracking=.8, anchor="middle",
               cls="fade", style=f"animation-delay:{delay + .1:.2f}s")
        if m["value"]:
            s.text(x + bw / 2, baseline - h - 8, str(m["value"]), "mono", MONO_SM,
                   t["accent"] if best_here else t["muted"], tracking=.5, anchor="middle",
                   cls="pop", style=f"animation-delay:{delay + .35:.2f}s")

    s.line(PAD, baseline, bx0 + len(months) * pitch - bgap, baseline, t["ink"], 1.2,
           cls="draw", style=f"--len:{len(months) * pitch};animation-delay:.2s",
           extra=f'stroke-dasharray="{len(months) * pitch}"')

    px = 620
    s.line(px - 34, 40, px - 34, 218, t["border"], 1, cls="draw",
           style="--len:178;animation-delay:.5s", extra='stroke-dasharray="178"')
    rows = [
        (f'{d["current"]:02d}', "CURRENT STREAK", f'{d["longest"]} DAYS BEST'),
        (f'{d["longest"]:02d}', "LONGEST STREAK",
         datetime.strptime(d["longest_end"], "%Y-%m-%d").strftime("%b %Y").upper()),
        (f'{d["busiest_count"]:02d}', "BUSIEST DAY",
         datetime.strptime(d["busiest_day"], "%Y-%m-%d").strftime("%A").upper()),
    ]
    for i, (val, label, sub) in enumerate(rows):
        top = 54 + i * 62
        s.text(px, top + 26, val, "serif", 30, t["ink"], cls="riseSm",
               style=f"animation-delay:{.55 + i * .12:.2f}s")
        s.text(px + 44, top + 11, label, "mono", MONO_SM, t["muted"], tracking=1.5,
               cls="fade", style=f"animation-delay:{.6 + i * .12:.2f}s")
        s.text(px + 44, top + 27, sub, "mono", MONO_SM, t["accent"], tracking=1.15,
               cls="fade", style=f"animation-delay:{.66 + i * .12:.2f}s")
        if i < 2:
            # the divider sits midway between the two blocks it separates
            dy = top + 51
            s.line(px, dy, W - PAD, dy, t["border"], 1, cls="draw",
                   style=f"--len:{W - PAD - px};animation-delay:{.7 + i * .12:.2f}s",
                   extra=f'stroke-dasharray="{W - PAD - px}"')
    return s


def card_tile(t: dict, tile: dict) -> Svg:
    w, h = TILE_W, TILE_H
    s = Svg(w, h, t)
    cw = w - GUTTER  # the card, with a transparent gutter so 33.33% rows align
    kind = tile["kind"]
    if kind == "accent":
        bg, fg, sub, arrow = t["accent"], t["on_accent"], "rgba(250,250,246,.62)", t["on_accent"]
    elif kind == "ink":
        bg, fg, arrow = t["tile_ink_bg"], t["tile_ink_fg"], t["tile_ink_fg"]
        sub = "rgba(250,250,246,.55)" if t["bg"] != "#0E0E0C" else "rgba(14,14,12,.55)"
    else:
        bg, fg, sub, arrow = t["surface"], t["ink"], t["muted"], t["accent"]

    s.body.clear()
    s.raw(f'<rect width="{w}" height="{h}" rx="10" fill="{t["bg"]}"/>')
    s.raw(f'<rect width="{cw}" height="{h}" rx="10" fill="{bg}"/>')
    if kind != "accent":
        s.raw(f'<rect x="0.5" y="0.5" width="{cw - 1}" height="{h - 1}" rx="10" fill="none" '
              f'stroke="{t["border"]}"/>')

    pad = 20
    s.raw(f'<g style="animation:swing .85s cubic-bezier(.2,.9,.3,1) {tile["delay"]:.2f}s both;'
          f'transform-origin:center 82%">')
    s.text(pad, 30, f'{tile["index"]} / {tile["label"]}', "mono", MONO_SM, sub, tracking=1.7,
           maxw=cw - pad * 2, where=f'tile/{tile["file"]}/label')

    if tile["count"] is not None:
        n, roll, base = tile["count"], 56, 107
        s.add_def(f'<clipPath id="clip-{tile["file"]}"><rect x="{pad - 6}" y="{base - 41}" '
                  f'width="{cw - pad * 2}" height="{roll}"/></clipPath>')
        stack = "".join(
            f'<text x="{pad}" y="{base + roll * i}" font-family="serif" font-size="54" '
            f'fill="{fg}">{i:02d}</text>' for i in range(n + 1)
        )
        s.track("".join(f"{i:02d}" for i in range(n + 1)))
        # the stack already sits on its last frame, so with motion off the
        # number still reads 02 / 04 instead of 00
        s.raw(f'<g clip-path="url(#clip-{tile["file"]})"><g style="--roll:-{roll * n}px;'
              f'transform:translateY(-{roll * n}px);animation:count .95s '
              f'steps({n + 1}, jump-none) {tile["delay"] + .5:.2f}s both">'
              f'{stack}</g></g>')
    else:
        s.raw(f'<circle cx="{pad + 7}" cy="87" r="6.6" fill="none" stroke="{t["accent"]}" '
              f'stroke-width="1.3" style="transform-origin:center;'
              f'animation:ring 2.8s ease-out {tile["delay"] + 1:.2f}s infinite"/>')
        s.raw(f'<circle cx="{pad + 7}" cy="87" r="3" fill="{t["accent"]}" '
              f'style="transform-origin:center;animation:pulse 2.8s ease-in-out '
              f'{tile["delay"] + 1:.2f}s infinite"/>')
        s.text(pad + 21, 91, "IN PROGRESS", "mono", MONO, fg, tracking=1.6,
               maxw=cw - pad * 2 - 21, where=f'tile/{tile["file"]}/prog')

    for i, line_ in enumerate(tile["caption"]):
        s.text(pad, 152 + i * 18, line_, "serif", 16, fg,
               maxw=cw - pad * 2, where=f'tile/{tile["file"]}/cap')
    s.text(pad, 194, tile["foot"], "mono", MONO_SM, sub, tracking=1.0,
           maxw=cw - pad * 2 - 22, where=f'tile/{tile["file"]}/foot')

    s.raw(f'<g style="transform-origin:center;animation:nudge 2.8s ease-in-out '
          f'{tile["delay"] + 1.3:.2f}s infinite">'
          f'<path d="M{cw - pad - 12} 186 h10 m-4 -4 l4 4 l-4 4" fill="none" '
          f'stroke="{arrow}" stroke-width="1.4" stroke-linecap="round"/></g>')
    s.raw("</g>")
    return s


def card_repo(t: dict, repo: dict) -> Svg:
    """A project card: tag + year, name, two mono lines, arrow."""
    w, h = REPO_W, REPO_H
    s = Svg(w, h, t)
    cw = w - GUTTER
    s.body.clear()
    s.raw(f'<rect width="{w}" height="{h}" rx="10" fill="{t["bg"]}"/>')
    s.raw(f'<rect width="{cw}" height="{h}" rx="10" fill="{t["surface"]}"/>')
    s.raw(f'<rect x="0.5" y="0.5" width="{cw - 1}" height="{h - 1}" rx="10" fill="none" '
          f'stroke="{t["border"]}"/>')
    pad = 20
    s.raw(f'<g class="riseSm" style="animation-delay:{repo["delay"]:.2f}s">')
    lw = s.text(pad, 28, repo["tag"], "mono", MONO_SM, t["muted"], tracking=1.4)
    s.text(pad + lw + 11, 28, "·", "mono", MONO_SM, t["border"], tracking=1.4)
    s.text(pad + lw + 17, 28, repo["year"], "mono", MONO_SM, t["muted"], tracking=1.4)
    s.text(pad, 62, repo["name"], "serif", 24, t["ink"], tracking=-.3,
           maxw=cw - pad * 2 - 18, where=f'repo/{repo["file"]}')
    for i, line_ in enumerate(repo["desc"]):
        s.text(pad, 88 + i * 16, line_, "mono", MONO_SM, t["muted"],
               maxw=cw - pad * 2 - 16, where=f'repo/{repo["file"]}/desc')
    s.raw(f'<path d="M{cw - pad - 13} {h - 16} h9 m-3.5 -3.5 l3.5 3.5 l-3.5 3.5" fill="none" '
          f'stroke="{t["accent"]}" stroke-width="1.4" stroke-linecap="round"/>')
    s.raw("</g>")
    return s


# ── main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    if not os.path.exists(DATA):
        print("missing data/contributions.json — run scripts/fetch_contributions.py", file=sys.stderr)
        return 1
    d = json.load(open(DATA, encoding="utf-8"))
    load_fonts()
    os.makedirs(CARDS, exist_ok=True)

    themes = [ONLY_THEME] if ONLY_THEME else ["light", "dark"]
    written = 0
    for name in themes:
        t = dict(THEMES[name])
        suffix = "" if name == "light" else "-dark"

        hero = card_hero(t, d)
        graph = card_graph(t, d)
        act = card_activity(t, d)
        for c, n in ((hero, "hero"), (graph, "graph"), (act, "activity")):
            c.check(f"{n}{suffix}")

        payload = {
            f"hero{suffix}.svg": (hero.render("hero", "Pratham Patel — AI-native full-stack developer"), 0),
            f"graph{suffix}.svg": (graph.render("graph", "Contribution graph"), .10),
            f"activity{suffix}.svg": (act.render("activity", "Contributions by month"), .20),
        }
        for i, tile in enumerate(TILES):
            tile = dict(tile)
            # tiles animate after the full-width cards above them
            tile["delay"] = 1.35 + i * .16
            s = card_tile(dict(t), tile)
            s.check(f'{tile["file"]}{suffix}')
            payload[f'{tile["file"]}{suffix}.svg'] = (
                s.render(tile["file"], f'{tile["label"]} — {tile["caption"][0]}'), .55)
        for i, proj in enumerate(PROJECTS):
            proj = dict(proj)
            proj["delay"] = 2.15 + i * .12
            s = card_repo(dict(t), proj)
            s.check(f'{proj["file"]}{suffix}')
            payload[f'{proj["file"]}{suffix}.svg'] = (
                s.render(proj["file"], f'{proj["name"]} — {proj["desc"][0]}'), .55)

        for fname, (svg, _) in payload.items():
            with open(os.path.join(CARDS, fname), "w", encoding="utf-8") as f:
                f.write(svg)
            written += 1

    if OVERLAPS:
        print("TEXT COLLISIONS:", file=sys.stderr)
        for o in OVERLAPS[:40]:
            print("  " + o, file=sys.stderr)
        return 3

    if OVERFLOWS:
        print("TEXT OVERFLOW:", file=sys.stderr)
        for o in OVERFLOWS[:40]:
            print("  " + o, file=sys.stderr)
        return 2

    print(f"rendered {written} cards into cards/")
    print(f"  total {d['total']} · active {d['active_days']} · streak {d['current']} "
          f"· best day {d['busiest_day']} ({d['busiest_count']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
