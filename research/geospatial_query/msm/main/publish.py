"""Copy one geoquery run's results into the engcyc dataset layout, with ledger, gaps and README."""
import csv, hashlib, re, shutil, subprocess, tarfile
from datetime import date
from pathlib import Path

import pandas as pd

INTEGRATED = {"observations_long": "observations_long.parquet",
              "features_wide": "features_wide.parquet",
              "coverage": "coverage.csv"}
GAP_REASONS = {
    "not_applicable": "The source does not cover this AOI, for example a US-only source and a Canadian AOI. "
                      "geoquery did not query it.",
    "no_hits": "The source answered but holds no data for this AOI, for example no station or no image "
               "tile nearby.",
    "failed": "The source did not answer: it needs a login, its address is gone, or it timed out. "
              "A later run can succeed.",
}
# Caveats a reader of one source's table needs and the data cannot show.
NOTES = {"phac_wastewater": (
    "`phac_wastewater` loads are SARS-CoV-2 N2 gene copies/mL, the unit PHAC's own dashboard puts on "
    "this series (\"Viral load (copies/mL)\"). PHAC applies the same label to solid-fraction samples, "
    "which are often measured per gram. PHAC's open CSV ends 2024-06-28.")}


def _files(results: Path, type_name: str) -> list[Path]:
    return sorted(p.resolve() for p in (results / f"geoquery-{type_name}").glob("*"))


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def publish(results: Path, aoi_table: Path, out: Path, sources_tsv: Path, run: str, image: str):
    with open(sources_tsv) as fh:
        # a path segment holds only letters, digits and _ (engcyc LAYOUT.md)
        family = {r["source"]: re.sub(r"[^a-z0-9]+", "_", r["family"].lower()).strip("_")
                  for r in csv.DictReader(fh, delimiter="\t")}
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    ledger = []

    def record(rel: str, stem: str, product: str, source: str):
        dst = out / rel
        assert dst.stat().st_size > 0, f"zero-byte output {rel}"
        ledger.append(dict(path=rel, stem=stem, product=product, run=run, source=source,
                           bytes=dst.stat().st_size, sha256=_sha256(dst)))

    def put(src: Path, rel: str, stem: str, product: str):
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out / rel)
        record(rel, stem, product, src.name)

    put(aoi_table, f"aois/{aoi_table.name}", out.name, "aoi_table")
    (aois,) = _files(results, "aois")
    put(aois, "aois/aois.geojson", out.name, "aois")
    norm = pd.read_json(aois).get("features")
    pd.DataFrame([f["properties"] for f in norm]).to_csv(out / "aois.csv", index=False)
    record("aois.csv", out.name, "aois", aois.name)

    found, tables = {}, []
    for t in _files(results, "source_table"):
        d = pd.read_csv(t, dtype=str)
        src = d.source.iloc[0]
        found[src] = int((d.status == "found").sum())
        if found[src]:
            tables.append(f"{family[src]}/{src}.csv")
            put(t, tables[-1], src, src)
    for name, fname in INTEGRATED.items():
        (f,) = _files(results, name)
        put(f, f"integrated/{fname}", out.name, name)

    (g,) = _files(results, "gaps")
    gaps = pd.read_csv(g, dtype=str).rename(columns={"reason": "detail", "gap": "reason"})
    (out / "_logs" / "runs").mkdir(parents=True)
    gaps[["aoi", "source", "reason", "detail"]].to_csv(out / "_logs" / "gaps.csv", index=False)
    record("_logs/gaps.csv", out.name, "gaps", g.name)
    pd.DataFrame(GAP_REASONS.items(), columns=["reason", "description"]).to_csv(
        out / "_logs" / "gaps_descriptions.csv", index=False)
    record("_logs/gaps_descriptions.csv", out.name, "gaps", "publish.py")
    logs = (results / "_metadata" / "logs.latest").resolve()
    with tarfile.open(out / "_logs" / "runs" / f"{run}.tar.gz", "w:gz") as tar:
        tar.add(logs, arcname=run)
        tar.add(results / "_metadata" / "index.yml", arcname=f"{run}/index.yml")
    record(f"_logs/runs/{run}.tar.gz", run, "run_logs", "logs.latest")

    empty = sorted(s for s, n in found.items() if n == 0)
    counts = gaps.reason.value_counts()
    readme = [
        f"# {out.name}",
        "",
        f"Geospatial features for {len(norm)} areas of interest (AOIs) from {len(found)} public data sources. "
        f"geoquery produced it on {date.today()} (run `{run}`, image `{image}`).",
        "",
        "Start with `integrated/features_wide.parquet` for one row per AOI, or open a source's CSV below.",
        "",
        "## Files",
        "",
        "- `aois.csv`: the AOIs, one row each. `aois/` holds the AOI file as delivered and as normalised "
        "(GeoJSON, EPSG:4326).",
        "- `<family>/<source>.csv`: one table per source that found data, grouped by feature family.",
        "- `integrated/observations_long.parquet`: every value, one row each.",
        "- `integrated/features_wide.parquet`: one row per AOI, one column per feature. Values are text.",
        "- `integrated/coverage.csv`: one row per AOI, one column per source: `found`, `unavailable` or "
        "`not-attempted`.",
        "- `_logs/gaps.csv`: every AOI and source with no data, and why. `_logs/gaps_descriptions.csv` explains "
        "each reason.",
        "- `_logs/ledger.csv`: size and sha256 of every file. `_logs/runs/`: the pipeline's run logs.",
        "",
        "## Columns in the source tables",
        "",
        "- `aoi`, `source`, `feature`: what was measured, where, and by which source.",
        "- `value`: the value as text. `value_num`: the same value as a number, blank when it is not one.",
        "- `SI_unit`: blank for categories, names and flags.",
        "- `family`, `observation_type`: the feature family and how the source observes (satellite, survey, "
        "station and so on).",
        "- `time`: the date of the data. `licence`: the source's licence. `native_res_m`: the source's "
        "resolution in metres, or `vector`.",
        "- `status`, `reason`: `found`, or why the source has no data for that AOI.",
        "",
        "Each source returns its default moment, usually its latest data or a long-term average. Raster reads "
        "cap at 320 pixels a side, so a large AOI reads coarser than the source's native resolution.",
        "",
        "## Gaps",
        "",
        *[f"- `{k}` ({counts.get(k, 0)}): {v}" for k, v in GAP_REASONS.items()],
        "",
        *[f"{NOTES[s]}\n" for s in sorted(NOTES) if found.get(s)],
        "## Tables",
        "",
        *[f"- `{p}`" for p in sorted(tables)],
        "",
        f"Sources with no data for any AOI ({len(empty)}): {', '.join(empty) or 'none'}.",
        "",
    ]
    (out / "README.md").write_text("\n".join(readme))
    record("README.md", out.name, "readme", "publish.py")
    pd.DataFrame(ledger).to_csv(out / "_logs" / "ledger.csv", index=False)
    return dict(tables=len(tables), empty=len(empty), gaps=len(gaps))


def image_digest(uri: str) -> str:
    tag = uri.removeprefix("docker://")
    r = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", tag], capture_output=True, text=True)
    return f"{tag}@{r.stdout.strip()[:19]}" if r.returncode == 0 else tag
