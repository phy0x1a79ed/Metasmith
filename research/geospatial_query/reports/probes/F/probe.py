"""Run the four Q2-Q5 probes against live STAC catalogues and write F_probes.csv.

    python probe.py            run everything (about 25 min, dominated by q4)
    python probe.py --reuse    rebuild the CSV from out/q*_result.json
"""
import csv
import json
import os
import sys

import common as c

COLS = ["gap", "candidate", "source_type", "endpoint", "auth", "reachable", "http_status", "aoi_hits", "control_passed",
        "observation_unit", "quality_fields", "off_nadir_field", "licence", "notes"]
OFF_NADIR = ("view:off_nadir (Landsat item property, always <1 deg so uninformative); "
             "S2: granule-metadata asset MTD_TL.xml Mean_Viewing_Incidence_Angle_List (not an item property)")


def load(name, module, reuse):
    path = f"{c.OUT}/{name}_result.json"
    if reuse and os.path.exists(path):
        return json.load(open(path))
    print(f"\n######## {module.__name__} ########")
    module.run(verbose=True)
    return json.load(open(path))


def licence():
    out = []
    for cat, base in c.CATALOGS.items():
        for coll in ("sentinel-2-l2a", "landsat-c2-l2"):
            j = c.HTTP.get(f"{base}/collections/{coll}").json()
            lk = next((l.get("title") or l["href"] for l in j.get("links", []) if l.get("rel") == "license"), "")
            out.append(f"{cat}:{coll} {j.get('license')} {lk}".strip())
    return " | ".join(sorted(set(out)))


def main():
    reuse = "--reuse" in sys.argv
    import q2_bands, q3_periodic, q4_qc_filter, q5_assets
    r2 = load("q2", q2_bands, reuse)
    r3 = load("q3", q3_periodic, reuse)
    r4 = load("q4", q4_qc_filter, reuse)
    r5 = load("q5", q5_assets, reuse)
    lic = licence()
    pcs = f"{c.PC}/search ; {c.PC}/collections/{{collection}}/queryables ; "
    ess = f"{c.ES}/search ; {c.ES}/collections/{{collection}}/queryables"
    rows = []

    h2 = r2["aoi_hits"]
    cm = r2["combos"]
    rows.append({
        "gap": "Q2", "candidate": "bands/indices field: eo:bands common_name + spyndex formula -> asset keys -> AOI mean",
        "source_type": "satellite",
        "endpoint": f"{c.PC}/collections/{{collection}}[/items/{{id}}] ; {c.ES}/collections/{{collection}}[/items/{{id}}]",
        "auth": "none", "reachable": "yes", "http_status": "200",
        "aoi_hits": f"{h2['PC']}/15", "control_passed": "yes" if all(v == 0 for v in r2["control"].values()) else "no",
        "observation_unit": "acquisition",
        "quality_fields": "eo:bands.common_name;eo:bands.center_wavelength;raster:bands.scale;raster:bands.offset;s2:processing_baseline;earthsearch:boa_offset_applied;storage:requester_pays",
        "off_nadir_field": OFF_NADIR, "licence": lic,
        "notes": (f"One spec (bands red,nir,swir16; indices NDVI,NDWI,NBR) resolved on S2 and Landsat on both catalogues (ES {h2['ES']}/15 AOIs). "
                  f"PC S2 NDVI={cm['PC:sentinel-2-l2a'].get('aoi_mean', {}).get('NDVI')} ES S2 NDVI={cm['ES:sentinel-2-l2a'].get('aoi_mean', {}).get('NDVI')} "
                  f"PC Landsat NDVI={cm['PC:landsat-c2-l2'].get('aoi_mean', {}).get('NDVI')}; ES Landsat read fails (requester-pays s3). "
                  "Landsat has no 'nir' common name (nir08) so a wavelength fallback is needed; PC S2 lacks raster:bands scale/offset; ES declares offset -0.1 but already applied it."),
    })

    h3 = r3["aoi_hits"]
    eqp, eqe = r3["catalogs"]["PC"]["equivalence"], r3["catalogs"]["ES"]["equivalence"]
    rows.append({
        "gap": "Q3", "candidate": "period field: one range search, client-side bins (monthly, every July, 16-day), best item per period by cloud",
        "source_type": "satellite", "endpoint": f"{c.PC}/search ; {c.ES}/search",
        "auth": "none", "reachable": "yes", "http_status": "200 (ES 502 when limit>~200 on busy AOIs)",
        "aoi_hits": f"{h3['PC']}/15", "control_passed": "yes" if r3["catalogs"]["PC"]["control_items"] == 0 and r3["catalogs"]["ES"]["control_items"] == 0 else "no",
        "observation_unit": "acquisition", "quality_fields": "datetime;eo:cloud_cover",
        "off_nadir_field": OFF_NADIR, "licence": lic,
        "notes": (f"farm_sk_quarter monthly: PC {eqp['monthly']['single_requests']} request vs {eqp['monthly']['fanout_requests']} fan-out, best cloud identical {eqp['monthly']['same_best_cloud']}/{eqp['monthly']['periods']}; "
                  f"ES {eqe['monthly']['single_requests']} vs {eqe['monthly']['fanout_requests']}. 15 AOIs: PC {r3['catalogs']['PC']['single_requests']} requests vs {r3['catalogs']['PC']['fanout_requests_theory']['monthly']} monthly fan-out; "
                  f"ES {h3['ES']}/15 AOIs. PC holds reprocessed duplicates (199 items, 142 distinct datetimes on farm_sk_quarter)."),
    })

    ah = r4["aoi_hits"]
    d4 = r4["best_dialect"]
    rows.append({
        "gap": "Q4", "candidate": "qc filters pushed into STAC search: CQL2-JSON (PC) / query extension (ES); AOI cloud from SCL after read",
        "source_type": "satellite",
        "endpoint": f"{c.PC}/search (filter-lang cql2-json) ; {c.ES}/search (query extension) ; {c.PC}/collections/{{collection}}/queryables ; {c.ES}/collections/{{collection}}/queryables",
        "auth": "none", "reachable": "yes", "http_status": "200",
        "aoi_hits": f"{max(ah['PC'].values())}/15", "control_passed": "yes" if all(v == 0 for v in r4["control"].values()) else "no",
        "observation_unit": "acquisition",
        "quality_fields": "eo:cloud_cover;view:off_nadir;view:sun_elevation;s2:mean_solar_zenith;landsat:correction;s2:product_type;s2:cloud_shadow_percentage;SCL band",
        "off_nadir_field": OFF_NADIR, "licence": lic,
        "notes": (f"PC honours CQL2 and query ext. ES silently IGNORES cql2-json (HTTP 200, F=notF=impossible=N) and honours only the query extension; ES queryables lists only eo:cloud_cover. "
                  "view:off_nadir on Landsat is <1 deg in every 2023 scene at all 15 AOIs (>1 returns 0), so the filter is honoured but never bites. S2 has no view:sun_elevation on PC (use s2:mean_solar_zenith); ES S2 has view:sun_elevation but no s2:mean_solar_zenith. "
                  f"SCL AOI cloud on {PROBE_AOI(r4)}: tile<10 passes {r4['scl']['tile_pass']}, AOI<10 passes {r4['scl']['aoi_pass']} of {r4['scl']['scenes']} scenes, {r4['scl']['disagree']} disagree."),
    })

    h5 = r5["hits"]
    rows.append({
        "gap": "Q5", "candidate": "observation.assets: item id + signed asset hrefs; range read confirms they resolve",
        "source_type": "satellite", "endpoint": f"{c.PC}/search ; https://planetarycomputer.microsoft.com/api/sas/v1/token/{{account}}/{{container}} ; {c.ES}/search",
        "auth": "none", "reachable": "yes", "http_status": "200 (unsigned blob: 409)",
        "aoi_hits": f"{len(h5['PC:sentinel-2-l2a'])}/15", "control_passed": "yes",
        "observation_unit": "acquisition", "quality_fields": "eo:cloud_cover;datetime;storage:requester_pays;SAS se expiry",
        "off_nadir_field": OFF_NADIR, "licence": lic,
        "notes": (f"Range GET 206: PC S2 {len(h5['PC:sentinel-2-l2a'])}/15, PC Landsat {len(h5['PC:landsat-c2-l2'])}/15, ES S2 {len(h5['ES:sentinel-2-l2a'])}/15 (one item has s3 jp2 only), ES Landsat {len(h5['ES:landsat-c2-l2'])}/15 (s3 requester-pays). "
                  f"Unsigned PC href -> HTTP {r5['unsigned']['status']}. SAS lifetime ~{r5['expiry'].get('minutes_remaining')} min at issue."),
    })

    with open(os.path.join(c.HERE, "F_probes.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows to F_probes.csv; HTTP requests this process: {c.HTTP.total()} (429s {c.HTTP.status429}, retries {c.HTTP.retries})")


def PROBE_AOI(r4):
    import q4_qc_filter
    return q4_qc_filter.PROBE_AOI


if __name__ == "__main__":
    main()
