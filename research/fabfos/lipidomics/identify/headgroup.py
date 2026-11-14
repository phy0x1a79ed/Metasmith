"""Read the headgroup off the MS/MS, and derive lipid shape from it.

Class annotation reaches 7% of this feature table, so it cannot supply a null for
any enrichment question. Mass alone cannot either: at 5 ppm most features admit
both phosphorus-containing and phosphorus-free formulas. What is left is the
instrument data.

WHICH EVIDENCE ACTUALLY EXISTS HERE. The obvious plan -- look for the diagnostic
headgroup anions -- does not survive contact with these spectra. Two of the generic
phospholipid ions, PO3- at 78.96 and H2PO4- at 96.97, are below the MS2 acquisition
floor of m/z 99.92 and were never recorded. The rest (glycerophosphate at 152.996
and 171.006, the headgroup ions at 140-297) are simply not there: searched at 50 mDa
across every unfiltered scan of the three positive controls, the only matches are
single-scan peaks at noise intensity, 17-49 mDa off. This is a DDA-PASEF method whose
MS2 puts its ions into acyl anions and the precursor envelope, not into the headgroup.

What IS there, as the base peaks of every negative-mode spectrum, is the fatty-acyl
carboxylate anions -- and the deconvoluted neutral mass is known to 5 ppm. Those two
together give the headgroup by subtraction:

    backbone = neutral_mass - sum(acyl chains) + n_chains * H2O

and the backbone residues are far apart on the mass axis. This recovers both PG
controls to within 1 mDa with the correct chain compositions.

This is MS/MS-CONSTRAINED MASS BALANCE, not direct observation of a headgroup, and
the distinction matters: the acyl anions are real fragment evidence, but the
headgroup itself is inferred by arithmetic. What makes it defensible rather than a
return to the failed mass-only attempt is that the hypothesis space is the lipid
structural grammar -- a backbone from a short list, carrying n fatty acids -- rather
than free CHNOPS enumeration, and that the residues are not interconvertible by
trading carbons for double bonds. PE and PG differ by 30.995 Da, which is not
expressible on the acyl lattice at all.

Positive mode has no acyl anions and no generic phospholipid ion, so it is called
only where the phosphocholine cation or a headgroup neutral loss appears. Most
positive-mode features therefore come back indeterminate. That is the honest answer
and the bounding in the enrichment step is built to absorb it.

Three-state throughout. "Unspecified" means the phospholipid gate passed and the
headgroup did not; "indeterminate" means there was no usable evidence. Collapsing
either into "not a phospholipid" would turn a weak spectrum into a biological claim.

Run:  mamba run -n p312 python -m identify.headgroup            (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common, fa_fragments  # noqa: E402

# ---------------------------------------------------------------- element masses
M = {"C": 12.0, "H": 1.007825032, "N": 14.003074005, "O": 15.994914620,
     "P": 30.97376151}
PROTON = 1.007276467
ELECTRON = 0.000548580
MS2_FLOOR_MZ = 99.92        # this method's MS2 lower acquisition limit


def neutral(c=0, h=0, n=0, o=0, p=0) -> float:
    return c * M["C"] + h * M["H"] + n * M["N"] + o * M["O"] + p * M["P"]


def anion(c=0, h=0, n=0, o=0, p=0) -> float:
    return neutral(c, h, n, o, p) - PROTON


def cation(c=0, h=0, n=0, o=0, p=0) -> float:
    return neutral(c, h, n, o, p) - ELECTRON


H2O = neutral(h=2, o=1)

# ----------------------------------------------------- backbone residue library
# The intact backbone, before any fatty acid is esterified onto it. A lipid of
# n chains has mass  residue + sum(FA) - n*H2O.
#
# PA is glycerophosphate: the same residue a PG or PE would show if its
# distal headgroup were lost, so PA is only called when the arithmetic closes on
# 172.014 exactly -- it is not a fallback bucket.
RESIDUE = {
    "PA": (neutral(c=3, h=9, o=6, p=1), True),                 # 172.0137
    "PE": (neutral(c=5, h=14, n=1, o=6, p=1), True),           # 215.0559
    "PG": (neutral(c=6, h=15, o=8, p=1), True),                # 246.0505
    "PC": (neutral(c=8, h=20, n=1, o=6, p=1), True),           # 257.1028
    "PS": (neutral(c=6, h=14, n=1, o=8, p=1), True),           # 259.0457
    "PI": (neutral(c=9, h=19, o=11, p=1), True),               # 334.0665
    # Non-phosphate backbones. Matching one of these is a positive "not a
    # phospholipid" call, which is what makes the negative class mean something.
    "glycerolipid": (neutral(c=3, h=8, o=3), False),           #  92.0473 (MAG/DAG/TAG)
}
PHOSPHO = {k for k, (_, p) in RESIDUE.items() if p}

# WHICH BACKBONES ARE ACTUALLY SEPARABLE. Two residues are indistinguishable if
# their difference can be absorbed by trading carbons and double bonds among the
# chains -- the acyl lattice is a*14.0157 - b*2.0157. Measured over this library:
#
#     PE  vs PC            42.0470 = 3xCH2                 0.00 mDa   EXACT
#     PA  vs glycerolipid  79.9663 = 7xCH2 - 9xH2          2.37 mDa
#     PI  vs glycerolipid 242.0192 = 20xCH2 - 19xH2        3.50 mDa
#     PA  vs PI           162.0528 = 13xCH2 - 10xH2        5.87 mDa
#
# So mass balance can never separate PE from PC, and -- the consequence that
# matters -- it cannot separate PA from a neutral glycerolipid, which means the
# PHOSPHOLIPID GATE ITSELF is undecidable for that group. This is what the
# validation caught: three triglycerides were being called PA. Rather than assert
# a class the physics does not support, degenerate residues are merged and the
# group carries the ambiguity forward honestly.
RESIDUE_GROUP = {
    "PE": "PE/PC", "PC": "PE/PC",
    "PG": "PG",
    "PS": "PS",
    "PA": "PA/PI/neutral", "PI": "PA/PI/neutral", "glycerolipid": "PA/PI/neutral",
}
# The PA/PI/neutral group spans both phospholipids and neutral glycerolipids, so
# membership alone cannot settle the gate. It is settled per feature instead, from
# which residues actually closed -- see mass_balance().

# 5 ppm at 700 Da is 3.5 mDa; 8 mDa allows for the acyl-anion calibration on top
# without opening the door to chance closures. The 15 mDa first pass admitted them.
RESIDUE_TOL_DA = 0.008
# A real glycerophospholipid puts its acyl anions at the BASE of the negative-mode
# spectrum -- the controls sit at 78-100% relative. A 5% floor lets noise peaks
# masquerade as chains, and three chains' worth of noise plus a free chain count is
# enough freedom to close a backbone by accident.
ACYL_MIN_REL_INTENSITY = 10.0
MAX_CHAINS = 4              # cardiolipin would be 4; acyl-PG is 3
CHAIN_C = range(10, 27)
CHAIN_DB = range(0, 7)

# --------------------------------------------- diagnostic ions (weak tier here)
# Retained because they are free to test and they corroborate where present. Their
# measured yield on this dataset is reported by headgroup_validate rather than
# assumed. Ions below MS2_FLOOR_MZ are flagged, not silently searched for.
GENERIC_NEG = {
    "PO3-": anion(p=1, o=3, h=1),                                             # 78.959
    "H2PO4-": anion(p=1, o=4, h=3),                                           # 96.970
    "glycerophosphate-H2O-": anion(c=3, h=9, o=6, p=1) - H2O,                 # 152.996
    "glycerophosphate-": anion(c=3, h=9, o=6, p=1),                           # 171.006
}
HEADGROUP_NEG = {
    "PE": {"phosphoethanolamine-": anion(c=2, h=8, n=1, o=4, p=1),            # 140.012
           "GPE-H2O-": anion(c=5, h=14, n=1, o=6, p=1) - H2O,                 # 196.038
           "GPE-": anion(c=5, h=14, n=1, o=6, p=1)},                          # 214.049
    "PG": {"GPG-H2O-": anion(c=6, h=15, o=8, p=1) - H2O,                      # 227.033
           "GPG-": anion(c=6, h=15, o=8, p=1)},                               # 245.043
    "PI": {"inositolphosphate-": anion(c=6, h=13, o=9, p=1),                  # 259.022
           "GPI-2H2O-": anion(c=9, h=19, o=11, p=1) - 2 * H2O},               # 297.038
    "PC": {"phosphocholine-CH3-": anion(c=4, h=12, n=1, o=4, p=1)},           # 168.043
    "PS": {"GPS-H2O-": anion(c=6, h=14, n=1, o=8, p=1) - H2O},                # 240.028
}
HEADGROUP_POS = {
    # The one positive-mode fragment strong enough to carry a call on its own.
    "PC": {"phosphocholine+": cation(c=5, h=15, n=1, o=4, p=1)},              # 184.073
}
NEUTRAL_LOSS_POS = {
    "PE": {"phosphoethanolamine": neutral(c=2, h=8, n=1, o=4, p=1)},          # 141.019
    "PS": {"phosphoserine": neutral(c=3, h=8, n=1, o=6, p=1)},                # 185.009
    "PG": {"phosphoglycerol": neutral(c=3, h=9, o=6, p=1)},                   # 172.014
}
TOL_DA = 0.012
MIN_REL_INTENSITY = 2.0

# ------------------------------------------------------------------ shape lookup
# Nitrogen survives the merge intact: PE and PC both carry it, PG does not, and
# every member of the PA/PI/neutral group is nitrogen-free. So contains_N is
# decidable even where the phospholipid gate is not.
GROUP_N = {"PE/PC": "yes", "PG": "no", "PS": "yes", "PA/PI/neutral": "no"}

# Curvature does NOT survive the merge: PE is a cone and PC is a cylinder, and the
# two are exactly degenerate by mass. Two readings are therefore emitted.
#   strict  -- PE/PC is indeterminate. Assumes nothing.
#   prior   -- PE/PC is read as PE, hence cone. Rests on E. coli having no
#              phosphatidylcholine synthase, so PC is not a native product here.
# Both are carried to the statistics rather than one being chosen silently.
GROUP_CURV_STRICT = {"PG": "cylinder", "PS": "cylinder",
                     "PE/PC": "indeterminate", "PA/PI/neutral": "indeterminate"}
GROUP_CURV_PRIOR = {**GROUP_CURV_STRICT, "PE/PC": "cone"}


def curvature(group: str | None, n_acyl: int | None, prior: bool = False) -> str:
    """Cone / cylinder / inverted cone, from headgroup group crossed with chain count.

    Any single-chain species is an inverted cone whatever its headgroup: the label
    is about head area against tail volume, and a lyso species has lost half its
    tails. Deliberately ordinal -- real spontaneous curvature is a measured
    X-ray/NMR quantity per lipid, and computing one from a class label would be
    false precision.
    """
    tab = GROUP_CURV_PRIOR if prior else GROUP_CURV_STRICT
    base = tab.get(group, "indeterminate")
    if base == "indeterminate":
        return base
    return "inverted-cone" if n_acyl == 1 else base


def contains_n(group: str | None) -> str:
    return GROUP_N.get(group, "indeterminate")


# ---------------------------------------------------------------- chain algebra
def fa_neutral(carbons: int, db: int) -> float:
    return carbons * M["C"] + (2 * carbons - 2 * db) * M["H"] + 2 * M["O"]


_FA_TABLE = [(f"{c}:{d}", fa_neutral(c, d)) for c in CHAIN_C for d in CHAIN_DB
             if d <= (c - 2) // 2]

_CH2 = M["C"] + 2 * M["H"]        # 14.01565 -- one carbon step
_H2 = 2 * M["H"]                  #  2.01565 -- one double-bond step
_FA_O2 = 2 * M["O"]               # 31.98983 -- the two oxygens each ester carries


def _decompose(mass: float, k: int, tol: float) -> list[str] | None:
    """Can `mass` be k fatty acids? Returns the total composition, or None.

    Solved on the lattice rather than by enumerating combinations. k chains with
    total carbons T and total double bonds D weigh exactly
    12T + H(2T-2D) + 2k*O, so the only free integers are T and D:

        mass - k*O2 = T*14.01565 - D*2.01565

    For each plausible T the required D follows, and only near-integer D in range
    is a solution. That turns a k-deep combinatorial search -- ~10^8 at k=4 -- into
    a hundred arithmetic checks, and returns the same answer, because the headgroup
    depends on the chains' TOTAL mass and not on how they are partitioned.

    Restricting the remainder to real fatty acids is what keeps this from becoming
    the free-formula search that already failed once.
    """
    if k == 0:
        return ([], abs(mass)) if abs(mass) <= tol else None
    target = mass - k * _FA_O2
    best = None
    for total_c in range(min(CHAIN_C) * k, max(CHAIN_C) * k + 1):
        d_real = (total_c * _CH2 - target) / _H2
        total_d = round(d_real)
        if total_d < 0 or total_d > max(CHAIN_DB) * k:
            continue
        # every chain needs at least ~2 carbons more than twice its double bonds
        if total_d > (total_c - 2 * k) // 2:
            continue
        err = abs(total_c * _CH2 - total_d * _H2 - target)
        if err <= tol and (best is None or err < best[0]):
            best = (err, [f"{total_c}:{total_d}[x{k}]"])
    return (best[1], best[0]) if best else None


def mass_balance(neutral_mass: float, observed: list[str]) -> dict | None:
    """Solve for the backbone from the neutral mass and the observed acyl anions.

    Prefers the solution using the MOST observed chains and the FEWEST inferred
    ones, so a call rests on evidence wherever evidence exists. The number of
    inferred chains travels with the result rather than being averaged away.

    Every solution within tolerance is collected, not just the winner. If solutions
    from more than one residue GROUP close, the answer is ambiguous for this feature
    regardless of what the library-wide degeneracy analysis says -- the chain count
    is a free parameter too, so a spectrum with spare peaks can close two different
    backbones. Reporting only the best would hide exactly that.
    """
    obs = {n: fa_neutral(*map(int, n.split(":"))) for n in observed}
    best = None
    groups: set[str] = set()
    residues: set[str] = set()
    for n_chain in range(1, MAX_CHAINS + 1):
        # k is how many chains the spectrum actually showed. k=0 is excluded: a
        # backbone that closes only on inferred chains is pure mass arithmetic,
        # which is the approach that already failed. Every call here rests on at
        # least one observed acyl anion.
        for k in range(min(n_chain, len(obs)), 0, -1):
            for combo in itertools.combinations(sorted(obs), k):
                used = sum(obs[c] for c in combo)
                for name, (res, _) in RESIDUE.items():
                    remainder = neutral_mass - res + n_chain * H2O - used
                    sol = _decompose(remainder, n_chain - k, RESIDUE_TOL_DA)
                    if sol is None:
                        continue
                    rest, err = sol
                    groups.add(RESIDUE_GROUP[name])
                    residues.add(name)
                    cand = {
                        "headgroup": name, "n_acyl": n_chain,
                        "chains_observed": list(combo), "chains_inferred": rest,
                        "n_inferred": n_chain - k,
                        "residue_err_mda": 1000 * err,
                    }
                    key = (-k, cand["n_inferred"], abs(cand["residue_err_mda"]))
                    if best is None or key < best[0]:
                        best = (key, cand)
    if best is None:
        return None
    out = dict(best[1])
    out["group"] = RESIDUE_GROUP[out["headgroup"]]
    out["groups_closing"] = sorted(groups)
    out["group_unique"] = len(groups) == 1
    # The phospholipid gate is decided by the residues that actually closed, not by
    # the worst case of the group they belong to. A backbone that closes only on
    # glycerol -- PA and PI both out of range for it -- is a positive
    # not-a-phospholipid call, and that is what keeps the negative class real.
    phos = {r in PHOSPHO for r in residues}
    out["phospholipid"] = ("yes" if phos == {True}
                           else "no" if phos == {False} else "indeterminate")
    return out


# ------------------------------------------------------------------- ion matcher
def _match(peaks, ref_mz: float) -> float | None:
    best = None
    for mz, inten in peaks:
        if abs(mz - ref_mz) <= TOL_DA and inten >= MIN_REL_INTENSITY:
            if best is None or inten > best:
                best = inten
    return best


def diagnostic_ions(peaks, polarity: str, precursor_mz: float | None,
                    charge: int = 1) -> dict[str, float]:
    """The weak corroborating channel. Ions below the MS2 floor are skipped."""
    found = {}
    tabs = ([("generic", GENERIC_NEG)] + [(k, v) for k, v in HEADGROUP_NEG.items()]
            if polarity == "neg" else [(k, v) for k, v in HEADGROUP_POS.items()])
    for tag, tab in tabs:
        for name, ref in tab.items():
            if ref < MS2_FLOOR_MZ:
                continue
            v = _match(peaks, ref)
            if v is not None:
                found[f"{tag}:{name}"] = v
    if polarity == "pos" and precursor_mz is not None:
        for hg, tab in NEUTRAL_LOSS_POS.items():
            for name, loss in tab.items():
                # A loss of L from a charge-z precursor moves m/z by L/z.
                v = _match(peaks, precursor_mz - loss / charge)
                if v is not None:
                    found[f"{hg}:NL-{name}"] = v
    return found


# ------------------------------------------------------------------------ caller
def classify(spec: dict, neutral_mass: float | None, polarity: str,
             precursor_mz: float, charge: int) -> dict:
    peaks = spec["peaks"]
    ions = diagnostic_ions(peaks, polarity, precursor_mz, charge)
    ion_hgs = {k.split(":")[0] for k in ions if k.split(":")[0] != "generic"}

    if polarity == "neg":
        chains = [c["chain"] for c in fa_fragments.annotate([list(p) for p in peaks])
                  if c["intensity"] >= ACYL_MIN_REL_INTENSITY]
        mb = mass_balance(neutral_mass, chains) if (chains and neutral_mass) else None
        if mb:
            group = mb["group"] if mb["group_unique"] else "ambiguous"
            pl = mb["phospholipid"]
            return {
                "phospholipid": pl,
                # A group is only named when it is the only one that closed, and
                # only when its members agree on phospholipid status.
                "headgroup": group if pl == "yes" else (
                    "none" if pl == "no" else "indeterminate"),
                "headgroup_group": group,
                "best_residue": mb["headgroup"],
                "n_acyl": mb["n_acyl"],
                "channel": "mass-balance",
                "n_chains_observed": len(mb["chains_observed"]),
                "n_chains_inferred": mb["n_inferred"],
                "chains": "+".join(mb["chains_observed"] + mb["chains_inferred"]),
                "groups_closing": ",".join(mb["groups_closing"]),
                "residue_err_mda": round(mb["residue_err_mda"], 2),
                "diagnostic_ions": ";".join(sorted(ions)),
            }
        # Acyl anions but no backbone closes: something is there and it is not a
        # glycerolipid we can name. Not a licence to call it non-phospholipid.
        return {**EMPTY, "channel": "neg-no-solution",
                "n_acyl": min(len(chains), MAX_CHAINS) if chains else None,
                "n_chains_observed": len(chains), "chains": "+".join(chains),
                "diagnostic_ions": ";".join(sorted(ions))}

    # Positive mode: no acyl anions, no generic phospholipid ion. It can say yes,
    # never no. The one fragment strong enough to carry a call is phosphocholine,
    # which names PC directly -- so unlike the negative channel this is not subject
    # to the PE/PC degeneracy.
    if ion_hgs:
        hg = sorted(ion_hgs, key=lambda h: -max(
            v for k, v in ions.items() if k.startswith(h + ":")))[0]
        return {**EMPTY, "phospholipid": "yes", "headgroup": RESIDUE_GROUP[hg],
                "headgroup_group": RESIDUE_GROUP[hg], "best_residue": hg,
                "channel": "pos-diagnostic-ion",
                "diagnostic_ions": ";".join(sorted(ions))}
    return {**EMPTY, "channel": "pos-no-evidence",
            "diagnostic_ions": ";".join(sorted(ions))}


EMPTY = {"phospholipid": "indeterminate", "headgroup": "indeterminate",
         "headgroup_group": "indeterminate", "best_residue": None,
         "n_acyl": None, "channel": "no-spectrum", "n_chains_observed": 0,
         "n_chains_inferred": None, "chains": "", "groups_closing": "",
         "residue_err_mda": None, "diagnostic_ions": ""}


# ------------------------------------------------------------------------ runner
def run(lane: str = "full") -> pd.DataFrame:
    pre = "" if lane == "hits" else "full_"
    manifest = pd.read_csv(
        common.IDENT_DIR / ("hit_manifest.csv" if lane == "hits" else "full_manifest.csv")
    ).set_index("feature_id")
    spectra = json.loads(
        (common.SPECTRA_DIR / (pre + "consensus_ms2.json")).read_text())

    rows = []
    for fid, f in manifest.iterrows():
        spec = spectra.get(fid)
        pol = f.polarity if isinstance(f.polarity, str) else None
        base = {
            "feature_id": fid, "mz": f.mz, "rt": f.rt, "adduct": f.adduct,
            "polarity": pol, "has_msms": bool(f.has_msms),
            "neutral_mass": f.neutral_mass,
            "n_scans": spec["n_scans"] if spec else 0,
            "n_peaks": spec["n_peaks"] if spec else 0,
            "mean_abundance": f.get("mean_bio_abundance"),
            "is_control": bool(f.is_control),
        }
        if spec is None or pol is None:
            c = dict(EMPTY)
        else:
            charge = int(f.charge) if pd.notna(f.get("charge")) else 1
            c = classify(spec, f.neutral_mass, pol, float(f.mz), charge)
        g = c["headgroup_group"] if c["headgroup_group"] in GROUP_N else None
        rows.append({**base, **c,
                     "contains_N": contains_n(g),
                     "curvature": curvature(g, c["n_acyl"]),
                     "curvature_prior": curvature(g, c["n_acyl"], prior=True)})

    out = pd.DataFrame(rows)
    if len(out) != len(manifest):
        raise AssertionError("classifier dropped features")
    out.to_csv(common.IDENT_DIR / f"{pre}headgroup_calls.csv", index=False)
    _report(out)
    return out


DECOY_SHIFT_DA = 0.5    # off every real lipid formula, on nothing


def decoy_rate(lane: str = "full") -> None:
    """How often does a backbone close on a mass that cannot be a lipid?

    The mass balance searches seven residues x four chain counts x every subset of
    the observed acyl anions, so it has enough freedom to close by accident -- which
    is exactly how three triglycerides became "PA" in the first pass. The honest
    measure of that is a decoy: shift every neutral mass by half a dalton, which
    lands between the lipid formula lattice's rungs, and re-run unchanged. Anything
    that still closes is chance.
    """
    manifest = pd.read_csv(
        common.IDENT_DIR / ("hit_manifest.csv" if lane == "hits" else "full_manifest.csv")
    ).set_index("feature_id")
    pre = "" if lane == "hits" else "full_"
    spectra = json.loads(
        (common.SPECTRA_DIR / (pre + "consensus_ms2.json")).read_text())
    real = decoy = eligible = 0
    for fid, f in manifest.iterrows():
        spec = spectra.get(fid)
        if spec is None or f.polarity != "neg" or pd.isna(f.neutral_mass):
            continue
        chains = [c["chain"] for c in fa_fragments.annotate(
            [list(p) for p in spec["peaks"]])
            if c["intensity"] >= ACYL_MIN_REL_INTENSITY]
        if not chains:
            continue
        eligible += 1
        real += mass_balance(f.neutral_mass, chains) is not None
        decoy += mass_balance(f.neutral_mass + DECOY_SHIFT_DA, chains) is not None
    print(f"\n== decoy control (neutral mass shifted +{DECOY_SHIFT_DA} Da)")
    print(f"   negative-mode features with usable acyl anions   {eligible}")
    print(f"   backbone closes on the TRUE mass                 {real}"
          f"  ({100 * real / max(eligible, 1):.1f}%)")
    print(f"   backbone closes on the DECOY mass                {decoy}"
          f"  ({100 * decoy / max(eligible, 1):.1f}%)   <- chance rate")
    if real:
        print(f"   implied false-discovery rate among calls        "
              f"{100 * decoy / real:.1f}%")


def _report(d: pd.DataFrame) -> None:
    n = len(d)
    print(f"features classified: {n}\n")
    for axis in ("phospholipid", "headgroup", "curvature", "curvature_prior",
                 "contains_N", "channel"):
        print(f"== {axis}")
        for k, v in d[axis].value_counts(dropna=False).items():
            print(f"    {str(k):<20} {v:5d}  {100 * v / n:5.1f}%")
        print()
    print("== acyl-chain count")
    print(d.n_acyl.value_counts(dropna=False).to_string())
    mb = d[d.channel == "mass-balance"]
    if len(mb):
        print(f"\n== mass-balance calls: {len(mb)}")
        print(f"   chains observed (not inferred): "
              f"{dict(mb.n_chains_observed.value_counts().sort_index())}")
        print(f"   chains inferred: "
              f"{dict(mb.n_chains_inferred.value_counts().sort_index())}")
        print(f"   |residue error| median {mb.residue_err_mda.abs().median():.2f} mDa, "
              f"max {mb.residue_err_mda.abs().max():.2f} mDa")
        print(f"   ambiguous (>1 residue group closed): "
              f"{int((mb.headgroup_group == 'ambiguous').sum())}")
    print("\n== controls")
    for _, r in d[d.is_control].iterrows():
        print(f"    {r.feature_id}  {r.polarity}  phospholipid={r.phospholipid}  "
              f"group={r.headgroup_group} (best {r.best_residue})  n_acyl={r.n_acyl}  "
              f"curv={r.curvature}/{r.curvature_prior}  chains={r.chains}  "
              f"err={r.residue_err_mda} mDa  closed={r.groups_closing}")


if __name__ == "__main__":
    lane = "hits" if "--hits" in sys.argv else "full"
    run(lane=lane)
    decoy_rate(lane)
