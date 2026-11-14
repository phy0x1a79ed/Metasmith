"""Retry MISSING rows from abstracts.tsv with rate-limited sequential requests
through PubMed esearch+efetch. NCBI allows ~3 req/s without an API key.
"""
from __future__ import annotations
import csv, re, sys, time, html, urllib.parse, json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "search" / "abstracts.tsv"
OUT = IN  # overwrite
EMAIL = "phyberosis@gmail.com"
TOOL = "scadc-literature"
HEADERS = {"User-Agent": f"{TOOL}/1.0 (mailto:{EMAIL})"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def pubmed_abstract(doi: str) -> tuple[str | None, str | None]:
    if not doi:
        return None, None
    q = urllib.parse.quote(doi)
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={q}[doi]&retmode=json&email={EMAIL}&tool={TOOL}"
    )
    try:
        j = json.loads(get(url))
        ids = j.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None, None
        pmid = ids[0]
    except Exception as e:
        return None, f"esearch-err: {e}"
    time.sleep(0.4)
    try:
        xml = get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&id={pmid}&rettype=abstract&retmode=xml&email={EMAIL}&tool={TOOL}"
        )
        # Some abstracts split into <AbstractText Label="BACKGROUND">…</AbstractText> etc.
        parts = re.findall(r"<AbstractText\b[^>]*>(.*?)</AbstractText>", xml, re.S | re.I)
        if parts:
            return clean(" ".join(parts)), None
    except Exception as e:
        return None, f"efetch-err: {e}"
    return None, None


def main() -> None:
    rows = list(csv.DictReader(IN.open(), delimiter="\t"))
    n_retry = sum(1 for r in rows if r["abstract_source"] == "MISSING")
    print(f"retrying {n_retry} MISSING rows via PubMed (rate-limited)", file=sys.stderr)
    for i, r in enumerate(rows, 1):
        if r["abstract_source"] != "MISSING":
            continue
        ab, err = pubmed_abstract(r["doi"])
        time.sleep(0.4)  # ~2.5 req/s ceiling
        if ab:
            r["abstract_source"] = "pubmed"
            r["abstract"] = ab.replace("\t", " ").replace("\n", " ")[:8000]
            print(f"  [{i}] {r['doi']:50s} OK ({len(ab)} chars)", file=sys.stderr)
        else:
            print(f"  [{i}] {r['doi']:50s} STILL MISSING{(' -- ' + err) if err else ''}", file=sys.stderr)
    with OUT.open("w") as f:
        w = csv.DictWriter(f, fieldnames=["doi", "pmcid", "abstract_source", "abstract"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
