"""Figures for the membrane-lipid classification and the per-cell abundance test.

Three panels, each answering a question a reviewer will ask in this order: how much
of the table is now called and how well; what the clone actually does; and whether
the answer survives being told the classifier is wrong.

Run:  mamba run -n p312 python -m identify.membrane_figures      (from research/fabfos/lipidomics)
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from identify import common, membrane_abundance as ma  # noqa: E402

PUBLISH = common.PUBLISH_DIR.parent / "07_lipid_class_enrichment"
TIER_COLOR = {"1_massbalance": "#1b4965", "2_formula": "#4a7c9e",
              "2_facility": "#7fa8c4", "3_model": "#c79a5b", "4_abstain": "#cccccc"}
CLONE_C, PCC1_C = "#22577a", "#c1666b"


def save(fig, stem: str) -> None:
    PUBLISH.mkdir(parents=True, exist_ok=True)
    fig.savefig(PUBLISH / f"{stem}.png", dpi=200, bbox_inches="tight")
    fig.savefig(PUBLISH / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)
    print(f"   wrote {stem}.png")


# ----------------------------------------------------------------------- figure 1
def fig_classifier(calls: pd.DataFrame, perf: pd.DataFrame) -> None:
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))

    # (a) coverage, by feature count and by signal -- the two are very different,
    # and that difference is the honest answer to "how much is the model carrying".
    a = ax[0, 0]
    order = ["1_massbalance", "2_formula", "2_facility", "3_model", "4_abstain"]
    order = [t for t in order if (calls.membrane_tier == t).any()]
    sig = calls.groupby("membrane_tier").mean_bio_abundance.sum()
    cnt = calls.membrane_tier.value_counts()
    left_c = left_s = 0.0
    for t in order:
        c = 100 * cnt.get(t, 0) / len(calls)
        s = 100 * sig.get(t, 0) / sig.sum()
        a.barh(1, c, left=left_c, color=TIER_COLOR[t], edgecolor="w")
        a.barh(0, s, left=left_s, color=TIER_COLOR[t], edgecolor="w",
               label=t.split("_", 1)[1])
        for y, v, lo in ((1, c, left_c), (0, s, left_s)):
            if v > 4:
                a.text(lo + v / 2, y, f"{v:.0f}%", ha="center", va="center",
                       color="w", fontsize=9, fontweight="bold")
        left_c += c
        left_s += s
    a.set_yticks([0, 1], ["share of signal", "share of features"])
    a.set_xlim(0, 100)
    a.set_xlabel("percent of the 800 negative-mode features")
    a.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.20),
             frameon=False)
    a.set_title("a  Coverage reaches 96% by count, but fragment evidence\n"
                "    still carries 70% of the signal", loc="left", fontsize=10)

    # (b) confusion matrices, with n on the face -- a rate estimated on 17 negatives
    # should never be shown without that 17 next to it.
    a = ax[0, 1]
    a.axis("off")
    rows = [("A  membrane (canonical)", perf[perf.model == "canonical"].iloc[0]),
            ("B  curvature (canonical)",
             perf[perf.model == "B curvature (canonical)"].iloc[0])]
    txt = []
    for name, r in rows:
        lo, hi = _wilson(int(r.tn), int(r.n_neg))
        txt.append(
            f"{name}\n"
            f"    AUC {r.auc_mean:.3f} +/- {r.auc_sd:.3f}\n"
            f"                    pred neg   pred pos\n"
            f"     true neg  {int(r.tn):8d}   {int(r.fp):8d}\n"
            f"     true pos  {int(r.fn):8d}   {int(r.tp):8d}\n"
            f"    sensitivity {r.sens:.3f}  (n = {int(r.n_pos)})\n"
            f"    specificity {r.spec:.3f}  (n = {int(r.n_neg)}, 95% CI "
            f"{lo:.2f}-{hi:.2f})")
    sh = perf[perf.model.str.contains("shuffled")]
    txt.append("shuffled-label controls   AUC "
               + ", ".join(f"{v:.3f}" for v in sh.auc_mean))
    a.text(0, 1, "\n\n".join(txt), va="top", family="monospace", fontsize=8.5,
           transform=a.transAxes)
    a.set_title("b  Out-of-fold performance, 20x5-fold CV\n"
                "    The specificity n is the binding constraint",
                loc="left", fontsize=10)

    # (c) the covariate shift the tier-3 calls are extrapolating across
    a = ax[1, 0]
    lab = calls.membrane_tier.isin(["1_massbalance", "2_formula", "2_facility"])
    bins = np.linspace(1, 7, 40)
    a.hist(np.log10(calls.loc[lab, "mean_bio_abundance"] + 1), bins=bins, alpha=0.75,
           color=TIER_COLOR["1_massbalance"], label=f"labelled  (n={int(lab.sum())})")
    a.hist(np.log10(calls.loc[calls.membrane_tier == "3_model",
                              "mean_bio_abundance"] + 1), bins=bins, alpha=0.75,
           color=TIER_COLOR["3_model"],
           label=f"model-called  (n={int((calls.membrane_tier == '3_model').sum())})")
    a.set_xlabel("log10 mean abundance")
    a.set_ylabel("features")
    a.legend(fontsize=8)
    a.set_title("c  The model is applied to features fainter than\n"
                "    anything it was trained on", loc="left", fontsize=10)

    # (d) does the composition land where E. coli's membrane is known to be?
    a = ax[1, 1]
    mem = calls.membrane == "yes"
    sets = {"fragment\nevidence only": mem & (calls.curvature_tier != "3_model"),
            "all tiers": mem}
    xs = []
    for i, (name, m) in enumerate(sets.items()):
        s = calls[m]
        w = s.mean_bio_abundance.fillna(0.0)
        cf = w[s.curvature_prior == "curvature-forcing"].sum()
        bf = w[s.curvature_prior == "bilayer-forming"].sum()
        pct = 100 * cf / (cf + bf)
        a.bar(i, pct, color=CLONE_C if i == 0 else TIER_COLOR["3_model"], width=0.55)
        a.text(i, pct + 2, f"{pct:.0f}%", ha="center", fontsize=10)
        xs.append(name)
    a.axhspan(70, 80, color="0.85", zorder=0)
    a.text(1.45, 75, "E. coli PE\n70-80%", ha="right", va="center", fontsize=8,
           color="0.35")
    a.set_xticks(range(len(xs)), xs, fontsize=9)
    a.set_ylim(0, 100)
    a.set_ylabel("curvature-forcing, % of membrane signal")
    a.set_title("d  Fragment evidence reproduces the known composition;\n"
                "    the model tier pulls away from it", loc="left", fontsize=10)

    fig.tight_layout()
    save(fig, "01_Membrane_classification_coverage_and_accuracy")


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    ph, d = k / n, 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# ----------------------------------------------------------------------- figure 2
def fig_contrasts(ps_all: pd.DataFrame, tests: pd.DataFrame) -> None:
    sets = [("tier1", "hard", "fragment evidence only  (144 features)"),
            ("full", "hard", "classifier, >=95% coverage  (630 features)")]
    fig, axes = plt.subplots(len(ma.READOUTS), 2, figsize=(11, 12), sharex=True)

    for row, readout in enumerate(ma.READOUTS):
        for col, (ls, wt, title) in enumerate(sets):
            a = axes[row, col]
            ps = ps_all[(ps_all.label_set == ls) & (ps_all.weighting == wt)]
            ps = ps.set_index("sample")
            t = tests[(tests.clone == "Clone2") & (tests.label_set == ls)
                      & (tests.weighting == wt) & (tests.readout == readout)]
            log = readout in ma.LOG_SCALE
            notes = []
            for i, (f, kind) in enumerate(ma.CONDITIONS):
                frac = ma.FRACTION_NAME[f]
                sides = ma.groups_for("Clone2", f, kind)
                for j, ((strain, treat), c) in enumerate(zip(sides,
                                                             (CLONE_C, PCC1_C))):
                    cols = ma.cols_for(strain, treat, f, ps.index)
                    v = ps.loc[cols, readout].to_numpy(float)
                    if log:
                        v = np.log2(v)
                    x = i + (-0.16 if j == 0 else 0.16)
                    a.scatter(np.full(len(v), x) + np.linspace(-.04, .04, len(v)), v,
                              s=34, color=c, zorder=3,
                              label=("a: test group" if j == 0 else "b: reference")
                              if (i == 0 and row == 0 and col == 0) else None)
                    a.hlines(v.mean(), x - 0.11, x + 0.11, color=c, lw=2, zorder=4)
                r = t[(t.fraction == frac) & (t.contrast == kind)]
                if len(r):
                    r = r.iloc[0]
                    mark = "*" if r.p_holm < 0.05 else ("." if r.p < 0.05 else "n.s.")
                    notes.append((i, f"{mark}\n{r.p_holm:.3f}"))
            # Headroom first, then annotate in axes fraction -- reading get_ylim()
            # mid-loop stacks the labels at four different heights.
            lo, hi = a.get_ylim()
            a.set_ylim(lo, hi + 0.30 * (hi - lo))
            for i, s in notes:
                a.annotate(s, xy=(i, 0.995), xycoords=("data", "axes fraction"),
                           ha="center", va="top", fontsize=7.5)
            a.set_xticks(range(4),
                         [f"{ma.FRACTION_NAME[f]}\n{k}" for f, k in ma.CONDITIONS],
                         fontsize=7.5)
            suffix = "\n(OD-invariant)" if readout.endswith("proportion") else ""
            a.set_ylabel(("log2 " if log else "") + readout + suffix, fontsize=9)
            if row == 0:
                a.set_title(title, fontsize=10, pad=16)

    fig.suptitle("Clone2, the four canonical conditions, per replicate   "
                 "(marker and Holm-corrected p above each)\n"
                 "columns 1 and 3 compare Clone2 to pCC1 at baseline; columns 2 and 4"
                 " are Clone2's own toluene response\n"
                 "amount readouts are per OD600; proportions cancel OD exactly",
                 fontsize=10.5)
    h, lb = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lb, loc="lower center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, -0.012))
    fig.tight_layout(rect=(0, 0.02, 1, 0.965))
    save(fig, "02_Membrane_lipid_per_cell_Clone2_vs_pCC1")


# ----------------------------------------------------------------------- figure 3
def fig_concordance(tests: pd.DataFrame, dec: pd.DataFrame) -> None:
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))

    key = ["clone", "fraction", "contrast", "readout"]
    t1 = tests[tests.label_set == "tier1"].set_index(key)
    fu = tests[(tests.label_set == "full") & (tests.weighting == "hard")].set_index(key)
    j = t1[["diff", "p"]].join(fu[["diff", "p"]], lsuffix="_t1", rsuffix="_full")
    j = j.reset_index()
    j = j[j.clone == "Clone2"]

    # Proportions and amounts are not on the same scale -- one is a fraction, the
    # other a log2 ratio -- so they get one panel each rather than a shared axis
    # that would hide the proportion flips underneath the amount effects.
    marks = {"A_proportion": "o", "B_proportion": "^", "A_amount": "s", "B_amount": "D"}
    for k, (panel, readouts, unit, verdict) in enumerate([
            ("a", ["A_proportion", "B_proportion"], "difference in proportion",
             "the compositional readouts do not survive it"),
            ("b", ["A_amount", "B_amount"], "log2 fold change, per OD600",
             "the per-cell readouts are unchanged by it")]):
        a = ax[k]
        s_all = j[j.readout.isin(readouts)]
        flip = np.sign(s_all.diff_t1) != np.sign(s_all.diff_full)
        for r in readouts:
            s = j[j.readout == r]
            a.scatter(s.diff_t1, s.diff_full, marker=marks[r], s=60, label=r,
                      facecolor=np.where(np.sign(s.diff_t1) != np.sign(s.diff_full),
                                         "#c1666b", "#22577a"),
                      edgecolor="k", linewidth=0.5, zorder=3)
        lim = np.nanmax(np.abs(np.r_[s_all.diff_t1, s_all.diff_full])) * 1.2
        a.plot([-lim, lim], [-lim, lim], "k--", lw=0.7, zorder=1)
        a.axhline(0, color="0.7", lw=0.7)
        a.axvline(0, color="0.7", lw=0.7)
        a.set_xlim(-lim, lim)
        a.set_ylim(-lim, lim)
        a.set_xlabel(f"fragment-evidence set  ({unit})")
        a.set_ylabel(">=95% classifier set")
        a.legend(fontsize=8, loc="lower right")
        a.set_title(f"{panel}  {int(flip.sum())} of {len(s_all)} change SIGN (red) --"
                    f"\n    {verdict}", loc="left", fontsize=10)

    # The amount readouts are a ratio of two things that both moved. Showing the
    # split is the difference between a lipid claim and a growth claim.
    a = ax[2]
    x = np.arange(len(dec))
    a.bar(x - 0.2, dec.log2_raw_signal, 0.38, label="raw membrane signal",
          color="#4a7c9e")
    a.bar(x + 0.2, dec.log2_od, 0.38, label="OD600", color="#c79a5b")
    a.plot(x, dec.log2_per_cell, "o-", color="k", lw=1.4, ms=6,
           label="per cell (= signal - OD)")
    a.axhline(0, color="k", lw=0.8)
    a.set_xticks(x, [f"{r.fraction}\n{r.contrast}" for _, r in dec.iterrows()],
                 fontsize=7)
    a.set_ylabel("log2  Clone2 / pCC1")
    a.legend(fontsize=8)
    a.set_title("c  Under toluene the per-cell effect is the OD term.\n"
                "    The lipid signal itself barely separates the strains.",
                loc="left", fontsize=10)

    fig.tight_layout()
    save(fig, "03_Does_the_result_depend_on_the_classifier")


def run() -> None:
    calls = pd.read_csv(PUBLISH / "membrane_calls.csv")
    perf = pd.read_csv(PUBLISH / "membrane_classifier_performance.csv")
    tests = pd.read_csv(PUBLISH / "membrane_abundance_tests.csv")
    ps = pd.read_csv(PUBLISH / "membrane_abundance_per_sample.csv")
    dec = pd.read_csv(PUBLISH / "membrane_abundance_od_decomposition.csv")
    fig_classifier(calls, perf)
    fig_contrasts(ps, tests)
    fig_concordance(tests, dec)


if __name__ == "__main__":
    run()
