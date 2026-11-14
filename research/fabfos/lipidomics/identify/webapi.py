"""Cached HTTP clients for the public services this lane queries.

Every response is written to disk keyed by the request, so a re-run is
reproducible without re-querying and the record of *what answered* survives.
The cache entry stores the URL, the fetch time and the status alongside the
body; a cache hit is therefore auditable, not just fast.

Services, and what each is good for:

  LIPID MAPS REST      formula and shorthand lookup against LMSD. Verified live.
                       It has NO exact-mass endpoint -- the service rejects mass
                       and accepts only formula / identifier / structure inputs
                       -- so mass search must go through generated formulas or
                       the offline RefMet dump.
  Metabolomics         RefMet name and formula lookup, which is the class
  Workbench            vocabulary the rest of the project already uses. Its
                       `moverz` mass-search endpoint returns empty results even
                       for the examples in its own documentation; it is treated
                       as broken and nothing here depends on it.
  GNPS2 FASST          asynchronous spectral search (submit -> poll -> fetch)
                       over the GNPS community library and, more importantly,
                       indexes of public repository data -- coverage no vendor
                       library provides. This is the reason to go to the web at
                       all: the facility already searched the vendor libraries.
  MassBank Europe      second spectral source, live at v2025.12.1.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

LIPIDMAPS = "https://www.lipidmaps.org/rest/compound"
WORKBENCH = "https://www.metabolomicsworkbench.org/rest"
FASST = "https://api.fasst.gnps2.org"
MASSBANK = "https://massbank.eu/MassBank-api"

POLITE_DELAY = 0.34
TIMEOUT = 60


def _cache_path(key: str) -> Path:
    return common.CACHE_DIR / f"{hashlib.sha256(key.encode()).hexdigest()[:24]}.json"


def cached_get(url: str, *, force: bool = False) -> dict:
    """GET with an on-disk cache. Returns the stored envelope."""
    common.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(url)
    if path.exists() and not force:
        return json.loads(path.read_text())
    time.sleep(POLITE_DELAY)
    try:
        r = requests.get(url, timeout=TIMEOUT)
        env = {"url": url, "status": r.status_code, "body": r.text}
    except requests.RequestException as exc:
        env = {"url": url, "status": -1, "body": "", "error": str(exc)}
    env["fetched_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(env))
    return env


def cached_post_json(url: str, payload: dict, *, force: bool = False) -> dict:
    key = url + "\n" + json.dumps(payload, sort_keys=True)
    common.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(key)
    if path.exists() and not force:
        return json.loads(path.read_text())
    time.sleep(POLITE_DELAY)
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        env = {"url": url, "payload": payload, "status": r.status_code, "body": r.text}
    except requests.RequestException as exc:
        env = {"url": url, "payload": payload, "status": -1, "body": "", "error": str(exc)}
    env["fetched_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(env))
    return env


def _json_or_none(env: dict):
    if env.get("status") != 200 or not env.get("body", "").strip():
        return None
    try:
        return json.loads(env["body"])
    except json.JSONDecodeError:
        return None


def _rows(payload) -> list[dict]:
    """LIPID MAPS returns {"Row1": {...}, "Row2": {...}} or a bare object."""
    if payload is None:
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        if any(k.startswith("Row") for k in payload):
            return [v for k, v in payload.items() if k.startswith("Row") and isinstance(v, dict)]
        return [payload]
    return []


def lipidmaps_formula(formula: str) -> list[dict]:
    """LMSD records with this molecular formula."""
    env = cached_get(f"{LIPIDMAPS}/formula/{quote(formula)}/all/json")
    return _rows(_json_or_none(env))


def lipidmaps_abbrev(abbrev: str) -> list[dict]:
    """LMSD records matching a lipid shorthand abbreviation (e.g. 'PG 34:1')."""
    env = cached_get(f"{LIPIDMAPS}/abbrev/{quote(abbrev)}/all/json")
    return _rows(_json_or_none(env))


def refmet_formula(formula: str) -> list[dict]:
    env = cached_get(f"{WORKBENCH}/refmet/formula/{quote(formula)}/all")
    return _rows(_json_or_none(env))


def refmet_name(name: str) -> dict | None:
    env = cached_get(f"{WORKBENCH}/refmet/name/{quote(name)}/all")
    rows = _rows(_json_or_none(env))
    return rows[0] if rows else None


# --- GNPS2 FASST ----------------------------------------------------------------
# Asynchronous: POST /search returns a task id, GET /search/status/{id} reports
# progress, GET /search/result/{id} serves the hits. `query_spectrum` must be a
# JSON-encoded *string*, not a nested object -- the API validates it as a string.

def fasst_submit(peaks: list[list[float]], precursor_mz: float, charge: int,
                 library: str = "gnpslibrary", *, analog: str = "No",
                 pm_tolerance: float = 0.05, fragment_tolerance: float = 0.05,
                 cosine_threshold: float = 0.6, force: bool = False) -> str | None:
    spectrum = {
        "n_peaks": len(peaks),
        "peaks": peaks,
        "precursor_charge": abs(charge) or 1,
        "precursor_mz": precursor_mz,
    }
    payload = {
        "query_spectrum": json.dumps(spectrum),
        "library": library,
        "analog": analog,
        "pm_tolerance": pm_tolerance,
        "fragment_tolerance": fragment_tolerance,
        "cosine_threshold": cosine_threshold,
    }
    env = cached_post_json(f"{FASST}/search", payload, force=force)
    body = _json_or_none(env)
    if isinstance(body, dict):
        return body.get("id") or body.get("result_task")
    return None


def fasst_status(task_id: str) -> str | None:
    env = cached_get(f"{FASST}/search/status/{task_id}", force=True)
    body = _json_or_none(env)
    if isinstance(body, dict):
        return body.get("status")
    return None


def fasst_result(task_id: str, *, force: bool = False) -> dict | None:
    env = cached_get(f"{FASST}/search/result/{task_id}", force=force)
    return _json_or_none(env)


def _massbank_accessions(query: str) -> list[str]:
    """Accession list from a MassBank record search.

    The search endpoint returns accessions and atom counts only; compound detail
    needs a second call per accession. Note the parameter names are specific
    (`exact_mass` / `mass_tolerance` / uppercase `ion_mode`) -- passing anything
    else is silently ignored and the service returns the head of the whole
    database, which reads exactly like a successful search.
    """
    env = cached_get(f"{MASSBANK}/records/search?{query}")
    payload = _json_or_none(env)
    if not isinstance(payload, dict):
        return []
    return [
        r["accession"] for r in (payload.get("data") or [])
        if isinstance(r, dict) and r.get("accession")
    ]


def massbank_by_formula(formula: str) -> list[str]:
    return _massbank_accessions(f"formula={quote(formula)}")


def massbank_by_mass(neutral_mass: float, tol_da: float = 0.02,
                     polarity: str | None = None) -> list[str]:
    q = f"exact_mass={neutral_mass:.4f}&mass_tolerance={tol_da}"
    if polarity:
        q += f"&ion_mode={'POSITIVE' if polarity == 'pos' else 'NEGATIVE'}"
    return _massbank_accessions(q)


def massbank_record(accession: str) -> dict | None:
    """Compound detail for one MassBank accession.

    Deliberately the full record, not `/simple`: the simple form returns the
    compound block with `names: None`, `formula: ""` and `mass: 0`, which parses
    without error and silently yields nothing.
    """
    env = cached_get(f"{MASSBANK}/records/{quote(accession)}")
    payload = _json_or_none(env)
    return payload if isinstance(payload, dict) else None


def cache_stats() -> dict:
    files = list(common.CACHE_DIR.glob("*.json")) if common.CACHE_DIR.exists() else []
    ok = err = 0
    for p in files:
        try:
            if json.loads(p.read_text()).get("status") == 200:
                ok += 1
            else:
                err += 1
        except json.JSONDecodeError:
            err += 1
    return {"entries": len(files), "ok": ok, "non_200": err}
