#!/usr/bin/env python3
from pathlib import Path
import sys, os, shutil, subprocess, html, re


def markdown_to_html(md_text):
    try:
        import markdown
        return markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "sane_lists", "nl2br"]
        )
    except Exception:
        escaped = html.escape(md_text)
        escaped = re.sub(r"^# (.+)$", r"<h1>\1</h1>", escaped, flags=re.M)
        escaped = re.sub(r"^## (.+)$", r"<h2>\1</h2>", escaped, flags=re.M)
        escaped = re.sub(r"^### (.+)$", r"<h3>\1</h3>", escaped, flags=re.M)
        paras = []
        for block in re.split(r"\n\s*\n", escaped):
            if block.startswith("<h"):
                paras.append(block)
            else:
                paras.append("<p>" + block.replace("\n", "<br>") + "</p>")
        return "\n".join(paras)


def find_browser():
    candidates = [
        os.environ.get("CHROME_PATH"),
        os.environ.get("EDGE_PATH"),
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


CSS = r"""
@page {
    size: A4;
    margin: 18mm 18mm 18mm 18mm;
}
:root {
    font-family: "Microsoft JhengHei", "Noto Sans TC", "PingFang TC",
                 "Heiti TC", "Arial Unicode MS", sans-serif;
    color: #202124;
    line-height: 1.72;
    font-size: 11.5pt;
}
body {
    max-width: 100%;
    margin: 0 auto;
}
h1 {
    font-size: 22pt;
    text-align: center;
    margin: 18mm 0 10mm;
    line-height: 1.35;
}
h2 {
    font-size: 15.5pt;
    margin-top: 10mm;
    margin-bottom: 4mm;
    padding-bottom: 2mm;
    border-bottom: 1px solid #aaa;
    page-break-after: avoid;
}
h3 {
    font-size: 13pt;
    margin-top: 7mm;
    margin-bottom: 2mm;
    page-break-after: avoid;
}
p {
    margin: 0 0 4.2mm;
    text-align: justify;
    orphans: 3;
    widows: 3;
}
blockquote {
    margin: 5mm 0;
    padding: 3mm 5mm;
    background: #f5f5f5;
    border-left: 3px solid #888;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin: 5mm 0;
    font-size: 10.5pt;
}
th, td {
    border: 1px solid #bbb;
    padding: 2.5mm;
    vertical-align: top;
}
th { background: #f2f2f2; }
ul, ol { margin: 2mm 0 4mm 7mm; }
li { margin-bottom: 1.5mm; }
code { font-family: Consolas, monospace; font-size: 9.5pt; }
a { color: inherit; text-decoration: none; }
hr {
    border: none;
    border-top: 1.5px solid #999;
    margin: 12mm 0;
    page-break-after: always;
}
"""


def main():
    if len(sys.argv) != 3:
        print("Usage: render_pdf.py <input.md> <output.pdf>")
        sys.exit(2)

    md_path = Path(sys.argv[1]).resolve()
    pdf_path = Path(sys.argv[2]).resolve()
    if not md_path.exists():
        raise SystemExit(f"Missing Markdown file: {md_path}")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = pdf_path.with_suffix(".html")
    body = markdown_to_html(md_path.read_text(encoding="utf-8"))

    full = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>Case Report</title>
  <style>{CSS}</style>
</head>
<body>{body}</body>
</html>"""
    html_path.write_text(full, encoding="utf-8")

    browser = find_browser()
    if not browser:
        raise SystemExit(
            "No Chrome/Edge/Chromium found. HTML was generated at "
            f"{html_path}. Install a Chromium-based browser or set CHROME_PATH/EDGE_PATH."
        )

    url = html_path.as_uri()
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not pdf_path.exists():
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit("Browser PDF generation failed.")

    print(f"Wrote PDF: {pdf_path}")


if __name__ == "__main__":
    main()
