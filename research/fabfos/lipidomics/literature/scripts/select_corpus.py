"""Curate the final ~30-paper corpus from candidates.tsv + abstracts.tsv.

The SELECTION dict below encodes the decisions made after reading each abstract:
  band   -- 'review' | 'methodology' | 'biological' | 'bipartite'
  must   -- True if this is a must-cite for the Phase-4 method
  note   -- 1-3 sentence "what this paper actually does" summary
            (grounded in the abstract, NOT the title)

Writes:
  search/selection_notes.md  -- one block per candidate, in_corpus or dropped+reason
  search/final_corpus.tsv    -- the ~30 rows that build_bib.py will consume
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "search" / "candidates.tsv"
ABS = ROOT / "search" / "abstracts.tsv"
OUT_NOTES = ROOT / "search" / "selection_notes.md"
OUT_FINAL = ROOT / "search" / "final_corpus.tsv"


# DOI -> selection record. Anything not listed here is dropped (with reason inferred).
SELECTION: dict[str, dict] = {
    # === REVIEWS (5) ===
    "10.3389/fphys.2016.00375": {
        "band": "review", "must": True,
        "note": "Survey of centrality measures and how each predicts essentiality. Categorizes methods by underlying strategy (topology-only, integrative, dynamic) and discusses predictive power and shortcomings. The anchor review the user pointed at — defines the language to engage when contrasting Phase-4 weighted current-flow BC against the older centrality zoo.",
    },
    "10.1186/1752-0509-3-102": {
        "band": "review", "must": False,
        "note": "Applies 16 centrality measures (incl. BC, closeness, degree, subgraph) to 18 reconstructed S. cerevisiae metabolic networks and shows no single measure beats random for essential-gene prediction; pair-combinations do. Establishes the empirical case for multi-measure scoring on metab graphs.",
    },
    "10.4137/grsb.s702": {
        "band": "review", "must": False,
        "note": "Methodology review of centrality measures on biological networks. Demonstrates that different centralities rank the same vertices differently and that bio-specific measures (functional substructure ranking) often beat the off-the-shelf ones — supports Phase-4's decision to weight BC by atom-mapped reaction flow rather than use vanilla BC.",
    },
    "10.1109/TCBB.2008.79": {
        "band": "review", "must": False,
        "note": "Tutorial review of metabolic network as a graph: bipartite vs. unipartite projections, stoichiometric vs. reaction-centric, hypergraphs. Maps which graph representation supports which structural analysis. Direct reference for justifying the Phase-4 bipartite EPI300 graph as the right substrate.",
    },
    "10.3389/fmolb.2022.841373": {
        "band": "review", "must": False,
        "note": "Surveys network-based methods for metabolomics interpretation: biochemical reaction networks, mass-spec feature networks, chemical similarity, correlation networks. Adds the post-2015 methods (MetaboRank, MetExplore, gap-mapping) that the older centrality reviews miss.",
    },

    # === METHODOLOGY / FOUNDATIONAL BC (5) ===
    "10.1016/j.socnet.2004.11.009": {
        "band": "methodology", "must": True,
        "note": "Introduces random-walk betweenness (equivalent to current-flow BC), relaxing the shortest-path-only assumption of classical BC by counting how often a node is traversed by a random walk between source/sink pairs. THE foundational paper for the Phase-4 weighted current-flow Δb metric; cite as definition.",
    },
    "10.1080/0022250X.2001.9990249": {
        "band": "methodology", "must": True,
        "note": "Brandes' O(nm) algorithm for shortest-path BC — the algorithmic foundation every subsequent BC implementation (NetworkX, igraph, graph-tool) is built on. Cite when describing how Phase-4 BC is actually computed.",
    },
    "10.2307/3033543": {
        "band": "methodology", "must": False,
        "note": "Freeman's original 1977 definition of BC as a measure of a node's potential for controlling information flow. The historical anchor for any BC discussion; cite once at the top of the methods section.",
    },
    "10.1038/srep19668": {
        "band": "methodology", "must": False,
        "note": "Defines randomized-shortest-path (RSP) betweenness, interpolating between shortest-path BC and random-walk BC via a temperature parameter. Useful contrast for the Phase-4 method's choice of pure current-flow weighting.",
    },
    "10.1007/s11538-018-0526-z": {
        "band": "methodology", "must": False,
        "note": "Measures how stable BC rankings are across alternative reconstructions of the same biological network and across small edge perturbations; finds rankings shift more than commonly assumed. Directly relevant to Phase-4's permutation/null-model design.",
    },

    # === FOUNDATIONAL METABOLIC TOPOLOGY + BC APPLICATIONS (15) ===
    "10.1038/35036627": {
        "band": "biological", "must": False,
        "note": "Jeong et al.'s Nature paper showing metabolic networks of 43 organisms are all scale-free with the same Erdős-like average path length, with a small set of hub metabolites (water, ATP, NADH) dominating connectivity. The paper that launched topological analysis of metabolic networks.",
    },
    "10.1098/rspb.2001.1711": {
        "band": "biological", "must": False,
        "note": "Wagner & Fell show the E. coli metabolic graph has small-world topology with characteristic path length ~3.2. First mapping of small-world / scale-free claims onto a substrate-product metabolic graph; baseline against which later reaction-centric work (Arita 2004, Ma & Zeng 2003) pushed back.",
    },
    "10.1093/bioinformatics/btg177": {
        "band": "biological", "must": False,
        "note": "Ma & Zeng compute closeness and giant-strong-component structure across 80 organism-level metabolic networks. First systematic application of classical centrality measures (including BC indirectly through connector identification) to metab graphs at multi-organism scale.",
    },
    "10.1093/bioinformatics/19.2.270": {
        "band": "biological", "must": False,
        "note": "Companion paper to Ma & Zeng 2003 — describes how the bipartite metabolic graphs were built from KEGG and the cofactor-stripping conventions used downstream. Methodological reference for the substrate-product graph form Phase-4 contrasts with its atom-tracked bipartite.",
    },
    "10.1073/pnas.0306458101": {
        "band": "biological", "must": False,
        "note": "Arita uses atom-tracing on E. coli reactions to show the metabolic 'small world' disappears once carbon-conservation is enforced — average path length is much longer than the cofactor-collapsed graph suggests. Key prior art for the Phase-4 atom-mapped weighting decision.",
    },
    "10.1038/nature03288": {
        "band": "biological", "must": False,
        "note": "Guimerà & Amaral cluster metabolic-network nodes by intra-/inter-module connectivity into ultra-peripheral / connector / hub roles. The 'cartographic' role assignments correlate with essentiality and are an alternative axis to BC for the same question.",
    },
    "10.1126/science.1073374": {
        "band": "biological", "must": False,
        "note": "Ravasz et al. demonstrate hierarchical modularity in 43 metabolic networks (small modules nested in bigger ones). Background for why BC concentrates at module boundaries rather than module interiors.",
    },
    "10.1529/biophysj.104.055723": {
        "band": "biological", "must": False,
        "note": "Mahadevan & Palsson show the high-flux backbone of E. coli's FBA-active subgraph aligns poorly with degree-based hubs — flux centrality and degree centrality disagree. Direct precedent for the Phase-4 split between structural BC and flux-weighted current-flow.",
    },
    "10.1529/biophysj.105.080572": {
        "band": "biological", "must": False,
        "note": "Wunderlich & Mirny predict mutant viability from topology alone (degree, BC, modular position) on E. coli/yeast/B. subtilis metab graphs and reach within ~5% of FBA — supports the claim that topology can substitute for stoichiometry in essentiality screens.",
    },
    "10.1371/journal.pcbi.1002720": {
        "band": "biological", "must": True,
        "note": "Resendis-Antonio et al. compute BC + modularity on E. coli reactions and link high-BC enzymes to FBA-essential reactions across nutrient conditions. Closest precedent for Phase-4's BC × biomass-DAG axis × medium combinations.",
    },
    "10.1073/pnas.0803571105": {
        "band": "biological", "must": False,
        "note": "Smart, Amaral & Ottino model cascading failure when high-BC metabolic nodes are removed and show robustness depends on out-degree heterogeneity. Background for why bridging/cascade metrics complement BC (also picked up by Kim 2019).",
    },
    "10.1016/j.jtbi.2005.04.025": {
        "band": "biological", "must": False,
        "note": "Ghim, Goh & Kahng map single + double-gene lethality on the E. coli metabolic graph and find synthetic lethals concentrate on bridging edges between modules — a structural signature BC partially captures.",
    },
    "10.1073/pnas.0703262104": {
        "band": "biological", "must": False,
        "note": "Kim et al. shift from gene-essentiality to metabolite-essentiality on the E. coli graph: which metabolites, if blocked, would halt growth. Metabolite-side framing that complements Phase-4's reaction-side BC analysis.",
    },
    "10.1073/pnas.1113065109": {
        "band": "biological", "must": False,
        "note": "Barve et al. enumerate 'superessential' reactions present in every viable random metabolic network in a given environment and propose a superessentiality index correlated with cross-genome conservation. Reaction-level baseline against which Phase-4's BC-vs-essentiality claims should be benchmarked.",
    },
    "10.1038/ncomms5015": {
        "band": "biological", "must": False,
        "note": "Notebaart et al. show that functional (FBA-flux) organization of metabolism differs from structural organization, with most essential reactions sitting outside the high-degree core. Direct motivation for Phase-4 weighting BC by atom-mapped flow rather than degree.",
    },

    # === REACTION-CENTRIC + BIPARTITE + CURRENT-FLOW (5) ===
    "10.1186/s12859-019-2897-z": {
        "band": "bipartite", "must": True,
        "note": "Kim, Ashlock & Yoon apply directed BC + bridging + their new 'cascade number' to directed reaction-centric graphs of five microbial GEMs. Methodologically the closest published precedent for Phase-4's directed BC on the EPI300 bipartite; their bridging+cascade hits beat BC alone at essentiality prediction.",
    },
    "10.1371/journal.pcbi.0030059": {
        "band": "bipartite", "must": True,
        "note": "Yu et al. show high-BC 'bottleneck' proteins in yeast PPI are essential even when degree is controlled — establishes BC as a distinct, dynamics-related signal beyond hub-ness. Phase-4's 'BC ≠ degree' framing should cite this as the canonical PPI counterpart.",
    },
    "10.1371/journal.pone.0156034": {
        "band": "bipartite", "must": False,
        "note": "Cooper & Lu define a 'functional centrality' that combines BC with metabolic flux directions and show it predicts which reactions shift flux state under environmental perturbation. A BC variant in spirit very close to what Phase-4's atom-weighted current-flow does on the EPI300 graph.",
    },
    "10.1017/S0031182010000363": {
        "band": "bipartite", "must": False,
        "note": "Cottret & Jourdan review graph methods (BC, k-shortest-path, modularity) applied to parasite metabolic networks for drug-target discovery. Real-world deployment of the same machinery Phase-4 is generalizing.",
    },
    "10.1371/journal.pone.0195226": {
        "band": "bipartite", "must": False,
        "note": "Plata et al. score Plasmodium falciparum reactions for essentiality by combining BC + degree + flux variability and surface novel essential reactions the parametric FBA misses. Strong template for combining BC with FBA in a drug-target pipeline.",
    },
}


# ---- DROP CASES (recorded for traceability; not strictly required) ----
DROP_REASONS = {
    "10.1038/81025": "Short Nat Biotech correspondence; superseded by Wagner & Fell 2001 (10.1098/rspb.2001.1711) which is already included.",
    "10.1186/1752-0509-4-55": "Mazurie et al. cross-species evolution survey — peripheral to BC; broader topology focus.",
    "10.1073/pnas.0711915105": "Citation in Amara 2022 review appears garbled (Jourdan/Vitkup attribution doesn't match any indexed PNAS 2008 paper). Dropped to avoid an unverifiable entry.",
    "10.1371/journal.pone.0079397": "Asgari et al. on controllability/driver-node analysis — adjacent to BC but a different framework (Liu-Slotine-Barabási); peripheral.",
    "10.1371/journal.pone.0054204": "Bánky et al. argue PageRank > BC for drug targets — interesting contrast but not BC-on-metabolic in spirit; dropped for diversity-band budget.",
    "10.1016/j.jmb.2005.09.079": "Croes et al. on weighted shortest-path metabolism — methodology overlaps with Ma & Zeng 2003 and Cooper 2016 which are already in.",
    "10.1093/gbe/evq064": "Cai et al. 'broker genes' is mostly PPI-centric disease analysis; redundant with Yu 2007.",
    "10.1093/bib/bbv115": "Frainay & Jourdan review of metabolomics subnetwork extraction — covered by Amara 2022 review which subsumes it.",
    "10.1093/gigascience/giy014": "Pavlopoulos bipartite-graphs survey — useful but redundant with Lacroix 2008 + Amara 2022 for our scope budget.",
    "10.1186/1471-2105-7-219": "Junker et al. CentiBiN — primarily a software tool; methodology is covered by Koschützki 2008.",
    "10.1155/JBB.2005.96": "Joy et al. PPI high-BC paper — redundant with Yu 2007 which is more cited and equally on-point.",
    "10.1145/1150402.1150471": "Hwang et al. bridging centrality — its essential bridging idea is already used in Kim 2019, which is in.",
    "10.1038/35075138": "Jeong et al. centrality-lethality is PPI-only (yeast PPI); the metabolic-network siblings (Jeong 2000, Wagner 2001, Ma 2003) are already in.",
    "10.1186/1471-2105-6-213": "Thibert et al. protein-residue BC — wrong scale (protein structure, not metabolic network).",
    "10.1371/journal.pcbi.1000140": "Zotenko et al. hub-essentiality dissection — PPI-only; not BC-driven.",
    "10.1093/molbev/msi072": "Hahn & Kern PPI centrality-essentiality — redundant with Jeong 2001 / Yu 2007 framing.",
    "10.1186/1471-2105-8-236": "Hart et al. yeast complex maps — PPI module essentiality, not BC.",
    "10.1186/1752-0509-7-90": "Winterbach et al. molecular-interaction-network topology — generic survey, redundant with Pavlopoulos / Koschützki / Lacroix.",
    "10.1186/1471-2105-4-10": "Pavlopoulos graph-theory tutorial — generic.",
    "10.1038/nrg1272": "Barabási & Oltvai NRG review — abstract is paywalled and not deposited to PubMed, so we cannot honor the 'read the abstract' requirement.",
    "10.1016/S0022-5193(03)00071-7": "Wuchty & Stadler 'centers of networks' — generic graph theory, peripheral to metabolic BC.",
    "10.1016/j.dam.2008.06.035": "Planes & Beasley discrete-math path-finding — abstract unretrievable and peripheral to BC.",
    "10.1371/journal.pone.0247018": "Generic drug-target network-analysis landscape; peripheral focus.",
    "10.1186/gb-2006-7-2-r19": "Samal et al. low-degree-metabolite essentiality — abstract unretrievable from automated sources; dropped for traceability.",
    "10.1186/s12918-018-0552-3": "Nam et al. enzyme-evolution-vs-flux — interesting but BC is incidental; peripheral.",
    "10.1093/bioinformatics/btl039": "Assenov BiNet software — tool paper; methodology covered by Koschützki 2008.",
    "10.1098/rsif.2007.1229": "Estrada subgraph centrality — explicitly out-of-scope per user (subgraph ≠ BC).",
    "10.1038/nrmicro1949": "Feist et al. GEM reconstruction review — not centrality.",
}


def main() -> None:
    cands = {r["doi"]: r for r in csv.DictReader(CAND.open(), delimiter="\t")}
    absts = {r["doi"]: r for r in csv.DictReader(ABS.open(), delimiter="\t")}

    final_rows = []
    notes_blocks = []
    notes_blocks.append("# Selection notes\n\nOne block per candidate. **IN_CORPUS** entries carry abstract + 1–3 sentence summary grounded in the abstract (not the title). **DROPPED** entries carry a short reason.\n")

    # IN-CORPUS section (ordered by band then DOI)
    band_order = ["review", "methodology", "biological", "bipartite"]
    band_titles = {
        "review": "## In corpus — Reviews",
        "methodology": "## In corpus — Methodology / foundational BC",
        "biological": "## In corpus — Metabolic-network topology + biological BC applications",
        "bipartite": "## In corpus — Reaction-centric / bipartite / current-flow",
    }

    for band in band_order:
        notes_blocks.append("\n" + band_titles[band] + "\n")
        for doi, sel in sorted(SELECTION.items(), key=lambda x: (x[1]["band"], x[0])):
            if sel["band"] != band:
                continue
            c = cands.get(doi, {})
            a = absts.get(doi, {})
            star = " ★ must-cite" if sel["must"] else ""
            cite = f"**{c.get('first_author','?')} ({c.get('year','?')})** — *{c.get('title','?')}* — {c.get('journal','?')}"
            pmcid = c.get("pmcid", "")
            pmc_str = f" — PMC{pmcid.replace('PMC','')}" if pmcid else ""
            notes_blocks.append(f"\n### `{doi}`{star}\n")
            notes_blocks.append(f"{cite} — [{doi}](https://doi.org/{doi}){pmc_str}\n")
            notes_blocks.append(f"\n*Why included:* {sel['note']}\n")
            ab_src = a.get("abstract_source", "?")
            ab = a.get("abstract", "").strip() or "_(abstract not retrievable)_"
            notes_blocks.append(f"\n*Abstract (source: {ab_src}):* {ab}\n")
            final_rows.append({
                "doi": doi,
                "pmcid": pmcid,
                "title": c.get("title", ""),
                "year": c.get("year", ""),
                "journal": c.get("journal", ""),
                "first_author": c.get("first_author", ""),
                "band": sel["band"],
                "must_cite": "yes" if sel["must"] else "no",
                "why_included": sel["note"],
                "abstract_source": ab_src,
                "abstract": ab,
            })

    # DROPPED section
    notes_blocks.append("\n## Dropped (recorded for traceability)\n")
    for doi, reason in sorted(DROP_REASONS.items()):
        c = cands.get(doi, {})
        cite = f"**{c.get('first_author','?')} ({c.get('year','?')})** — *{c.get('title','?')}* — {c.get('journal','?')}"
        notes_blocks.append(f"- `{doi}` — {cite}. **Dropped:** {reason}")

    OUT_NOTES.write_text("\n".join(notes_blocks) + "\n")

    fields = ["doi", "pmcid", "title", "year", "journal", "first_author", "band", "must_cite", "why_included", "abstract_source", "abstract"]
    with OUT_FINAL.open("w") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        for r in final_rows:
            for k in ("why_included", "abstract"):
                r[k] = (r.get(k, "") or "").replace("\t", " ").replace("\n", " ")
            w.writerow(r)
    print(f"wrote {OUT_NOTES} and {OUT_FINAL} ({len(final_rows)} corpus entries, {len(DROP_REASONS)} dropped)")


if __name__ == "__main__":
    main()
