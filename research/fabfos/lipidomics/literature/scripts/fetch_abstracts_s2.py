"""Final pass: try Semantic Scholar + OpenAlex for any rows still MISSING."""
from __future__ import annotations
import csv, json, sys, time, html, re, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "search" / "abstracts.tsv"
EMAIL = "phyberosis@gmail.com"
HEADERS = {"User-Agent": f"scadc-lit/1.0 (mailto:{EMAIL})"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(t: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def s2(doi: str) -> str | None:
    try:
        d = json.loads(get(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi, safe='/')}?fields=abstract"))
        ab = d.get("abstract")
        return clean(ab) if ab else None
    except Exception:
        return None


def oa(doi: str) -> str | None:
    try:
        d = json.loads(get(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi, safe='/')}?mailto={EMAIL}"))
        ai = d.get("abstract_inverted_index")
        if not ai:
            return None
        ws = sorted([(p, w) for w, ps in ai.items() for p in ps])
        return " ".join(w for _, w in ws)
    except Exception:
        return None


def main() -> None:
    rows = list(csv.DictReader(TSV.open(), delimiter="\t"))
    missing = [r for r in rows if r["abstract_source"] == "MISSING"]
    print(f"final pass on {len(missing)} rows (S2 then OpenAlex)", file=sys.stderr)
    for r in missing:
        doi = r["doi"]
        ab = s2(doi)
        src = "s2"
        if not ab:
            time.sleep(0.5)
            ab = oa(doi)
            src = "openalex"
        time.sleep(0.6)
        if ab:
            r["abstract_source"] = src
            r["abstract"] = ab.replace("\t", " ").replace("\n", " ")[:8000]
            print(f"  {doi:48s} OK via {src}", file=sys.stderr)
        else:
            print(f"  {doi:48s} STILL MISSING", file=sys.stderr)
    with TSV.open("w") as f:
        w = csv.DictWriter(f, fieldnames=["doi", "pmcid", "abstract_source", "abstract"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
