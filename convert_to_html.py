"""Convert every .md in the prep-guide tree to a print-ready HTML file.

Usage: python convert_to_html.py
Output: writes <name>.html next to every <name>.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent

# Subjects that need right-to-left typography (Urdu / Arabic script).
RTL_SUBJECTS = {"urdu", "islamiyat"}

# CSS — shared by every page. Print-friendly A4 layout, exam-paper feel
# for model papers, clean reference look for study guides and answer keys.
CSS = r"""
:root {
    --ink: #1a1a1a;
    --muted: #555;
    --rule: #cfcfcf;
    --accent: #0b5394;
    --soft-bg: #f6f6f4;
}

* { box-sizing: border-box; }

html { font-size: 16px; }

body {
    margin: 0;
    padding: 2.5rem clamp(1rem, 5vw, 4rem);
    font-family: "Source Serif Pro", "Georgia", "Times New Roman", serif;
    color: var(--ink);
    background: #fdfdfb;
    line-height: 1.55;
    max-width: 980px;
    margin-left: auto;
    margin-right: auto;
}

body.rtl {
    direction: rtl;
    font-family: "Jameel Noori Nastaleeq", "Noto Nastaliq Urdu",
                 "Alvi Nastaleeq", "Urdu Typesetting",
                 "Arial Unicode MS", serif;
    font-size: 1.15rem;
    line-height: 2.1;
}

.crumb {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--rule);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
    font-size: 0.85rem;
    color: var(--muted);
    font-family: "Inter", "Segoe UI", system-ui, sans-serif;
}

.crumb a { color: var(--accent); text-decoration: none; }
.crumb a:hover { text-decoration: underline; }

h1, h2, h3, h4, h5 {
    font-family: "Inter", "Segoe UI", system-ui, sans-serif;
    color: var(--ink);
    line-height: 1.25;
    margin-top: 2rem;
    margin-bottom: 0.6rem;
}

body.rtl h1, body.rtl h2, body.rtl h3, body.rtl h4 {
    font-family: "Jameel Noori Nastaleeq", "Noto Nastaliq Urdu",
                 "Alvi Nastaleeq", "Arial Unicode MS", serif;
}

h1 { font-size: 2rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.4rem; }
h2 { font-size: 1.45rem; border-bottom: 1px solid var(--rule); padding-bottom: 0.3rem; }
h3 { font-size: 1.2rem; }
h4 { font-size: 1.05rem; color: var(--accent); }

p, ul, ol { margin: 0.6rem 0; }

ul, ol { padding-left: 1.6rem; }
body.rtl ul, body.rtl ol { padding-right: 1.6rem; padding-left: 0; }

li { margin: 0.3rem 0; }

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
    font-size: 0.95rem;
}

body.rtl table { font-size: 1.05rem; }

th, td {
    border: 1px solid var(--rule);
    padding: 0.55rem 0.7rem;
    text-align: left;
    vertical-align: top;
}

body.rtl th, body.rtl td { text-align: right; }

th {
    background: var(--soft-bg);
    font-weight: 600;
    font-family: "Inter", "Segoe UI", system-ui, sans-serif;
}

body.rtl th {
    font-family: "Jameel Noori Nastaleeq", "Noto Nastaliq Urdu",
                 "Alvi Nastaleeq", serif;
}

blockquote {
    border-left: 3px solid var(--accent);
    margin: 1rem 0;
    padding: 0.6rem 1rem;
    background: var(--soft-bg);
    color: var(--ink);
    font-style: italic;
}

body.rtl blockquote {
    border-left: none;
    border-right: 3px solid var(--accent);
}

code {
    background: var(--soft-bg);
    border: 1px solid var(--rule);
    border-radius: 3px;
    padding: 0.05rem 0.35rem;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 0.9em;
}

pre {
    background: var(--soft-bg);
    border: 1px solid var(--rule);
    border-radius: 4px;
    padding: 1rem;
    overflow-x: auto;
    line-height: 1.4;
}

pre code { background: none; border: none; padding: 0; }

hr {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 2rem 0;
}

a { color: var(--accent); }

/* Exam-paper specific look for model papers */
body.exam .crumb { border-bottom: 2px solid var(--ink); }
body.exam h1 { text-align: center; border-bottom: none; }
body.exam h1 + p { text-align: center; font-weight: 600; margin-top: -0.4rem; }

/* Cover sheet table for the exam header (Roll No, Time, Marks) */
body.exam table:first-of-type {
    border: 2px solid var(--ink);
    margin-bottom: 1.5rem;
}
body.exam table:first-of-type th,
body.exam table:first-of-type td {
    border: 1px solid var(--ink);
}

/* Print rules */
@media print {
    body {
        padding: 1cm 1.5cm;
        background: white;
        max-width: none;
    }
    .crumb { display: none; }
    h1 { page-break-before: avoid; }
    h2 { page-break-after: avoid; }
    table, blockquote, pre { page-break-inside: avoid; }
    body.exam h2 { page-break-before: auto; }
    a { color: var(--ink); text-decoration: none; }
}

@page {
    size: A4;
    margin: 1.5cm 1.7cm;
}
"""

# HTML page template.
TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}" dir="{dir}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style>
</head>
<body class="{body_class}">
<div class="crumb">
  <span>{crumb_left}</span>
  <span>{crumb_right}</span>
</div>
{content}
</body>
</html>
"""

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]

def first_h1(text: str) -> str:
    """Pull the first H1 from the markdown for the page <title>."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Document"

def rewrite_md_links(html: str) -> str:
    """Rewrite href="*.md" → href="*.html" so internal links work in HTML output."""
    return re.sub(r'href="([^"]+?)\.md(#[^"]*)?"', r'href="\1.html\2"', html)

def crumb_for(md_path: Path) -> tuple[str, str]:
    """Return (left, right) breadcrumb text for the page header."""
    rel = md_path.relative_to(ROOT)
    parts = list(rel.parts)
    if len(parts) == 1:
        # Root-level files (README, study-calendar)
        return ("11th Class Prep Guide", "BISE Abbottabad")
    subject = parts[0].title()
    # Link back up to README
    depth = len(parts) - 1
    up = "../" * depth
    left = f'<a href="{up}README.html">11th Class Prep Guide</a> &rsaquo; {subject}'
    right = "BISE Abbottabad &middot; FSc Pre-Engineering"
    return (left, right)

def body_class_for(md_path: Path) -> tuple[str, str, str]:
    """Return (css class, lang, dir) for the page."""
    rel = md_path.relative_to(ROOT)
    parts = list(rel.parts)
    classes = []
    lang = "en"
    direction = "ltr"
    if len(parts) > 1 and parts[0] in RTL_SUBJECTS:
        classes.append("rtl")
        lang = "ur"
        direction = "rtl"
    if md_path.stem.startswith("model-paper"):
        classes.append("exam")
    return (" ".join(classes), lang, direction)

def convert(md_path: Path) -> Path:
    text = md_path.read_text(encoding="utf-8")
    title = first_h1(text)
    html_body = markdown.markdown(text, extensions=MD_EXTENSIONS, output_format="html5")
    html_body = rewrite_md_links(html_body)
    body_class, lang, direction = body_class_for(md_path)
    crumb_left, crumb_right = crumb_for(md_path)
    page = TEMPLATE.format(
        lang=lang,
        dir=direction,
        title=title,
        css=CSS,
        body_class=body_class,
        crumb_left=crumb_left,
        crumb_right=crumb_right,
        content=html_body,
    )
    out_path = md_path.with_suffix(".html")
    out_path.write_text(page, encoding="utf-8")
    return out_path

def main() -> None:
    md_files = sorted(p for p in ROOT.rglob("*.md"))
    if not md_files:
        print("No .md files found.")
        return
    for md in md_files:
        rel = md.relative_to(ROOT)
        out = convert(md)
        print(f"  {rel}  ->  {out.relative_to(ROOT)}")
    print(f"\nDone: {len(md_files)} file(s) converted.")

if __name__ == "__main__":
    main()
