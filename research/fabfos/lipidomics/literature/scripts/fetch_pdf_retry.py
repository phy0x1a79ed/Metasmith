"""For each row marked 'missing' in pdf_status.tsv:
   1. Look up PMC ID via the new idconv API (pmc.ncbi.nlm.nih.gov/tools/idconv)
   2. If a PMC ID is found, retry the PMC PDF route.
   3. As a final fallback, try the doi.org → publisher landing → look for an in-page
      'pdf' link.

Updates pdf_status.tsv in place and writes any new PDFs into the pdfs dir.
"""
from __future__ import annotations
import csv, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE_ROOT = ROOT.parents[1]
PDF_DIR = SCOPE_ROOT / ".awm" / "data" / "literature" / "pdfs"
FINAL = ROOT / "search" / "final_corpus.tsv"
STATUS = ROOT / "search" / "pdf_status.tsv"

EMAIL = "phyberosis@gmail.com"
HEADERS = {"User-Agent": f"scadc-lit/1.0 (mailto:{EMAIL})", "Accept": "*/*"}
TIMEOUT = 30


def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def get_text(url: str) -> str:
    return get_bytes(url).decode("utf-8", errors="replace")


def slug_filename(first_author: str, year: str, title: str) -> str:
    last = re.split(r"[\s,]+", first_author.strip())[0] or "anon"
    last = re.sub(r"[^A-Za-z0-9]+", "", last)
    words = re.findall(r"[A-Za-z0-9]+", title.lower())[:6]
    slug = "-".join(words) or "untitled"
    return f"{last}{year}_{slug}.pdf"


def lookup_pmcid(doi: str) -> str | None:
    url = (
        "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
        f"?email={EMAIL}&tool=scadc-lit&ids={urllib.parse.quote(doi, safe='/')}&format=json"
    )
    try:
        d = json.loads(get_text(url))
        recs = d.get("records") or []
        if recs and "pmcid" in recs[0] and recs[0]["pmcid"]:
            return recs[0]["pmcid"]
    except Exception:
        return None
    return None


def try_pmc(pmcid: str, out_path: Path) -> bool:
    """Use Europe PMC -- the NCBI PMC PDF endpoint now serves a JS proof-of-work
    interstitial that blocks scripted downloads. Europe PMC mirrors PMC content
    and serves PDFs directly."""
    if not pmcid:
        return False
    p = pmcid if pmcid.startswith("PMC") else f"PMC{pmcid}"
    urls = [
        f"https://europepmc.org/articles/{p}?pdf=render",
        f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={p}&blobtype=pdf",
    ]
    for url in urls:
        try:
            data = get_bytes(url)
            if data[:5] == b"%PDF-":
                PDF_DIR.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(data)
                return True
        except Exception:
            continue
    return False


def try_publisher_landing(doi: str, out_path: Path) -> tuple[bool, str]:
    """Hit doi.org and look for an inline PDF link in the landing HTML."""
    try:
        html = get_text(f"https://doi.org/{urllib.parse.quote(doi, safe='/')}")
    except Exception as e:
        return False, f"landing err: {e}"
    # Find candidate PDF URLs in the landing page
    cands = set(re.findall(r'href=[\'"]([^\'"]+\.pdf[^\'"]*)[\'"]', html, re.I))
    cands |= set(re.findall(r'content=[\'"]([^\'"]+\.pdf[^\'"]*)[\'"]', html, re.I))
    cands = sorted(cands, key=lambda u: (0 if "pdf" in u.lower() else 1, len(u)))
    for u in list(cands)[:5]:
        if u.startswith("/"):
            # join with doi.org redirected origin — approximate
            continue
        try:
            data = get_bytes(u)
            if data[:5] == b"%PDF-":
                PDF_DIR.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(data)
                return True, u
        except Exception:
            continue
    return False, "no inline pdf found"


def main() -> None:
    corpus = {r["doi"]: r for r in csv.DictReader(FINAL.open(), delimiter="\t")}
    rows = list(csv.DictReader(STATUS.open(), delimiter="\t"))
    missing = [r for r in rows if r["status"] == "missing"]
    print(f"retrying {len(missing)} missing rows via PMC idconv + publisher landing", file=sys.stderr)

    for r in missing:
        doi = r["doi"]
        c = corpus.get(doi, {})
        fname = slug_filename(c.get("first_author", "anon"), c.get("year", ""), c.get("title", "untitled"))
        out = PDF_DIR / fname

        # 1) Try PMC via idconv
        pmcid = lookup_pmcid(doi)
        time.sleep(0.4)
        if pmcid and try_pmc(pmcid, out):
            r["filename"] = fname; r["status"] = "ok"; r["source"] = "pmc"
            r["note"] = f"via idconv -> {pmcid}"
            print(f"  {doi:48s} OK via PMC ({pmcid})", file=sys.stderr)
            continue

        # 2) Publisher-landing inline pdf
        ok, info = try_publisher_landing(doi, out)
        if ok:
            r["filename"] = fname; r["status"] = "ok"; r["source"] = "publisher"
            r["note"] = f"landing -> {info[:120]}"
            print(f"  {doi:48s} OK via publisher landing", file=sys.stderr)
        else:
            r["note"] = (r.get("note", "") + f"; retry: pmcid={pmcid or 'none'}; landing={info}")[:400]
            print(f"  {doi:48s} STILL MISSING (pmcid={pmcid}, landing={info})", file=sys.stderr)
        time.sleep(0.4)

    with STATUS.open("w") as f:
        w = csv.DictWriter(f, fieldnames=["doi", "filename", "status", "source", "note"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    print(f"\nDONE: {n_ok}/{len(rows)} PDFs downloaded after retry.", file=sys.stderr)


if __name__ == "__main__":
    main()
