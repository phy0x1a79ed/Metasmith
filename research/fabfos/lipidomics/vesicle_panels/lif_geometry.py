"""T2 — per-series field-of-view geometry, read from the .lif originals.

Physical area is the denominator of a vesicle density, so it has to come from
the instrument rather than from a constant in a script. This reads the Leica
`.lif` files directly, emits one row per acquired series, and cross-checks every
row against the exported `MetaData/*_Properties.xml`. Any disagreement beyond
the exported file's own 2-decimal rounding is an error.

It also reconciles what was *acquired* against what was *exported*: the exported
tree is a curated subset, and a series that exists only in the .lif is reported
by name rather than silently dropped.

Writes fov_geometry.csv beside this file.
"""

import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from readlif.reader import LifFile

from vesicle_common import BACKGROUND, DATA, GRID, PANELS, RESULTS, lif_path, series_tifs

OUT = RESULTS / "fov_geometry.csv"

# The .lif header states lengths in metres; the exported XML states them in µm
# and rounds to 2 decimals. Compare in µm at that tolerance.
XML_TOL_UM = 0.01
M_TO_UM = 1e6


def lif_series_geometry(lif_file: Path) -> list[dict]:
    """One row per series in a .lif, from the embedded LMS XML header.

    Walks the Element tree rather than trusting a flat iter() over
    DimensionDescription, because a .lif holds one such block per series and a
    flat scan cannot tell you which series a block belongs to.
    """
    lif = LifFile(str(lif_file))
    by_name = {img.name: img for img in lif.get_iter_image()}

    rows = []
    for el in lif.xml_root.iter("Element"):
        desc = el.find("Data/Image/ImageDescription")
        if desc is None:
            continue
        name = el.get("Name")
        dims = {d.get("DimID"): d for d in desc.iter("DimensionDescription")}
        if "1" not in dims or "2" not in dims:
            continue

        nx = int(dims["1"].get("NumberOfElements"))
        ny = int(dims["2"].get("NumberOfElements"))
        # Leica reports the full extent (Length) separately from the element
        # count. Pixel pitch is extent/count; the exported XML's `Voxel` is this
        # value rounded to 2 dp, which is where the hardcoded 0.09 came from.
        len_x_um = float(dims["1"].get("Length")) * M_TO_UM
        len_y_um = float(dims["2"].get("Length")) * M_TO_UM
        um_px_x = len_x_um / nx
        um_px_y = len_y_um / ny

        settings = {}
        for atl in el.iter("ATLConfocalSettingDefinition"):
            settings = atl.attrib
            break

        img = by_name.get(name)
        rows.append({
            "lif": lif_file.name,
            "series": name,
            "px_x": nx,
            "px_y": ny,
            "um_per_px_x": round(um_px_x, 6),
            "um_per_px_y": round(um_px_y, 6),
            "width_um": round(len_x_um, 4),
            "height_um": round(len_y_um, 4),
            "fov_area_um2": round(len_x_um * len_y_um, 2),
            "objective": " ".join(settings.get("ObjectiveName", "").split()),
            "magnification": settings.get("Magnification", ""),
            "numerical_aperture": round(float(settings["NumericalAperture"]), 3)
                                  if settings.get("NumericalAperture") else "",
            "zoom": settings.get("Zoom", ""),
            "pinhole_um": round(float(settings["Pinhole"]) * M_TO_UM, 2)
                          if settings.get("Pinhole") else "",
            "bit_depth": img.bit_depth[0] if img else "",
            "channels": img.channels if img else "",
        })
    return rows


def exported_xml_geometry(xml_path: Path) -> dict:
    """Pixel counts and extents from an exported *_Properties.xml (µm)."""
    root = ET.parse(xml_path).getroot()
    dims = {d.get("DimID"): d for d in root.iter("DimensionDescription")}
    return {
        "px_x": int(dims["X"].get("NumberOfElements")),
        "px_y": int(dims["Y"].get("NumberOfElements")),
        "width_um": float(dims["X"].get("Length")),
        "height_um": float(dims["Y"].get("Length")),
        "voxel_um": float(dims["X"].get("Voxel")),
    }


def main() -> int:
    subs = [sub for *_, sub in GRID] + BACKGROUND
    rows = []
    problems = []

    for sub in subs:
        lf = lif_path(sub)
        if not lf.exists():
            problems.append(f"missing .lif for exported folder {sub!r}: {lf}")
            continue

        acquired = lif_series_geometry(lf)
        exported = {f"Series{idx:03d}": idx for idx, _ in series_tifs(sub)}

        acq_names = {r["series"] for r in acquired}
        only_lif = sorted(acq_names - exported.keys())
        only_exp = sorted(exported.keys() - acq_names)
        if only_lif:
            print(f"  NOTE {sub}: acquired but never exported: {', '.join(only_lif)}")
        if only_exp:
            problems.append(f"{sub}: exported series absent from {lf.name}: {only_exp}")

        for r in acquired:
            r["exported_dir"] = sub
            r["exported"] = r["series"] in exported
            r["is_background"] = sub in BACKGROUND
            if not r["exported"]:
                rows.append(r)
                continue

            idx = exported[r["series"]]
            xml = DATA / sub / f"Series{idx:03d}" / "MetaData" / f"Series{idx:03d}_Properties.xml"
            if not xml.exists():
                problems.append(f"{sub}/{r['series']}: no exported Properties.xml")
                rows.append(r)
                continue

            e = exported_xml_geometry(xml)
            for key in ("px_x", "px_y"):
                if r[key] != e[key]:
                    problems.append(
                        f"{sub}/{r['series']}: {key} .lif={r[key]} exported={e[key]}")
            for key in ("width_um", "height_um"):
                if abs(r[key] - e[key]) > XML_TOL_UM:
                    problems.append(
                        f"{sub}/{r['series']}: {key} .lif={r[key]:.4f} "
                        f"exported={e[key]:.2f} (tol {XML_TOL_UM})")
            r["exported_voxel_um"] = e["voxel_um"]
            rows.append(r)

        n_exp = sum(1 for r in acquired if r["series"] in exported)
        print(f"{sub:38s} {lf.name:22s} acquired={len(acquired):2d} exported={n_exp:2d}")

    if problems:
        print("\n!! geometry disagreements — refusing to write a table that "
              "would launder them:", file=sys.stderr)
        for p in problems:
            print(f"   {p}", file=sys.stderr)
        return 1

    fields = ["exported_dir", "lif", "series", "exported", "is_background",
              "px_x", "px_y", "um_per_px_x", "um_per_px_y", "exported_voxel_um",
              "width_um", "height_um", "fov_area_um2", "objective",
              "magnification", "numerical_aperture", "zoom", "pinhole_um",
              "bit_depth", "channels"]
    with OUT.open("w", newline="") as fh:
        fh.write(
            "# Per-series field-of-view geometry for the 22 May 2026 GUV imaging.\n"
            "# Read from the Leica .lif originals (data/fabfos/runs/scadc_microscopy/\n"
            "# vesicle_imaging_May_22_2026/rep{1,2}/*.lif) by research/fabfos/lipidomics/vesicle_panels/\n"
            "# lif_geometry.py, and cross-checked against every exported\n"
            "# MetaData/*_Properties.xml. um_per_px = Length/NumberOfElements;\n"
            "# exported_voxel_um is Leica's own 2-dp rounding of the same value.\n"
            "# fov_area_um2 = width_um * height_um, the denominator of density.\n"
            "# is_background marks the Backgroundlif frames: zoom 0.75, not samples.\n")
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    sample = [r for r in rows if not r["is_background"]]
    areas = {r["fov_area_um2"] for r in sample}
    px = {(r["um_per_px_x"], r["um_per_px_y"]) for r in sample}
    print(f"\nwrote {OUT}  ({len(rows)} series, {len(sample)} sample)")
    print(f"  distinct sample FOV areas : {sorted(areas)}")
    print(f"  distinct sample µm/px     : {sorted(px)}")
    print(f"  zooms                     : {sorted({r['zoom'] for r in rows})}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
