#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
document_pipeline.py — the system's single-page document engine.

It renders my CV and other one-page documents: one content file in,
a design-frozen PDF out. The design never argues with the content.

Usage:
  python3.11 document_pipeline.py
      -> renders content.sample.json (included): document.html + document.pdf

  python3.11 document_pipeline.py --variant variants/X.json --out out/document_X.pdf
      -> deep-merges a variant over the core (dict = deep, list = replace)
         and renders a tailored PDF.

  --check: renders to a temp dir and reports page count without touching real output.

Inline mini-markup in content strings: **text** = emphasis span, <m>text</m> = muted span.
Safety: a document that overflows one page fails the build (exit 2) — an error, not a warning.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = HERE / "content.sample.json"


def find_chrome() -> str:
    """CHROME_PATH env var wins; otherwise try the usual locations per platform."""
    if os.environ.get("CHROME_PATH"):
        return os.environ["CHROME_PATH"]
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        *(shutil.which(n) or "" for n in ("google-chrome", "chromium", "chromium-browser")),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    sys.exit("Chrome/Chromium not found — set CHROME_PATH (see templates/env.example).")

# ============================ frozen design ============================
CSS = """
  @page { size: A4; margin: 15mm 17mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body {
    font-family: "Helvetica Neue", Arial, "Segoe UI", sans-serif;
    color: #1a1a1a;
    font-size: 10.5pt;
    line-height: 1.45;
    letter-spacing: 0.1px;
  }
  .name {
    font-size: 25pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: #16324f;
    line-height: 1;
  }
  .contact {
    margin-top: 7px;
    font-size: 9.4pt;
    color: #555;
    letter-spacing: 0.2px;
  }
  .summary {
    margin-top: 12px;
    font-size: 10.5pt;
    color: #262626;
    line-height: 1.5;
  }
  h2 {
    font-size: 9.6pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.6px;
    color: #16324f;
    border-bottom: 1.4px solid #c9d4df;
    padding-bottom: 3px;
    margin-top: 16px;
    margin-bottom: 7px;
  }
  .row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 12px;
  }
  .role { font-weight: 700; color: #1a1a1a; }
  .meta { font-weight: 400; color: #555; }
  .dates { font-size: 9.2pt; color: #555; white-space: nowrap; }
  .sub { font-size: 9.6pt; color: #555; margin-top: 1px; }
  ul { list-style: none; margin-top: 5px; }
  li {
    position: relative;
    padding-left: 14px;
    margin-bottom: 5px;
    color: #262626;
  }
  li::before {
    content: "";
    position: absolute;
    left: 0; top: 7px;
    width: 4px; height: 4px;
    border-radius: 50%;
    background: #3a6ea5;
  }
  .skills p { margin-bottom: 4px; }
  .skills .k { font-weight: 700; color: #16324f; }
  .award { font-weight: 600; color: #16324f; }
  .block { margin-bottom: 3px; }
  a { color: inherit; text-decoration: none; }
"""

SEP = "  ·  "  # contact-line separator


def esc(text: str) -> str:
    """HTML-escape, then restore only the allowed mini-markup."""
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r'<span class="award">\1</span>', t)
    t = t.replace("&lt;m&gt;", '<span class="meta">').replace("&lt;/m&gt;", "</span>")
    return t


def linkify(escaped: str, raw: str) -> str:
    """Wrap real links (github / email) in a clickable <a> — identical visuals, clickable PDF."""
    if raw.startswith("github.com/"):
        return f'<a href="https://{raw}">{escaped}</a>'
    if "@" in raw and " " not in raw:
        return f'<a href="mailto:{raw}">{escaped}</a>'
    return escaped


def deep_merge(base, over):
    """dict = deep merge; list/scalar = full replace; variant keys starting with _ are skipped."""
    for k, v in over.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def bullets_html(items) -> str:
    return "<ul>\n" + "\n".join(f"      <li>{esc(b)}</li>" for b in items) + "\n    </ul>"


def block_html(sec: dict) -> str:
    """Section with headline/dates and optional sub/bullets (Education/Project/Experience)."""
    parts = [
        '<div class="block">',
        '    <div class="row">',
        f'      <span class="role">{esc(sec["headline"])}</span>',
        f'      <span class="dates">{linkify(esc(sec["dates"]), sec["dates"])}</span>',
        "    </div>",
    ]
    if sec.get("sub"):
        parts.append(f'    <div class="sub">{esc(sec["sub"])}</div>')
    if sec.get("bullets"):
        parts.append("    " + bullets_html(sec["bullets"]))
    parts.append("  </div>")
    return "\n  ".join(parts)


def skills_html(sec: dict) -> str:
    lines = "\n".join(
        f'    <p><span class="k">{esc(line["label"])}:</span> {esc(line["text"])}</p>'
        for line in sec["lines"]
    )
    return f'<div class="skills">\n{lines}\n  </div>'


def section_html(key: str, sec: dict) -> str:
    if key == "skills":
        inner = skills_html(sec)
    elif "headline" in sec:
        inner = block_html(sec)
    else:  # bullets-only section
        inner = bullets_html(sec["bullets"])
    return f'  <h2>{esc(sec["heading"])}</h2>\n  {inner}'


def build_html(d: dict) -> str:
    contact_parts = list(d["header"]["contact"])
    for link_key in ("linkedin", "github"):
        v = d["header"].get(link_key)
        if v:
            contact_parts.append(v)
    contact = SEP.join(linkify(esc(p), p) for p in contact_parts)

    sections = "\n\n".join(section_html(k, d[k]) for k in d["sections_order"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>{CSS}</style>
</head>
<body>

  <div class="name">{esc(d["header"]["name"])}</div>
  <div class="contact">{contact}</div>

  <p class="summary">
    {esc(d["summary"])}
  </p>

{sections}

</body>
</html>
"""


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    pdf_path.unlink(missing_ok=True)  # never report a stale file as fresh output
    res = subprocess.run(
        [find_chrome(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_path}", f"file://{html_path.resolve()}"],
        capture_output=True, text=True, timeout=60,
    )
    if res.returncode != 0 or not pdf_path.exists():
        sys.exit(f"render failed: {res.stderr[-400:]}")


def page_count(pdf_path: Path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a single-page document from a content file")
    ap.add_argument("--core", default=str(CORE), help="core content file (default: content.sample.json)")
    ap.add_argument("--variant", help="variant JSON, deep-merged over the core")
    ap.add_argument("--out", help="output PDF path (default: document.pdf next to this script)")
    ap.add_argument("--html-out", help="output HTML path (default: next to the PDF)")
    ap.add_argument("--check", action="store_true", help="render to a temp dir, report only")
    ap.add_argument("--append", help="PDF to append after the document, when a workflow requires a single merged file")
    args = ap.parse_args()

    core_path = Path(args.core)
    if not core_path.exists():
        sys.exit(f"content file not found: {core_path} — try the included content.sample.json")
    data = json.loads(core_path.read_text(encoding="utf-8"))
    if args.variant:
        variant = json.loads(Path(args.variant).read_text(encoding="utf-8"))
        deep_merge(data, variant)

    if args.check:
        tmp = Path(tempfile.mkdtemp(prefix="cv-check-"))
        pdf_path, html_path = tmp / "check.pdf", tmp / "check.html"
    else:
        pdf_path = Path(args.out) if args.out else HERE / "document.pdf"
        html_path = Path(args.html_out) if args.html_out else pdf_path.with_suffix(".html")
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

    html_path.write_text(build_html(data), encoding="utf-8")
    render_pdf(html_path, pdf_path)

    doc_pages = page_count(pdf_path)
    if doc_pages is None:
        print("WARNING: pypdf missing — the one-page gate did NOT run (pip install pypdf).")
    elif doc_pages > 1:
        print(f"FAIL: the document overflowed to {doc_pages} pages — cut content, not design.")
        sys.exit(2)

    if args.append:  # merge an appendix after the document page
        from pypdf import PdfWriter
        w = PdfWriter()
        w.append(str(pdf_path))
        w.append(args.append)
        with open(pdf_path, "wb") as f:
            w.write(f)

    pages = page_count(pdf_path)
    tag = f"{pages} page(s)" if pages else "pages: unchecked (pypdf missing)"
    extra = " (document + appendix)" if args.append else ""
    print(f"OK: {pdf_path}  ({pdf_path.stat().st_size:,} bytes, {tag}{extra})")


if __name__ == "__main__":
    main()
