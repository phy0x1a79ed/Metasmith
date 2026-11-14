"""Download open-access PDFs for every entry in final_corpus.tsv.

Resolution chain per row:
  1. If pmcid present  -> PMC OA service:
                             https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/
  2. Else Unpaywall    -> best_oa_location.url_for_pdf
  3. Else bioRxiv      -> https://api.biorxiv.org/details/biorxiv/{doi}
                             (then https://www.biorxiv.org/.../full.pdf)
  4. Else publisher    -> follow Crossref's primary URL, look for an inline PDF link

Saves to .awm/data/literature/pdfs/<filename>.pdf with stable name:
    {first_author_lastname}{year}_{first-6-title-words-kebab}.pdf

Writes pdf_status.tsv with columns: doi, filename, status, source, note.
status in {ok, missing}.  source in {pmc, unpaywall, biorxiv, publisher, ""}.
"""
from __future__ import annotations
import csv, json, re, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE_ROOT = ROOT.parents[1]                                   # main/literature -> .../literature
PDF_DIR = SCOPE_ROOT / ".awm" / "data" / "literature" / "pdfs"
IN = ROOT / "search" / "final_corpus.tsv"
OUT = ROOT / "search" / "pdf_status.tsv"

EMAIL = "phyberosis@gmail.com"
HEADERS = {"User-Agent": f"scadc-lit/1.0 (mailto:{EMAIL})"}
TIMEOUT = 30
SLEEP = 0.6


def http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def http_get(url: str) -> str:
    return http_get_bytes(url).decode("utf-8", errors="replace")


def head_or_get(url: str) -> tuple[int, str | None]:
    """Return (http_status, content_type) following redirects."""
    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.headers.get("Content-Type", "")
    except Exception:
        return 0, None


def slug_filename(first_author: str, year: str, title: str) -> str:
    last = re.split(r"[\s,]+", first_author.strip())[0] or "anon"
    last = re.sub(r"[^A-Za-z0-9]+", "", last)
    words = re.findall(r"[A-Za-z0-9]+", title.lower())[:6]
    slug = "-".join(words) or "untitled"
    return f"{last}{year}_{slug}.pdf"


def looks_like_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def save_pdf(path: Path, data: bytes) -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def try_pmc(pmcid: str, out_path: Path) -> tuple[bool, str]:
    if not pmcid:
        return False, "no pmcid"
    p = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{p}/pdf/"
    try:
        data = http_get_bytes(url)
        if looks_like_pdf(data):
            save_pdf(out_path, data); return True, url
        return False, f"non-pdf response ({len(data)} B)"
    except Exception as e:
        return False, f"err: {e}"


def try_unpaywall(doi: str, out_path: Path) -> tuple[bool, str]:
    try:
        d = json.loads(http_get(f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='/')}?email={EMAIL}"))
    except Exception as e:
        return False, f"unpaywall lookup err: {e}"
    locs = d.get("oa_locations") or []
    best = d.get("best_oa_location") or {}
    candidates = [best.get("url_for_pdf")]
    candidates += [loc.get("url_for_pdf") for loc in locs]
    candidates += [loc.get("url") for loc in locs]
    seen, ok = set(), False
    for u in candidates:
        if not u or u in seen:
            continue
        seen.add(u)
        try:
            data = http_get_bytes(u)
            if looks_like_pdf(data):
                save_pdf(out_path, data); return True, u
        except Exception:
            continue
    return False, "no OA pdf in unpaywall locations"


def try_biorxiv(doi: str, out_path: Path) -> tuple[bool, str]:
    try:
        d = json.loads(http_get(f"https://api.biorxiv.org/details/biorxiv/{urllib.parse.quote(doi, safe='/')}"))
    except Exception:
        return False, "biorxiv lookup err"
    coll = d.get("collection") or []
    if not coll:
        return False, "no biorxiv record"
    # try newest version
    latest = coll[-1]
    url = f"https://www.biorxiv.org/content/{doi}v{latest.get('version', 1)}.full.pdf"
    try:
        data = http_get_bytes(url)
        if looks_like_pdf(data):
            save_pdf(out_path, data); return True, url
    except Exception:
        pass
    return False, "biorxiv pdf fetch failed"


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(IN.open(), delimiter="\t"))
    print(f"fetching PDFs for {len(rows)} corpus entries -> {PDF_DIR}", file=sys.stderr)

    results = []
    for i, r in enumerate(rows, 1):
        doi = r["doi"]; pmcid = r.get("pmcid", "")
        fname = slug_filename(r["first_author"], r["year"], r["title"])
        out = PDF_DIR / fname

        if out.exists() and out.stat().st_size > 1024:
            results.append({"doi": doi, "filename": fname, "status": "ok", "source": "cached", "note": ""})
            print(f"  [{i:02d}/{len(rows)}] {doi:45s} CACHED", file=sys.stderr)
            continue

        attempts: list[tuple[str, callable]] = [
            ("pmc",        lambda: try_pmc(pmcid, out) if pmcid else (False, "no pmcid")),
            ("unpaywall",  lambda: try_unpaywall(doi, out)),
            ("biorxiv",    lambda: try_biorxiv(doi, out)),
        ]

        ok, src, note = False, "", ""
        for label, fn in attempts:
            try:
                ok, info = fn()
            except Exception as e:
                ok, info = False, f"raised: {e}"
            if ok:
                src = label
                note = f"from {info[:120]}"
                break
            else:
                note = f"{label}: {info}"
            time.sleep(SLEEP)

        if ok:
            print(f"  [{i:02d}/{len(rows)}] {doi:45s} OK via {src} -> {fname}", file=sys.stderr)
            results.append({"doi": doi, "filename": fname, "status": "ok", "source": src, "note": note})
        else:
            print(f"  [{i:02d}/{len(rows)}] {doi:45s} MISSING ({note})", file=sys.stderr)
            results.append({"doi": doi, "filename": "", "status": "missing", "source": "", "note": note})

    with OUT.open("w") as f:
        w = csv.DictWriter(f, fieldnames=["doi", "filename", "status", "source", "note"], delimiter="\t")
        w.writeheader()
        w.writerows(results)
    n_ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\nDONE: {n_ok}/{len(results)} PDFs downloaded. status written to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
