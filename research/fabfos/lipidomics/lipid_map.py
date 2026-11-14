"""Real name->class lipid mapping (RefMet + Goslin), replacing the regex parser.

The MetaboScape `name` column holds trivial / systematic compound names from the
facility's spectral & target libraries (HMDB, NIST, Bruker MetaBASE, LipidBlast),
NOT shorthand. `lipidio.parse_shorthand`'s regex therefore resolved only ~87/2180
features. This module does authoritative name->class resolution instead:

  * RefMet (Metabolomics Workbench) batch name-standardisation -> standardized
    name + super/main/sub class for EVERY name (trivial or shorthand). Cached to
    a local JSON so reruns are offline & reproducible.
  * Goslin (pygoslin) parses the standardized shorthand RefMet returns (e.g.
    "PC 12:0/12:0", "PG 12:0_19:0") -> LIPID MAPS category + total C + total DB.

Output: features_mapped.csv next to features_clean.csv (does NOT overwrite the
regex baseline). Columns add: refmet_name, super_class, main_class, sub_class,
gos_category, gos_class, map_total_c, map_total_db, map_source, is_lipid_map.

Env: p312. Run from the project dir.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path("data/fabfos/runs/scadc_lipidomics")
FEATURES = ROOT / "processed/metaboscape/features_clean.csv"
OUT = ROOT / "processed/metaboscape/features_mapped.csv"
CACHE = ROOT / "refmet/refmet_name_cache.json"
REFMET_BATCH = ("https://www.metabolomicsworkbench.org/databases/refmet/"
                "name_to_refmet_new_min.php")
CHUNK = 250


def refmet_batch(names: list[str]) -> dict:
    """POST names to RefMet; return {input_name: {refmet_name, super/main/sub}}."""
    out: dict = {}
    payload = urllib.parse.urlencode(
        {"metabolite_name": "\n".join(names)}).encode()
    req = urllib.request.Request(REFMET_BATCH, data=payload,
                                 headers={"Content-Type":
                                          "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=120) as r:
        text = r.read().decode("utf-8", "replace")
    for line in text.splitlines():
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) < 7 or cells[0] == "Input name":
            continue
        inp, std, _formula, _mass, sup, main, sub = cells[:7]
        out[inp] = {"refmet_name": std, "super_class": sup,
                    "main_class": main, "sub_class": sub}
    return out


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def save_cache(c: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, indent=0))


def resolve_refmet(names: list[str]) -> dict:
    cache = load_cache()
    todo = [n for n in names if n not in cache]
    print(f"[refmet] {len(names)} unique names, {len(todo)} uncached")
    for i in range(0, len(todo), CHUNK):
        batch = todo[i:i + CHUNK]
        try:
            res = refmet_batch(batch)
        except Exception as e:           # network hiccup: record empties, go on
            print(f"[refmet] chunk {i} failed: {e}")
            res = {}
        for n in batch:
            cache[n] = res.get(n, {"refmet_name": "-", "super_class": "-",
                                   "main_class": "-", "sub_class": "-"})
        save_cache(cache)
        print(f"[refmet] {min(i + CHUNK, len(todo))}/{len(todo)}")
        time.sleep(0.5)
    return cache


import re

_GOSLIN = None


def _get_goslin():
    global _GOSLIN
    if _GOSLIN is None:
        try:
            from pygoslin.parser.Parser import LipidParser
            _GOSLIN = LipidParser()
        except Exception:
            _GOSLIN = False
    return _GOSLIN


def clean_name(n: str) -> str:
    """Strip isomer/stereo decorations RefMet/Goslin choke on."""
    s = re.sub(r"_Iso\d+$", "", str(n))
    s = re.sub(r",\s*(DL|D|L|rac)-?\s*$", "", s)
    return s.strip()


def goslin_parse(*candidates):
    """Try Goslin on each candidate string; return first (category, class, C, DB)."""
    parser = _get_goslin()
    if not parser:
        return (None, None, None, None)
    for s in candidates:
        if not s or s == "-":
            continue
        try:
            lip = parser.parse(s)
            lp = lip.lipid
            cls = lp.get_extended_class()
            info = lp.info
            tc = getattr(info, "num_carbon", None) if info else None
            db = getattr(info, "double_bonds", None) if info else None
            tdb = db.get_num() if hasattr(db, "get_num") else db
            return (cls, cls, tc, tdb)
        except Exception:
            continue
    return (None, None, None, None)


def main():
    df = pd.read_csv(FEATURES)
    uniq = sorted(df["name"].dropna().astype(str).unique())
    cache = resolve_refmet(uniq)

    rows = []
    # second RefMet pass on cleaned variants of the misses
    misses = [n for n in uniq
              if cache.get(n, {}).get("sub_class", "-") in ("-", "")]
    cleaned = {n: clean_name(n) for n in misses if clean_name(n) != n}
    extra = resolve_refmet(sorted(set(cleaned.values())))

    rows = []
    for n in uniq:
        rm = cache.get(n, {})
        if rm.get("sub_class", "-") in ("-", "") and n in cleaned:
            alt = extra.get(cleaned[n], {})
            if alt.get("sub_class", "-") not in ("-", ""):
                rm = alt
        std = rm.get("refmet_name", "-")
        # Goslin on raw name, cleaned name, and the RefMet standardized name
        gcat, gcls, gc, gdb = goslin_parse(std if std != "-" else None,
                                           n, clean_name(n))
        sub = rm.get("sub_class", "-")
        sup = rm.get("super_class", "-")
        # final class: prefer RefMet sub_class (PE/PG/PC/...), else goslin head
        final = sub if sub not in ("-", "") else (gcls or None)
        src = ("refmet" if sub not in ("-", "") else
               ("goslin" if gcls else "unmapped"))
        rows.append(dict(name=n, refmet_name=std, super_class=sup,
                         main_class=rm.get("main_class", "-"), sub_class=sub,
                         gos_category=gcat, map_total_c=gc, map_total_db=gdb,
                         final_class=final, map_source=src,
                         is_lipid_map=sup not in ("-", "", "Alkaloids")))
    mp = pd.DataFrame(rows).set_index("name")
    out = df.join(mp, on="name")
    out.to_csv(OUT, index=False)

    n = len(out)
    nmap = int((out["map_source"] != "unmapped").sum())
    print(f"\n[map] {nmap}/{n} features mapped to a class "
          f"({100 * nmap / n:.0f}%) — baseline regex was 87 ({87 * 100 // n}%)")
    print("\n[map] by RefMet super_class:")
    print(out["super_class"].value_counts().head(15).to_string())
    print("\n[map] top final_class:")
    print(out["final_class"].value_counts().head(20).to_string())
    print(f"\n[map] wrote {OUT}")


if __name__ == "__main__":
    main()
