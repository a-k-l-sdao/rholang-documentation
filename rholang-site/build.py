#!/usr/bin/env python3
"""Convert rholang-guide markdown files into static HTML pages with sidebar navigation."""

import re
import html
import os

GUIDE_DIR = os.path.join(os.path.dirname(__file__), "..", "rholang-guide")
OUT_DIR = os.path.dirname(__file__)

PAGES = [
    ("README.md", "index.html", "Introduction"),
    ("01-language-basics.md", "01-language-basics.html", "Language Basics"),
    ("02-contracts-and-patterns.md", "02-contracts-and-patterns.html", "Contracts & Patterns"),
    ("03-system-contracts.md", "03-system-contracts.html", "System Contracts"),
    ("04-deploys-and-registry.md", "04-deploys-and-registry.html", "Deploys & Registry"),
    ("05-security-patterns.md", "05-security-patterns.html", "Security Patterns"),
    ("06-standard-library.md", "06-standard-library.html", "Standard Library"),
    ("07-examples.md", "07-examples.html", "Examples"),
]

def md_to_html(md: str) -> str:
    """Minimal markdown to HTML converter for our specific docs."""
    lines = md.split("\n")
    out = []
    in_code = False
    code_lang = ""
    code_buf = []
    in_table = False
    table_buf = []

    def flush_table():
        nonlocal in_table, table_buf
        if not table_buf:
            return ""
        rows = table_buf
        table_buf = []
        in_table = False
        # first row = header, second row = separator, rest = body
        h = "<div class=\"table-wrap\"><table>\n<thead><tr>"
        cols = [c.strip() for c in rows[0].strip("|").split("|")]
        for c in cols:
            h += f"<th>{inline(c)}</th>"
        h += "</tr></thead>\n<tbody>\n"
        for row in rows[2:]:
            cells = [c.strip() for c in row.strip("|").split("|")]
            h += "<tr>"
            for c in cells:
                h += f"<td>{inline(c)}</td>"
            h += "</tr>\n"
        h += "</tbody></table></div>"
        return h

    def inline(text: str) -> str:
        """Convert inline markdown."""
        # code spans (do first to avoid conflicts)
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        # bold+italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        # bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code fences
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line.strip()[3:].strip()
                code_buf = []
                i += 1
                continue
            else:
                lang_class = f' class="language-{code_lang}"' if code_lang else ""
                escaped = html.escape("\n".join(code_buf))
                out.append(f'<pre><code{lang_class}>{escaped}</code></pre>')
                in_code = False
                code_lang = ""
                i += 1
                continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        # Tables
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
                table_buf = []
            table_buf.append(line)
            i += 1
            continue
        elif in_table:
            out.append(flush_table())

        stripped = line.strip()

        # Empty line
        if not stripped:
            i += 1
            continue

        # Headers
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            level = len(m.group(1))
            text = m.group(2)
            slug = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
            out.append(f'<h{level} id="{slug}">{inline(text)}</h{level}>')
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^---+\s*$', stripped):
            out.append("<hr>")
            i += 1
            continue

        # Unordered list
        if re.match(r'^[-*]\s', stripped):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*]\s', lines[i]):
                item_text = re.sub(r'^\s*[-*]\s+', '', lines[i])
                items.append(f"<li>{inline(item_text)}</li>")
                i += 1
            out.append("<ul>" + "\n".join(items) + "</ul>")
            continue

        # Ordered list
        if re.match(r'^\d+\.\s', stripped):
            items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s', lines[i]):
                item_text = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                items.append(f"<li>{inline(item_text)}</li>")
                i += 1
            out.append("<ol>" + "\n".join(items) + "</ol>")
            continue

        # Paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].strip().startswith("```") and not lines[i].strip().startswith("|"):
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            out.append(f"<p>{inline(' '.join(para_lines))}</p>")
            continue

        i += 1

    if in_table:
        out.append(flush_table())

    return "\n".join(out)


def build_sidebar(current_html: str) -> str:
    items = []
    for _, html_file, title in PAGES:
        active = ' class="active"' if html_file == current_html else ""
        items.append(f'<a href="{html_file}"{active}>{title}</a>')
    return "\n".join(items)


def build_page(md_file: str, html_file: str, title: str) -> str:
    md_path = os.path.join(GUIDE_DIR, md_file)
    with open(md_path, "r") as f:
        md_content = f.read()

    body = md_to_html(md_content)

    # Rewrite .md links to .html links
    for src_md, dst_html, _ in PAGES:
        body = body.replace(f'href="./{src_md}"', f'href="{dst_html}"')
        body = body.replace(f'href="{src_md}"', f'href="{dst_html}"')

    sidebar = build_sidebar(html_file)

    # Find prev/next
    idx = next(i for i, p in enumerate(PAGES) if p[1] == html_file)
    prev_link = ""
    next_link = ""
    if idx > 0:
        prev_link = f'<a href="{PAGES[idx-1][1]}">&larr; {PAGES[idx-1][2]}</a>'
    if idx < len(PAGES) - 1:
        next_link = f'<a href="{PAGES[idx+1][1]}">{PAGES[idx+1][2]} &rarr;</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - Rholang Developer Guide</title>
<style>
:root {{
  --bg: #1a1b26;
  --bg-sidebar: #16161e;
  --bg-code: #12121a;
  --text: #c0caf5;
  --text-dim: #565f89;
  --text-bright: #e0e6ff;
  --accent: #7aa2f7;
  --accent-hover: #89b4fa;
  --border: #292e42;
  --h1: #bb9af7;
  --h2: #7dcfff;
  --h3: #73daca;
  --str: #9ece6a;
  --kw: #bb9af7;
  --comment: #565f89;
  --num: #ff9e64;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  display: flex;
  min-height: 100vh;
}}
nav {{
  width: 260px;
  min-width: 260px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  padding: 24px 0;
  position: fixed;
  top: 0;
  bottom: 0;
  overflow-y: auto;
}}
nav .logo {{
  padding: 0 20px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
}}
nav .logo h2 {{
  color: var(--h1);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.3px;
}}
nav .logo p {{
  color: var(--text-dim);
  font-size: 12px;
  margin-top: 4px;
}}
nav a {{
  display: block;
  padding: 8px 20px;
  color: var(--text-dim);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.15s;
  border-left: 3px solid transparent;
}}
nav a:hover {{
  color: var(--text);
  background: rgba(122, 162, 247, 0.06);
}}
nav a.active {{
  color: var(--accent);
  background: rgba(122, 162, 247, 0.1);
  border-left-color: var(--accent);
  font-weight: 600;
}}
main {{
  margin-left: 260px;
  flex: 1;
  max-width: 860px;
  padding: 48px 56px 80px;
}}
h1 {{
  color: var(--h1);
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 24px;
  letter-spacing: -0.5px;
}}
h2 {{
  color: var(--h2);
  font-size: 22px;
  font-weight: 600;
  margin-top: 48px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}}
h3 {{
  color: var(--h3);
  font-size: 17px;
  font-weight: 600;
  margin-top: 32px;
  margin-bottom: 12px;
}}
h4 {{ color: var(--text-bright); font-size: 15px; margin-top: 24px; margin-bottom: 8px; }}
p {{ margin-bottom: 16px; }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ color: var(--accent-hover); text-decoration: underline; }}
code {{
  font-family: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace;
  font-size: 13.5px;
}}
p code, li code, td code {{
  background: var(--bg-code);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border);
  color: var(--accent);
  font-size: 13px;
}}
pre {{
  background: var(--bg-code);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  overflow-x: auto;
  line-height: 1.5;
}}
pre code {{
  color: var(--text);
  font-size: 13.5px;
}}
ul, ol {{
  margin-bottom: 16px;
  padding-left: 24px;
}}
li {{
  margin-bottom: 4px;
}}
.table-wrap {{
  overflow-x: auto;
  margin-bottom: 20px;
}}
table {{
  border-collapse: collapse;
  width: 100%;
  font-size: 14px;
}}
th, td {{
  text-align: left;
  padding: 10px 14px;
  border: 1px solid var(--border);
}}
th {{
  background: var(--bg-sidebar);
  color: var(--text-bright);
  font-weight: 600;
}}
td {{ background: var(--bg-code); }}
hr {{
  border: none;
  border-top: 1px solid var(--border);
  margin: 32px 0;
}}
strong {{ color: var(--text-bright); }}
.page-nav {{
  display: flex;
  justify-content: space-between;
  margin-top: 64px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}}
.page-nav a {{
  padding: 8px 16px;
  background: rgba(122, 162, 247, 0.1);
  border-radius: 6px;
  font-size: 14px;
}}
.page-nav a:hover {{
  background: rgba(122, 162, 247, 0.2);
  text-decoration: none;
}}
.hamburger {{
  display: none;
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 100;
  background: var(--bg-sidebar);
  border: 1px solid var(--border);
  color: var(--text);
  font-size: 20px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
}}
@media (max-width: 768px) {{
  nav {{
    transform: translateX(-100%);
    transition: transform 0.2s;
    z-index: 50;
  }}
  nav.open {{ transform: translateX(0); }}
  main {{ margin-left: 0; padding: 48px 20px; }}
  .hamburger {{ display: block; }}
}}

/* Syntax highlighting for code blocks */
.language-rholang .kw,
pre code .kw {{ color: var(--kw); }}
</style>
</head>
<body>
<button class="hamburger" onclick="document.querySelector('nav').classList.toggle('open')">&#9776;</button>
<nav>
  <div class="logo">
    <h2>Rholang Guide</h2>
    <p>F1R3FLY Developer Docs</p>
  </div>
  {sidebar}
</nav>
<main>
{body}
<div class="page-nav">
  <span>{prev_link}</span>
  <span>{next_link}</span>
</div>
</main>
</body>
</html>
"""


def main():
    for md_file, html_file, title in PAGES:
        page = build_page(md_file, html_file, title)
        out_path = os.path.join(OUT_DIR, html_file)
        with open(out_path, "w") as f:
            f.write(page)
        print(f"  {html_file}")
    print(f"\nDone. Open {os.path.join(OUT_DIR, 'index.html')} in your browser.")


if __name__ == "__main__":
    main()
