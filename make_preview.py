
"""Render README.md itself into a static HTML mock for both themes."""
import re, sys, os

md = open("README.md", encoding="utf-8").read()
md = re.sub(r"<!--.*?-->", "", md, flags=re.S)

def strip_sources(text, theme):
    text = re.sub(r"<source[^>]*>", "", text)
    def swap(m):
        src = m.group(1)
        if theme == "dark" and not src.endswith("-dark.svg"):
            src = src[:-4] + "-dark.svg"
        return 'src="%s"' % src
    return re.sub(r'src="([^"]+\.svg)"', swap, text)

CSS = """body{margin:0;background:%(bg)s;font-family:-apple-system,'Segoe UI',sans-serif;color:%(fg)s;}
.col{max-width:830px;margin:0 auto;padding:24px 0 48px;}
h2,h3{font-size:1.25em;font-weight:600;border-bottom:1px solid %(bd)s;padding-bottom:.3em;margin:26px 0 16px;}
img{max-width:100%%;vertical-align:middle;}
p{font-size:16px;line-height:1.6;margin:0 0 16px;}
blockquote{border-left:.25em solid %(bd)s;color:%(mu)s;margin:0 0 16px;padding:0 1em;}
table{border-collapse:collapse;width:100%%;font-size:14px;margin:0 0 16px;}
td,th{border:1px solid %(bd)s;padding:6px 10px;text-align:left;}
pre{background:#151b23;color:#e6edf3;font-family:ui-monospace,Menlo,monospace;font-size:13px;
    line-height:1.45;padding:16px;border-radius:6px;overflow:auto;margin:0 0 16px;}
a{color:%(link)s;}
sub{font-size:12px;color:%(mu)s;}
"""
THEME = {
    "light": dict(bg="#ffffff", fg="#1f2328", bd="#d0d7de", mu="#59636e", link="#0969da"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", bd="#30363d", mu="#9198a1", link="#4493f8"),
}

for theme in ("light", "dark"):
    body = strip_sources(md, theme)
    html = ("<!doctype html><html><head><meta charset='utf-8'><style>"
            + CSS % THEME[theme] + "</style></head><body><div class='col'>"
            + body + "</div></body></html>")
    out = "render-%s.html" % theme
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, len(html))
