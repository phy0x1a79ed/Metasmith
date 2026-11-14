"""Fetch abstracts for every DOI in candidates.tsv.

Resolution chain per row:
  1. If pmcid present -> NCBI E-utilities efetch (PMC) for the abstract.
  2. Else -> Crossref /works/{doi} - returns 'abstract' when publisher deposited it.
  3. Else -> PubMed esearch by DOI -> efetch the abstract.
Writes a parallel TSV with columns: doi, pmcid, abstract_source, abstract.
"""

from __future__ import annotations
import csv, re, sys, time, html, urllib.parse, concurrent.futures as cf
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
IN  = ROOT / "search" / "candidates.tsv"
OUT = ROOT / "search" / "abstracts.tsv"
EMAIL = "phyberosis@gmail.com"
HEADERS = {"User-Agent": f"scadc-literature/1.0 (mailto:{EMAIL})"}
TIMEOUT = 20


def _http_get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8", errors="replace")


def _clean(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", txt)         # strip XML/HTML tags
    txt = html.unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def fetch_pmc(pmcid: str) -> str | None:
    pmcid = pmcid.replace("PMC", "")
    if not pmcid:
        return None
    try:
        url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&rettype=xml"
        xml = _http_get(url)
        m = re.search(r"<abstract\b[^>]*>(.*?)</abstract>", xml, re.S | re.I)
        if m:
            return _clean(m.group(1))
    except Exception as e:
        return f"__error__: PMC: {e}"
    return None


def fetch_crossref(doi: str) -> str | None:
    if not doi:
        return None
    try:
        url = f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}"
        import json
        data = json.loads(_http_get(url))
        ab = data.get("message", {}).get("abstract")
        if ab:
            return _clean(ab)
    except Exception as e:
        return f"__error__: Crossref: {e}"
    return None


def fetch_pubmed_via_doi(doi: str) -> str | None:
    if not doi:
        return None
    try:
        s = _http_get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={urllib.parse.quote(doi)}[doi]&retmode=json"
        )
        import json
        ids = json.loads(s).get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None
        pmid = ids[0]
        xml = _http_get(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract&retmode=xml"
        )
        m = re.search(r"<AbstractText\b[^>]*>(.*?)</AbstractText>", xml, re.S | re.I)
        if m:
            return _clean(m.group(1))
    except Exception as e:
        return f"__error__: PubMed: {e}"
    return None


def resolve_one(row: dict) -> dict:
    doi, pmcid = row.get("doi", "").strip(), row.get("pmcid", "").strip()
    src, abstract = None, None
    if pmcid:
        abstract = fetch_pmc(pmcid)
        if abstract and not abstract.startswith("__error__"):
            src = "pmc"
    if not abstract or abstract.startswith("__error__"):
        ab2 = fetch_crossref(doi)
        if ab2 and not ab2.startswith("__error__"):
            abstract, src = ab2, "crossref"
    if not abstract or abstract.startswith("__error__"):
        ab3 = fetch_pubmed_via_doi(doi)
        if ab3 and not ab3.startswith("__error__"):
            abstract, src = ab3, "pubmed"
    return {
        "doi": doi,
        "pmcid": pmcid,
        "abstract_source": src or "MISSING",
        "abstract": (abstract or "").replace("\t", " ").replace("\n", " ")[:8000],
    }


def main() -> None:
    rows = list(csv.DictReader(IN.open(), delimiter="\t"))
    print(f"fetching abstracts for {len(rows)} candidates", file=sys.stderr)
    out_rows = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for i, res in enumerate(ex.map(resolve_one, rows), 1):
            out_rows.append(res)
            print(f"  [{i}/{len(rows)}] {res['doi']:50s} -> {res['abstract_source']}", file=sys.stderr)
    with OUT.open("w") as f:
        w = csv.DictWriter(f, fieldnames=["doi", "pmcid", "abstract_source", "abstract"], delimiter="\t")
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
