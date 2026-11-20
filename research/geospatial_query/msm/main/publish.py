"""Copy one geoquery run's results into the engcyc dataset layout, with ledger, gaps and README."""
import csv, hashlib, re, shutil, subprocess, tarfile
from datetime import date
from pathlib import Path

import pandas as pd

INTEGRATED = {"observations_long": "observations_long.parquet",
              "features_wide": "features_wide.parquet",
              "coverage": "coverage.tsv"}


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
    tsv = out / "aois.tsv"
    pd.DataFrame([f["properties"] for f in norm]).to_csv(tsv, sep="\t", index=False)
    record("aois.tsv", out.name, "aois", aois.name)

    found = {}
    for t in _files(results, "source_table"):
        d = pd.read_csv(t, sep="\t", dtype=str)
        src = d.source.iloc[0]
        found[src] = int((d.status == "found").sum())
        if found[src]:
            put(t, f"{family[src]}/{src}.tsv", src, src)
    for name, fname in INTEGRATED.items():
        (f,) = _files(results, name)
        put(f, f"integrated/{fname}", out.name, name)

    (g,) = _files(results, "gaps")
    gaps = pd.read_csv(g, sep="\t", dtype=str)
    gaps = gaps.rename(columns={"source": "product", "aoi": "stem", "reason": "detail", "gap": "reason"})
    (out / "_logs" / "runs").mkdir(parents=True)
    gaps[["product", "stem", "reason", "detail"]].to_csv(out / "_logs" / "gaps.tsv", sep="\t", index=False)
    record("_logs/gaps.tsv", out.name, "gaps", g.name)
    logs = (results / "_metadata" / "logs.latest").resolve()
    with tarfile.open(out / "_logs" / "runs" / f"{run}.tar.gz", "w:gz") as tar:
        tar.add(logs, arcname=run)
        tar.add(results / "_metadata" / "index.yml", arcname=f"{run}/index.yml")
    record(f"_logs/runs/{run}.tar.gz", run, "run_logs", "logs.latest")

    tables = sorted(r["path"] for r in ledger if r["path"].endswith(".tsv") and "/" in r["path"]
                    and not r["path"].startswith(("integrated", "aois", "_logs")))
    empty = sorted(s for s, n in found.items() if n == 0)
    readme = [
        f"# {out.name}",
        "",
        f"Geospatial features for {len(norm)} areas of interest, pulled from {len(found)} public sources "
        f"by the geoquery metasmith DAG (run `{run}`, {date.today()}, image `{image}`).",
        "",
        "## Layout",
        "",
        "- `aois.tsv`, `aois/`: the AOI table as delivered and as normalised (EPSG:4326, slugged `aoi_id`).",
        "- `<family>/<source>.tsv`: one table per source that found data. Rows are AOI × feature, plus one "
        "status row per AOI the source did not cover.",
        "- `integrated/observations_long.parquet`: every found value, one row each.",
        "- `integrated/features_wide.parquet`: AOI × feature, values as text.",
        "- `integrated/coverage.tsv`: AOI × source status (`found`, `unavailable`, `not-attempted`).",
        "- `_logs/gaps.tsv`: every AOI × source pair that is not `found`. `reason` is `no_hits`, `failed` or "
        "`not_applicable`; `detail` is the adapter's message.",
        "- `_logs/ledger.tsv`: bytes and sha256 of every published file. `_logs/runs/`: the metasmith run logs.",
        "",
        "## Columns",
        "",
        "`aoi`, `source`, `observation_type`, `time`, `feature`, `family`, `value` (text), `value_num` "
        "(numeric when parseable), `SI_unit` (blank for categorical or text features), `licence`, "
        "`native_res_m`, `status`, `reason`.",
        "",
        "Each source is asked for its default moment, usually its latest data or a climatology. Raster reads "
        "cap at 320 px a side, so large AOIs read coarser than the source's native resolution.",
        "",
        "## Tables",
        "",
        *[f"- `{p}`" for p in tables],
        "",
        f"Sources with no data for any AOI ({len(empty)}): {', '.join(empty) or 'none'}.",
        "",
    ]
    (out / "README.md").write_text("\n".join(readme))
    record("README.md", out.name, "readme", "publish.py")
    pd.DataFrame(ledger).to_csv(out / "_logs" / "ledger.tsv", sep="\t", index=False)
    return dict(tables=len(tables), empty=len(empty), gaps=len(gaps))


def image_digest(uri: str) -> str:
    tag = uri.removeprefix("docker://")
    r = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", tag], capture_output=True, text=True)
    return f"{tag}@{r.stdout.strip()[:19]}" if r.returncode == 0 else tag
