"""T4 -- publish the graded identifications into the figure tree.

One figure, because there is one question: which evidence source reached which
feature, and how much confidence did it earn. That is a presence matrix with an
ordinal fill, not a bar chart of counts -- the counts are a caption, the coverage
pattern is the finding.

Confidence is ordered (L2 stronger than L5), so the fill is a single-hue ordinal
ramp, darkest = strongest, with a neutral for "no candidate". Colours are the
documented pre-validated blue steps; nothing here invents a hue.

Run:  mamba run -n p312 python -m identify.publish              (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common  # noqa: E402

# Ordinal ramp, darkest = strongest evidence. Steps 700/500/350/250 of the
# documented blue ramp; 250 is the light-mode ordinal floor.
LEVEL_COLOR = {
    "L2": "#0d366b",
    "L3": "#256abf",
    "L4": "#5598e7",
    "L5": "#86b6ef",
    "analog": "#a9a8a3",
    "occurrence": "#c9c8c3",
    "none": "#f0efec",
}
LEVEL_LABEL = {
    "L2": "L2  library MS/MS match",
    "L3": "L3  database compound, isomers unresolved",
    "L4": "L4  unequivocal formula only",
    "L5": "L5  exact mass only",
    "analog": "analog entry — a related compound, not this one",
    "occurrence": "seen in public data, unnamed",
    "none": "no candidate",
}
SOURCE_ORDER = [
    ("fasst_gnpslibrary", "GNPS\nlibrary"),
    ("fasst_gnps_analog", "GNPS\nanalog"),
    ("fasst_repository", "public\nrepository"),
    ("massbank_reference", "MassBank\nreference"),
    ("lipidmaps_formula", "LIPID MAPS\nformula"),
    ("refmet_formula", "RefMet\nformula"),
    ("refmet_mass", "RefMet\nmass"),
    ("formula_enumeration", "formula\nonly"),
]
INK, INK_2, GRID = "#0b0b0b", "#52514e", "#dedcd6"
SURFACE = "#fcfcfb"
LEVEL_RANK = {
    "L2": 0, "L3": 1, "L4": 2, "L5": 3, "analog": 4, "occurrence": 5, "none": 6,
}


ACYL_COLOR = "#eb6834"   # a different hue because it is a different kind of
                         # evidence, not another step on the confidence ramp


def _figure(graded: pd.DataFrame, best: pd.DataFrame, acyl: dict[str, str],
            out_stem: Path) -> None:
    best = best.copy()
    best["_r"] = best.best_level.map(LEVEL_RANK)
    best = best.sort_values(["_r", "mz"]).reset_index(drop=True)
    order = list(best.feature_id)

    # Best level each source reached, per feature.
    cell: dict[tuple[str, str], str] = {}
    for (fid, src), grp in graded.groupby(["feature_id", "evidence_source"]):
        if src == "none":
            continue
        lvl = min(grp.confidence_level, key=lambda x: LEVEL_RANK.get(x, 9))
        cell[(fid, src)] = lvl

    fig, ax = plt.subplots(figsize=(12.4, 9.4), dpi=300)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    n_src = len(SOURCE_ORDER)
    for yi, fid in enumerate(order):
        for xi, (src, _) in enumerate(SOURCE_ORDER):
            lvl = cell.get((fid, src))
            colour = LEVEL_COLOR.get(lvl, LEVEL_COLOR["none"])
            ax.add_patch(
                plt.Rectangle(
                    (xi + 0.06, yi + 0.06), 0.88, 0.88,
                    facecolor=colour, edgecolor=SURFACE, linewidth=2,
                )
            )
        # The acyl-chain column sits apart, after a gap: it does not come from a
        # library at all, and it is the only evidence here that survives the
        # libraries not holding these lipids.
        chains = acyl.get(fid)
        ax.add_patch(
            plt.Rectangle(
                (n_src + 0.36, yi + 0.06), 0.88, 0.88,
                facecolor=ACYL_COLOR if chains else LEVEL_COLOR["none"],
                edgecolor=SURFACE, linewidth=2,
            )
        )
        if chains:
            ax.text(n_src + 1.36, yi + 0.5, chains, va="center", ha="left",
                    fontsize=6.4, color=INK_2, family="monospace")

    ax.set_xlim(0, n_src + 3.9)
    ax.set_ylim(len(order), 0)
    ax.set_xticks([i + 0.5 for i in range(n_src)] + [n_src + 0.8])
    ax.set_xticklabels([lab for _, lab in SOURCE_ORDER] + ["acyl chains\nfrom MS/MS"],
                       fontsize=8, color=INK_2)
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")

    labels = []
    for _, r in best.iterrows():
        star = "*" if r.is_control else " "
        labels.append(f"{r.feature_id}{star} {r.mz:9.4f} @ {r.rt:4.2f}")
    ax.set_yticks([i + 0.5 for i in range(len(order))])
    ax.set_yticklabels(labels, fontsize=7.2, family="monospace", color=INK)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)

    counts = best.best_level.value_counts()
    ax.set_title(
        "Evidence reaching each clone-response feature\n"
        f"{int(counts.get('L2', 0))} reach L2 · {int(counts.get('L3', 0))} L3 · "
        f"{int(counts.get('L4', 0))} L4 · {int(counts.get('L5', 0))} mass-only · "
        f"{int(counts.get('none', 0))} nothing — "
        f"the community libraries name none of them",
        fontsize=11, color=INK, pad=34, loc="left",
    )

    present = [k for k in ("L2", "L3", "L4", "L5", "analog", "occurrence", "none")
               if (best.best_level == k).any() or any(v == k for v in cell.values())]
    handles = [Patch(facecolor=LEVEL_COLOR[k], label=LEVEL_LABEL[k]) for k in present]
    handles.append(Patch(facecolor=ACYL_COLOR,
                         label="acyl chains read off the feature's own MS/MS"))
    ax.legend(
        handles=handles, loc="upper left", bbox_to_anchor=(0.0, -0.035),
        frameon=False, fontsize=8, ncol=2, labelcolor=INK_2,
    )
    fig.text(
        0.01, 0.005,
        "* positive control: feature already identified by the facility, run blind through this pipeline.",
        fontsize=7, color=INK_2,
    )
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    for ext in ("png", "svg"):
        fig.savefig(out_stem.with_suffix(f".{ext}"), facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def _n_feat(graded: pd.DataFrame, source: str) -> int:
    return int(graded[graded.evidence_source == source].feature_id.nunique())


def _readme(graded: pd.DataFrame, best: pd.DataFrame, manifest: pd.DataFrame) -> str:
    c = best.best_level.value_counts()
    n = len(best)
    n_id = int(sum(c.get(k, 0) for k in ("L2", "L3", "L4", "L5")))
    dark = best[best.best_level == "none"]
    was_named = int(best.was_already_named.sum())
    ms2 = int(manifest.has_msms.sum())
    spectra = common.SPECTRA_DIR / "consensus_ms2.json"
    n_spectra = 0
    if spectra.exists():
        import json
        n_spectra = len(json.loads(spectra.read_text()))

    controls = []
    for _, r in best[best.is_control].iterrows():
        truth = common.CONTROL_FEATURES[r.feature_id]
        line = (
            f"- `{r.feature_id}` — expected **{truth['class']}**, recovered "
            f"`{r.lipid_class}` at **{r.best_level}** via {r.evidence_source}."
        )
        if isinstance(r.acyl_chains_observed, str) and r.acyl_chains_observed:
            line += f" Acyl chains read off its own MS/MS: **{r.acyl_chains_observed}**."
        controls.append(line)

    acyl = best[best.acyl_chains_observed.notna()] if "acyl_chains_observed" in best else best.iloc[:0]

    return f"""# Identification of the clone-response features

Candidate identifications for the {n} features that came out of the
clone-response analysis next door in `05_clone_response`. Of those, {was_named}
arrived already named by the facility; the other {n - was_named} were m/z and
retention time only.

## What this is

Two tables and one figure.

- `clone_response_identification_candidates.csv` — every candidate for every
  feature, one row per candidate, ranked within the feature and graded.
- `clone_response_best_call_per_feature.csv` — one row per feature: the best
  call and how much evidence stands behind it.
- `clone_response_acyl_fragments.csv` — the fatty-acyl chains read directly off
  the negative-mode MS/MS.
- `../05_clone_response/clone_response_storey_hits_identified.csv` — the
  statistics table next door with these identifications joined on, so the result
  and the chemistry read together. The original hits file is left as it was.
- `01_evidence_per_feature` — which source reached which feature, coloured by
  the confidence that source earned.

## Acyl chains, read off the spectra

{len(acyl)} of the {int((best.adduct.astype(str).str.endswith('-')).sum())}
negative-mode features give up fatty-acyl carboxylate anions in their own MS/MS.
This is the most useful evidence in the whole folder, because it does not depend
on any library holding the intact lipid — and the libraries demonstrably do not.
It is what distinguishes among the isomers sitting under an L3 call: a mass
search says "some C40H71O10P exists"; the fragments say which chains are on it.

It is reported beside the grade, never folded into it. A carboxylate anion
identifies a chain, not the molecule that shed it, and a co-isolated precursor
can donate fragments it was never part of.

**One ambiguity is flagged, not resolved.** A chain marked `*` (e.g. `17:1*`) is
mass-identical to the cyclopropane-containing saturated chain of the same carbon
number. E. coli genuinely makes 17:0-cyclo and 19:0-cyclo, so a `17:1*` here is
at least as likely to be 17:0-cyclo. Mass cannot separate them.

## The headline, stated plainly

| level | meaning | features |
|---|---|---|
| L2 | library MS/MS match, or the facility's own MS/MS hit where the candidate's class agrees with it — probable structure | {int(c.get('L2', 0))} |
| L3 | a curated database holds a compound at this mass or formula; isomers unresolved | {int(c.get('L3', 0))} |
| L4 | molecular formula unequivocal, no database compound carries it | {int(c.get('L4', 0))} |
| L5 | exact mass only — several formulas fit, none supported | {int(c.get('L5', 0))} |
| — | no candidate from any source | {int(c.get('none', 0))} |

**{n_id} of {n} features carry a candidate of some kind.** Read that number with
the levels attached, not on its own: only **{int(c.get('L2', 0))}** reach L2, and
the **{int(c.get('L5', 0))}** at L5 are candidates in name only — several formulas
fit the mass and no database supports any of them.
{'' if dark.empty else 'Features with nothing at all: ' + ', '.join(f'`{f}`' for f in dark.feature_id) + '.'}

Nothing **below** L2 is an identification. L3 in particular means "a curated
database holds a compound of this composition", not "this feature is that
compound" — the isomers underneath an L3 call are usually many, and the table
records how many.

## What the spectral search actually returned

This is the part worth reading closely, because it is mostly a negative result
and negative results here are informative.

| source | features reached |
|---|---|
| GNPS community library — a named match | {_n_feat(graded, 'fasst_gnpslibrary')} |
| GNPS analog / "suspect" entries — not identifications | {_n_feat(graded, 'fasst_gnps_analog')} |
| public repository — recurring but unnamed | {_n_feat(graded, 'fasst_repository')} |
| MassBank — a reference spectrum exists for the composition | {_n_feat(graded, 'massbank_reference')} |

**The GNPS community library names none of these features.** Of the raw hits the
service returned, all but a handful were matches over three or four shared
fragments — at a 0.05 Da tolerance unrelated lipids collide that often by
chance, so anything under six matching peaks is discarded here. What survives
that floor carries no compound name.

What the repository index does say is more interesting than nothing: a few
features recur in eight or more independent public datasets at nine to fourteen
matching peaks, and are **unidentified in every one of them**. These are real,
widespread molecules that the field has not named — not artefacts of this
experiment.

MassBank's spectral-similarity endpoint returns a server error, so no spectral
comparison against it was possible; formula and neutral-mass lookup were used
instead, and a hit there means a reference spectrum exists for that composition,
not that it matches.

## What was searched

Reached over the network, because these are libraries the facility did **not**
use:

- **GNPS2 FASST** against the GNPS community library, and separately against an
  index of public repository data. A repository hit is recorded as *occurrence*
  and never as an identification: it says the same spectrum has been seen in
  other public experiments, not what the molecule is.
- **MassBank Europe** — precursor-window lookup.
- **LIPID MAPS** — formula lookup against LMSD.
- **RefMet / Metabolomics Workbench** — formula lookup, which also supplies the
  class vocabulary the rest of this project uses.

Searched offline: the 206k-row RefMet dump already in the data tree, by neutral
mass at 5 ppm.

MS/MS was re-extracted from the raw runs rather than taken from any earlier
processing: {ms2} of {n} features were flagged as having MS/MS, and a consensus
spectrum was recovered for {n_spectra}.

## What was NOT searched, and why

Bruker MetaboBASE, NIST23, the HMDB target list and MS-DIAL LipidBlast VS69.
The facility already ran all four against this exact data, and two in-house
re-runs against the same LipidBlast atlas returned nothing. Repeating them would
have produced the same silence more slowly.

## Caveats a reader should carry

- **Mass is degenerate at this size.** At 5 ppm on a ~900 Da molecule several
  formulas fit. The three features the facility had already identified come back
  at formula ranks 2, 3 and 6 on mass alone — which is exactly why database
  support, not mass ranking, decides the grade here.
- **LIPID MAPS does not cover everything.** It returns nothing for HBMP, a class
  the facility did identify in this dataset. Absence from LMSD is not absence
  from biology.
- **Bacterial phospholipid coverage in public spectral libraries is poor and
  unmeasured.** A dark feature here is a statement about library coverage at
  least as much as about the molecule.
- **The *E. coli* prior is a reading aid, not a filter.** This organism makes
  PE and PG and essentially no PC, and the project's own reports flag PC as
  over-called elsewhere in this dataset. That prior was deliberately kept out of
  the code so it could not quietly remove a correct answer.
- **CCS is measured for all {n} features and is not yet used.** It is carried in
  the table as unexploited orthogonal evidence.

## Positive control

The three features the facility had already identified were run blind through
the identical pipeline. A run that fails to recover them is not to be trusted
for the other {n - was_named}.

{chr(10).join(controls)}

Read the acyl-chain line against the expected name, because it is the sharpest
check available and it does not agree everywhere. The two HBMP controls are
corroborated exactly — the chains the facility named are the chains their own
MS/MS gives up. The PS control is **not**: it passes on mass and formula, but
its fragments show neither of the chains in the name it carries. That call came
from an HMDB name list rather than a spectral match, and this is the first
evidence bearing on it directly. Treat it as open.

## Reproducing

From `research/fabfos/lipidomics`, in order:

    mamba run -n p312       python -m identify.build_manifest
    mamba run -n p312       python -m identify.massdb
    mamba run -n p312       python -m identify.web_candidates
    mamba run -n lipidomics python -m identify.extract_spectra
    mamba run -n p312       python -m identify.fa_fragments
    mamba run -n p312       python -m identify.spectral_search
    mamba run -n p312       python -m identify.grade
    mamba run -n p312       python -m identify.publish
    mamba run -n p312       python -m identify.hits_table

Every web response is cached under `processed/identification/cache/`, so a
re-run reproduces this table without re-querying. `extract_spectra` needs
pyteomics and therefore the `lipidomics` env; everything else runs under `p312`.
`extract_spectra --reuse` re-derives the consensus spectra from the persisted
raw scans, so the merge rule can be retuned without another pass over 30 GB of
mzML.
"""


def run() -> None:
    manifest = pd.read_csv(common.IDENT_DIR / "hit_manifest.csv")
    graded = pd.read_csv(common.IDENT_DIR / "graded_candidates.csv")
    best = pd.read_csv(common.PUBLISH_DIR / "clone_response_best_call_per_feature.csv")

    acyl = {}
    if "acyl_chains_observed" in best:
        acyl = {
            r.feature_id: r.acyl_chains_observed
            for _, r in best.iterrows()
            if isinstance(r.acyl_chains_observed, str) and r.acyl_chains_observed
        }

    common.PUBLISH_DIR.mkdir(parents=True, exist_ok=True)
    _figure(graded, best, acyl, common.PUBLISH_DIR / "01_evidence_per_feature")
    (common.PUBLISH_DIR / "readme.md").write_text(_readme(graded, best, manifest))

    print(f"published to {common.PUBLISH_DIR}")
    for p in sorted(common.PUBLISH_DIR.iterdir()):
        print(f"  {p.name:<52} {p.stat().st_size:>9,} B")


if __name__ == "__main__":
    run()
