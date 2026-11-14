"""Shared definitions for the May-2026 GUV imaging panels.

The condition grid and the bad-field-of-view exclusions were previously
duplicated across the panel scripts. They live here so the mosaic and the
quantification cannot silently disagree about which field of view is which.
"""

from pathlib import Path
import re


def resolve_scadc_data() -> Path:
    """This worktree's DVC-pinned run data. Raises rather than falling back:
    reading another scope's tree silently bypasses this scope's own pins."""
    for _p in Path(__file__).resolve().parents:
        _d = _p / "data" / "fabfos" / "runs"
        if _d.exists():
            return _d
    raise RuntimeError(
        f"no data/fabfos/runs found above {Path(__file__).resolve()} — fix the path "
        f"resolution here; do not restore a hardcoded cross-scope path."
    )


DATA = resolve_scadc_data() / "scadc_microscopy" / "vesicle_imaging_May_22_2026"
PANELS = Path(__file__).parent
RESULTS = resolve_scadc_data() / "scadc_vesicle_results"

# (strain, rep, toluene, exported folder). The .lif original of the same
# acquisition is rep{N}/<basename>.lif, where <basename> is the folder leaf.
GRID = [
    ("epi300", "r1", "notol", "exported rep 1/Epi_1"),
    ("epi300", "r2", "notol", "exported rep 2/ep2"),
    ("epi300", "r1", "tol",   "exported rep 1/Epi_tol_1"),
    ("epi300", "r2", "tol",   "exported rep 2/ep_tol_2"),
    ("pcc1",   "r1", "notol", "exported rep 1/pcc1_1"),
    ("pcc1",   "r2", "notol", "exported rep 2/pCC1_2"),
    ("pcc1",   "r1", "tol",   "exported rep 1/pcc1_tol_1"),
    ("pcc1",   "r2", "tol",   "exported rep 2/pCC1_tol_2"),
    ("clone1", "r1", "notol", "exported rep 1/clon1_2"),
    ("clone1", "r2", "notol", "exported rep 2/clon1_1"),
    ("clone1", "r1", "tol",   "exported rep 1/clon1_tol_2"),
    ("clone1", "r2", "tol",   "exported rep 2/clon1_tol_1"),
    ("clone2", "r1", "notol", "exported rep 1/clon2_"),
    ("clone2", "r2", "notol", "exported rep 2/clon2_3"),
    ("clone2", "r1", "tol",   "exported rep 1/clon2_tol_2"),
    ("clone2", "r2", "tol",   "exported rep 2/clon2_tol_3"),
]

# Acquired at zoom 0.75, not 2 — a different physical field of view, and not a
# sample. Excluded from every statistic; carried through geometry so the
# deviation is on the record rather than merely absent.
BACKGROUND = ["exported rep 1/Backgroundlif"]

STRAIN_LABEL = {"epi300": "EPI300", "pcc1": "PCC1", "clone1": "Clone1", "clone2": "Clone2"}
REP_LABEL = {"r1": "R1", "r2": "R2"}
TOL_LABEL = {"tol": "Tol+", "notol": "Tol-"}

STRAINS = ["epi300", "pcc1", "clone1", "clone2"]
TOL_LEVELS = ["notol", "tol"]

# Fields of view rejected by eye when the mosaic was built: out of focus, empty,
# or dominated by a single large aggregate. Assembled for picking presentable
# mosaic tiles, which is not automatically the right basis for quantification —
# the measurement scripts report counts both with and without it applied.
EXCLUDE = (
    {("exported rep 1/Epi_1", 12)}
    | {("exported rep 2/ep2", 6)}
    | {("exported rep 2/ep_tol_2", 6)}
    | {("exported rep 2/pCC1_2", 6)}
    | {("exported rep 2/pCC1_tol_2", 6)}
    | {("exported rep 2/clon1_1", s) for s in (1, 2, 3, 6, 7, 8, 9)}
    | {("exported rep 2/clon1_tol_1", 6)}
    | {("exported rep 2/clon2_3", 6)}
    | {("exported rep 2/clon2_tol_3", 7)}
)

SERIES_RE = re.compile(r"Series(\d+)_ch00\.tif$")


def lif_path(sub: str) -> Path:
    """Exported folder -> the .lif original it was exported from."""
    rep_dir, leaf = sub.split("/", 1)
    rep = "rep1" if rep_dir.endswith("1") else "rep2"
    return DATA / rep / f"{leaf}.lif"


def series_tifs(sub: str) -> list[tuple[int, Path]]:
    """(series index, ch00 tif) for one exported folder, in series order."""
    out = []
    folder = DATA / sub
    for s in sorted(p for p in folder.iterdir() if p.is_dir() and p.name.startswith("Series")):
        for t in s.glob("*_ch00.tif"):
            m = SERIES_RE.search(t.name)
            if m:
                out.append((int(m.group(1)), t))
    out.sort()
    return out


def series_properties_xml(sub: str, series_idx: int) -> Path:
    d = DATA / sub / f"Series{series_idx:03d}"
    return d / "MetaData" / f"Series{series_idx:03d}_Properties.xml"


def _um_per_px(background: bool) -> float:
    """The one pixel pitch shared by a class of acquisition, from measured
    metadata.

    Reads fov_geometry.csv rather than hardcoding a constant. Every field in a
    class was acquired at one setting, so a single number is correct — but it is
    checked here, so a future acquisition at a different zoom raises instead of
    silently rescaling every measurement. Run lif_geometry.py to produce the
    table.
    """
    import csv

    geom = RESULTS / "fov_geometry.csv"
    if not geom.exists():
        raise RuntimeError(f"{geom} missing — run lif_geometry.py first")
    with geom.open() as fh:
        rows = list(csv.DictReader(l for l in fh if not l.startswith("#")))
    want = "True" if background else "False"
    vals = {round(float(r["um_per_px_x"]), 6) for r in rows
            if r["is_background"] == want}
    kind = "background" if background else "sample"
    if not vals:
        raise RuntimeError(f"no {kind} rows in {geom}")
    if len(vals) != 1:
        raise RuntimeError(
            f"{kind} acquisitions span more than one pixel size: {sorted(vals)}. "
            f"Code that assumed a single scale must be revisited before it is "
            f"applied to this data.")
    return vals.pop()


def sample_um_per_px() -> float:
    """Pixel pitch of the 103 sample fields (63x, zoom 2)."""
    return _um_per_px(background=False)


def background_um_per_px() -> float:
    """Pixel pitch of the two Backgroundlif fields, acquired at zoom 0.75."""
    return _um_per_px(background=True)


def format_length(um: float) -> str:
    """A length as the shortest string that does not round away its own value."""
    if um < 1.0:
        return f"{um * 1000:.0f} nm"
    if um < 10.0:
        return f"{um:.2f} µm"
    return f"{um:.1f} µm"


def scale_bar(target_um: float, um_per_display_px: float) -> tuple[int, str]:
    """Pick the whole number of display pixels nearest `target_um`, then label
    it with what that run of pixels actually measures.

    The rounding has to land somewhere. Putting it in the *label* makes it
    visible and true. Putting it in the *bar* — deriving a pixel length from a
    round target and then printing the target — makes it invisible and wrong,
    which is what the earlier panels did: their bars read 20 µm, 2 µm and 100 nm
    while measuring 20.2 µm, 2.16 µm and 124 nm.

    Callers must paint exactly `n_px` columns. PIL's `draw.rectangle` is
    inclusive of *both* corners, so the span is [x1 - n_px + 1, x1] — not
    [x1 - n_px, x1], which paints one column too many and is where the 24% error
    on the 100 nm bar came from.
    """
    if um_per_display_px <= 0:
        raise ValueError(f"um_per_display_px must be positive, got {um_per_display_px}")
    n_px = max(1, round(target_um / um_per_display_px))
    return n_px, format_length(n_px * um_per_display_px)
