#!/usr/bin/env python3
"""Fetch a public PDF (or HTML page) and print its text, with PDF page numbers.

The way to read web pages in the cloud session (the built-in WebFetch tool cannot resolve hosts there; this
script goes through the session proxy), and for reports over WebFetch's 10 MB limit on the Mac. Downloads are
cached in $PDF_CACHE (default: a temp folder).

Usage:
  python3 -E tools/pdftext.py "<url>"                                   # whole page / document
  python3 -E tools/pdftext.py "<url>" --grep "total assets|customers' deposits" --context 600
  python3 -E tools/pdftext.py "<url>" --pages 1-15

Extraction uses the pdftotext binary when installed, else pypdf, else pdfminer.six. Sites with bot protection
block this too; do not try to get around them.

Rebuilt on 12 Oct 2026 in the cloud session (the original script was not transferred).
"""
import argparse
import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")


def quote_url(url):
    """Percent-encode non-ASCII characters (Arabic paths) so urllib can request them."""
    p = urllib.parse.urlsplit(url)
    host = p.hostname.encode("idna").decode("ascii") if p.hostname else ""
    netloc = host + (f":{p.port}" if p.port else "")
    return urllib.parse.urlunsplit((p.scheme, netloc, urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;="),
                                    urllib.parse.quote(p.query, safe="=&%/:+,;@!$'()*"), p.fragment))


def fetch(url, timeout=60, cache=None):
    """Return (bytes, content_type, final_url). Raises on HTTP or network errors."""
    cache = cache or os.environ.get("PDF_CACHE") or os.path.join(tempfile.gettempdir(), "gccfi_pdf")
    os.makedirs(cache, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    path = os.path.join(cache, key)
    if os.path.exists(path) and os.path.exists(path + ".meta"):
        ctype, final = open(path + ".meta", encoding="utf-8").read().split("\n", 1)
        return open(path, "rb").read(), ctype, final
    req = urllib.request.Request(quote_url(url), headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        ctype = r.headers.get("Content-Type", "")
        final = r.geturl()
    with open(path, "wb") as fh:
        fh.write(data)
    with open(path + ".meta", "w", encoding="utf-8") as fh:
        fh.write(f"{ctype}\n{final}")
    return data, ctype, final


def pdf_pages(data):
    """List of page texts for PDF bytes (empty list if no extractor worked)."""
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(data)
            name = fh.name
        try:
            out = subprocess.run(["pdftotext", "-layout", name, "-"], capture_output=True, timeout=300)
            if out.returncode == 0:
                pages = out.stdout.decode("utf-8", "replace").split("\f")
                if any(p.strip() for p in pages):
                    return pages[:-1] if pages and not pages[-1].strip() else pages
        finally:
            os.unlink(name)
    try:
        import io
        from pypdf import PdfReader
        return [(pg.extract_text() or "") for pg in PdfReader(io.BytesIO(data)).pages]
    except Exception:
        pass
    try:
        import io
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(data)).split("\f")
    except Exception:
        return []


def html_text(data):
    """Readable text of an HTML page; LinkedIn profile/company links found on the page are listed at the end."""
    t = data.decode("utf-8", "replace")
    links = sorted(set(re.findall(r'href="(https?://[a-z]*\.?linkedin\.com/(?:in|company)/[^"#?]+)', t, re.I)))
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h[1-6]|section|article|td|th)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t).replace(" ", " ")
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    if links:
        t += "\n[LinkedIn links on this page: " + " ".join(links) + "]"
    return t


def document_pages(url, cache=None):
    """Return (pages, kind) for a URL: PDF pages, or a single 'page' of HTML text."""
    data, ctype, _ = fetch(url, cache=cache)
    if data[:5] == b"%PDF-" or "pdf" in ctype.lower():
        return pdf_pages(data), "pdf"
    return [html_text(data)], "html"


def parse_pages(spec, n):
    out = set()
    for part in spec.split(","):
        a, _, b = part.partition("-")
        lo, hi = int(a), int(b or a)
        out.update(range(max(1, lo), min(n, hi) + 1))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--grep", help="regex (case-insensitive); prints matches with context and page numbers")
    ap.add_argument("--context", type=int, default=400)
    ap.add_argument("--pages", help="e.g. 1-15 or 3,7,9-11: print whole pages")
    a = ap.parse_args()
    try:
        pages, kind = document_pages(a.url)
    except Exception as e:
        sys.exit(f"fetch failed: {e}")
    if not pages or not any(p.strip() for p in pages):
        sys.exit("no extractable text (scanned PDF, blocked page or empty response)")
    print(f"[{kind}, {len(pages)} page(s)]")
    if a.pages:
        for n in parse_pages(a.pages, len(pages)):
            print(f"\n===== page {n} =====\n{pages[n - 1]}")
    if a.grep:
        rx = re.compile(a.grep, re.I)
        hits = 0
        for n, text in enumerate(pages, 1):
            for m in rx.finditer(text):
                hits += 1
                lo, hi = max(0, m.start() - a.context // 2), min(len(text), m.end() + a.context // 2)
                print(f"\n----- page {n} -----\n{text[lo:hi]}")
        print(f"\n[{hits} match(es)]")
    if not a.pages and not a.grep:
        print("\n\f".join(pages))


if __name__ == "__main__":
    main()
