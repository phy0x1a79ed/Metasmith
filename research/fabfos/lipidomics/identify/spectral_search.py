"""T3 -- search the consensus MS/MS against libraries the facility did not use.

The facility already searched Bruker MetaboBASE, NIST23, an HMDB target list and
the MS-DIAL LipidBlast VS69 atlas, and two in-house re-runs against that same
atlas returned nothing. Re-running them is the failure mode this lane exists to
avoid. What is new here is reachable only over the network:

  gnpslibrary     the GNPS community reference library -- names a match.
  repository index a searchable index over public MassIVE data. A hit there does
                  not name the molecule; it says the same spectrum has been seen
                  in other public experiments, which is occurrence evidence and
                  is reported as such, never as an identification.
  MassBank Europe a second curated library, live at v2025.12.1.

FASST is asynchronous -- submit returns a task id, results are collected from a
separate endpoint -- so every spectrum is submitted first and polled after.

Run:  mamba run -n p312 python -m identify.spectral_search   (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common, webapi  # noqa: E402

LIBRARIES = [
    ("gnpslibrary", "fasst_gnpslibrary", True),
    ("metabolomicspanrepo_index_latest", "fasst_repository", False),
]
COSINE_THRESHOLD = 0.6
MAX_HITS_NAMED = 25
MAX_HITS_OCCURRENCE = 10
# A cosine computed over three or four shared fragments is not evidence -- with
# a 0.05 Da tolerance, unrelated lipids share that many peaks by chance. The
# observed distribution here is overwhelmingly 3-4 matching peaks, so without
# this floor the table would fill with thousands of coincidences wearing high
# cosines. Six is the conventional minimum for a credible library match.
MIN_MATCHED_PEAKS = 6
MASSBANK_MAX_RECORDS = 12


def _formulas_for_feature(fid: str) -> list[str]:
    """The formulas a curated database already supported for this feature."""
    p = common.IDENT_DIR / "formula_support_summary.csv"
    if not p.exists():
        return []
    df = pd.read_csv(p).set_index("feature_id")
    if fid not in df.index:
        return []
    val = df.loc[fid, "supported"]
    return [f for f in str(val).split(";") if f and f != "nan"][:3]
POLL_SECONDS = 5
POLL_LIMIT = 120   # each round already costs ~18 s of polite polling across the batch


def _load() -> tuple[pd.DataFrame, dict]:
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv").set_index("feature_id")
    path = common.SPECTRA_DIR / "consensus_ms2.json"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing -- run identify.extract_spectra under the `lipidomics` env first"
        )
    return manifest, json.loads(path.read_text())


def _submit(manifest: pd.DataFrame, spectra: dict, fid: str, tag: str,
            library: str, *, force: bool) -> str | None:
    f = manifest.loc[fid]
    return webapi.fasst_submit(
        spectra[fid]["peaks"], float(f.mz), -1 if f.polarity == "neg" else 1,
        library=library, cosine_threshold=COSINE_THRESHOLD, force=force,
    )


def submit_all(manifest: pd.DataFrame, spectra: dict) -> dict:
    tasks = {}
    for fid in sorted(spectra):
        for library, tag, _named in LIBRARIES:
            tid = _submit(manifest, spectra, fid, tag, library, force=False)
            tasks[(fid, tag)] = {"task_id": tid, "library": library, "resubmitted": False}
            print(f"  submit {fid} -> {library:<34} task={tid}")
    return tasks


def collect(tasks: dict, manifest: pd.DataFrame, spectra: dict) -> dict:
    """Poll each task to completion; return raw result payloads.

    Task ids expire server-side, and submissions are cached on disk, so a re-run
    will hand back an id the API has forgotten. A NOT_FOUND is therefore treated
    as "re-submit once", not as an empty result -- otherwise a cached run would
    silently report no spectral hits.
    """
    results = {}
    pending = {k: v for k, v in tasks.items() if v["task_id"]}
    for key, v in tasks.items():
        if not v["task_id"]:
            results[key] = None
            print(f"  SUBMIT FAILED: {key}")

    for attempt in range(POLL_LIMIT):
        if not pending:
            break
        done = []
        for key, v in pending.items():
            status = webapi.fasst_status(v["task_id"])
            if status == "NOT_FOUND" and not v["resubmitted"]:
                fid, tag = key
                v["task_id"] = _submit(manifest, spectra, fid, tag, v["library"], force=True)
                v["resubmitted"] = True
                print(f"  re-submitted (expired id) {fid} {tag} -> {v['task_id']}")
                continue
            if status in ("PENDING", "STARTED", "RETRY", None):
                continue
            results[key] = webapi.fasst_result(v["task_id"], force=True)
            done.append(key)
        for k in done:
            pending.pop(k)
        if pending:
            print(f"  poll {attempt + 1}: {len(pending)} still running")
            time.sleep(POLL_SECONDS)

    for key in pending:
        results[key] = None
        print(f"  TIMED OUT: {key}")
    return results


def _hits(payload) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, dict):
        for k in ("results", "hits", "data"):
            if isinstance(payload.get(k), list):
                return payload[k]
        return []
    return payload if isinstance(payload, list) else []


def run(from_raw: bool = False) -> pd.DataFrame:
    common.ensure_dirs()
    manifest, spectra = _load()
    print(f"consensus spectra to search: {len(spectra)}")

    raw_path = common.IDENT_DIR / "fasst_raw.json"
    if from_raw and raw_path.exists():
        # Re-parse the stored payloads. Fixing how a response is read should not
        # cost the service another 52 searches.
        blob = json.loads(raw_path.read_text())
        results = {tuple(k.split("|", 1)): v for k, v in blob.items()}
        print(f"re-parsing {len(results)} stored payloads ({raw_path})")
    else:
        tasks = submit_all(manifest, spectra)
        results = collect(tasks, manifest, spectra)
        # Kept whole: truncating the string would leave invalid JSON behind, and
        # the raw payload is the audit trail for every call made here.
        raw_path.write_text(
            json.dumps({f"{k[0]}|{k[1]}": v for k, v in results.items()}, indent=1)
        )

    named_tag = {tag: named for _, tag, named in LIBRARIES}
    rows, per_feature, truncated = [], {}, []
    weak = 0
    for (fid, tag), payload in sorted(results.items()):
        raw_hits = _hits(payload)
        per_feature[fid] = per_feature.get(fid, 0) + len(raw_hits)

        # Filter BEFORE capping. Capping first would rank by cosine, and a cosine
        # over three shared peaks outranks a real match over twelve -- the cap
        # would then discard exactly the hits worth keeping.
        strong = [
            h for h in raw_hits
            if h.get("Matching Peaks") is not None
            and int(h["Matching Peaks"]) >= MIN_MATCHED_PEAKS
        ]
        weak += len(raw_hits) - len(strong)

        # A repository-wide search can still return many near-identical hits;
        # they are occurrence evidence, so a capped sample says the same thing.
        cap = MAX_HITS_NAMED if named_tag[tag] else MAX_HITS_OCCURRENCE
        hits = sorted(
            strong,
            key=lambda h: (-int(h["Matching Peaks"]), -float(h.get("Cosine") or 0)),
        )
        if len(hits) > cap:
            truncated.append(f"{fid}/{tag}: {len(strong)} strong hits, kept {cap}")
            hits = hits[:cap]

        for h in hits:
            name = (h.get("CompoundName") or h.get("Compound_Name") or "").strip()
            cosine = h.get("Cosine")
            matched = h.get("Matching Peaks")
            usi = h.get("USI") or ""
            accession = h.get("GNPSLibraryAccession") or ""
            dataset = h.get("Dataset") or ""

            # GNPS "Suspect related to ..." entries are propagated analog
            # annotations carrying an explicit delta m/z, not measurements of
            # this compound. They are kept, but never as an identification.
            is_suspect = name.lower().startswith("suspect related to")

            if not named_tag[tag]:
                name = name or f"(unnamed public spectrum, {dataset})"
            if not name:
                continue

            note = "library spectral match"
            source = tag
            if is_suspect:
                note = ("GNPS analog/suspect entry -- a propagated annotation with a "
                        "mass shift, not a match to this compound")
                source = "fasst_gnps_analog"
            elif not named_tag[tag]:
                note = "public-repository occurrence, not an identification"

            rows.append(
                common.candidate_row(
                    fid, source,
                    candidate_name=name,
                    ms2_cosine=None if cosine is None else round(float(cosine), 4),
                    ms2_matched_peaks=int(matched),
                    external_ids=";".join(
                        p for p in (f"USI:{usi}" if usi else "",
                                    f"GNPS:{accession}" if accession else "",
                                    f"Dataset:{dataset}" if dataset else "") if p
                    ) or None,
                    notes=note,
                )
            )

    # MassBank. Its peak_list similarity endpoint returns 502, so the spectral
    # comparison it advertises is not available; what works is formula and
    # neutral-mass lookup. A hit therefore says "a curated reference spectrum
    # exists for this composition", which is a coverage statement, not a match.
    mb_rows = 0
    for fid in sorted(spectra):
        f = manifest.loc[fid]
        accessions = list(dict.fromkeys(
            webapi.massbank_by_mass(float(f.neutral_mass), 0.02, f.polarity)
            + [a for fml in _formulas_for_feature(fid)
               for a in webapi.massbank_by_formula(fml)]
        ))[:MASSBANK_MAX_RECORDS]
        for acc in accessions:
            rec = webapi.massbank_record(acc)
            if not rec:
                continue
            comp = rec.get("compound") or {}
            names = comp.get("names") or []
            if not names:
                continue
            mb_rows += 1
            rows.append(
                common.candidate_row(
                    fid, "massbank_reference",
                    candidate_name=names[0],
                    formula=comp.get("formula"),
                    exactmass=comp.get("mass"),
                    external_ids=f"MassBank:{acc}",
                    notes="a MassBank reference spectrum exists for this composition "
                          "(no spectral comparison -- the similarity endpoint is down)",
                )
            )

    out = pd.DataFrame(rows, columns=common.CANDIDATE_COLS)
    out.to_csv(common.IDENT_DIR / "candidates_spectral.csv", index=False)

    print("\nSpectral search")
    print(f"  spectra searched          {len(spectra)}")
    print(f"  hits discarded < {MIN_MATCHED_PEAKS} peaks {weak}")
    print(f"  FASST hit rows kept       {len(out) - mb_rows}")
    print(f"  MassBank precursor rows   {mb_rows}")
    print(f"  features with any hit     {out.feature_id.nunique()}/{len(spectra)}")
    if truncated:
        print(f"  capped result sets        {len(truncated)}")
        for t in truncated[:10]:
            print(f"    {t}")
    print(f"  cache                     {webapi.cache_stats()}")
    if out.empty:
        print("\n  NO SPECTRAL MATCHES. This is a reportable result, not a failure:")
        print("  bacterial phospholipid coverage in public libraries is poor and")
        print("  unmeasured, which is precisely why these features are dark.")
    return out


if __name__ == "__main__":
    run(from_raw="--from-raw" in sys.argv)
