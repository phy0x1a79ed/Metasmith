"""Generate pipeline_{pos,neg}.mzbatch from reference_lc_tims.mzbatch + reference_lipid_annotation.mzbatch.

The reference is the MZmine 4.8 official LC+TIMS integration-test batch from
mzmine/mzmine GitHub (`mzmine-community/src/test/resources/rawdatafiles/integration_tests/lc_tims/lc_tims_local.mzbatch`).
We surgically:

1. Empty the <File names/> list  → MZmine CLI overrides via `-i <glob>`.
2. Replace the SpectralLibrarySearchModule batchstep with LipidAnnotationModule
   (lifted from reference_lipid_annotation.mzbatch, filtered to bacterial-relevant
   lipid classes and adjusted per polarity).
3. Set Filename placeholder in the CSV export → MZmine CLI overrides via `-o`.

Run:  mamba run -n lipidomics python research/fabfos/lipidomics/build_mzbatch.py
Output: research/fabfos/lipidomics/pipeline_pos.mzbatch, research/fabfos/lipidomics/pipeline_neg.mzbatch
"""
from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).parent
REF_PIPELINE = HERE / "reference_lc_tims.mzbatch"
REF_LIPID = HERE / "reference_lipid_annotation.mzbatch"

# Lipid classes to query. Selected for E. coli + engineered clones — the four
# major bacterial classes (PE, PG, CL) plus enough surrounding classes to catch
# precursors/intermediates and any heterologous output the constructs may produce.
LIPID_CLASSES = [
    # Fatty acyls
    "Fatty Acyls",
    "Fatty acids and Conjugates",
    "FA Free fatty acids",
    "FA Oxidized fatty acids",
    "Fatty esters",
    # Glycerolipids
    "Glycerolipids",
    "Monoradylglycerols",
    "MG Monoacylglycerols",
    "Diradylglycerols",
    "DG Diacylglycerols",
    "Triradylglycerols",
    "TG Triacylglycerols",
    # Glycerophospholipids — bacterial backbone
    "Glycerophospholipids",
    "Glycerophosphoethanolamines",
    "PE Diacylglycerophosphoethanolamines",
    "PE Alkylacylglycerophosphoethanolamines",
    "LPE Monoacylglycerophosphoethanolamines",
    "Glycerophosphoglycerols",
    "PG Diacylglycerophosphoglycerols",
    "LPG Monoacylglycerophosphoglycerols",
    "Glycerophosphates",
    "PA Diacylglycerophosphates",
    "LPA Monoacylglycerophosphates",
    "Glycerophosphoinositols",
    "PI Diacylglycerophosphoinositols",
    "LPI Monoacylglycerophosphoinositols",
    "Glycerophosphoserines",
    "PS Diacylglycerophosphoserines",
    "LPS Monoacylglycerophosphoserines",
    "Phosphatidylcholine",
    "PC Diacylglycerophosphocholines",
    "LPC Monoacylglycerophosphocholines",
    # Cardiolipins (major bacterial class)
    "Cardiolipin",
    "CL Diacylglycerophosphoglycerophosphodiradylglycerols",
    "MLCL Diacylglycerophosphoglycerophosphomonoradylglycerols",
    "DLCL Monoacylglycerophosphoglycerophosphomonoradylglycerols",
]

POS_IGNORE = []  # let MZmine search default positive-mode adducts
NEG_IGNORE = []  # let MZmine search default negative-mode adducts


def load_reference() -> ET.ElementTree:
    return ET.parse(REF_PIPELINE)


def load_lipid_step() -> ET.Element:
    tree = ET.parse(REF_LIPID)
    root = tree.getroot()
    for step in root.findall("batchstep"):
        if step.get("method", "").endswith(".LipidAnnotationModule"):
            return deepcopy(step)
    raise RuntimeError("LipidAnnotation step not found in reference_lipid_annotation.mzbatch")


def configure_lipid_step(step: ET.Element, polarity: str) -> None:
    ignore = POS_IGNORE if polarity == "pos" else NEG_IGNORE
    for p in step.findall("parameter"):
        name = p.get("name", "")
        if name == "Lipid classes":
            for child in list(p):
                p.remove(child)
            for lc in LIPID_CLASSES:
                item = ET.SubElement(p, "item")
                item.text = lc
        elif name == "Advanced":
            ions = p.find("parameter[@name='Ions to ignore']")
            if ions is not None:
                for child in list(ions):
                    ions.remove(child)
                for ion in ignore:
                    item = ET.SubElement(ions, "item")
                    item.text = ion


def transform(polarity: str) -> ET.ElementTree:
    tree = load_reference()
    root = tree.getroot()

    # 1) Empty the input file list — CLI -i overrides at run time.
    #    Also clear any leftover Spectral library files / Metadata file paths
    #    from the reference batch (they pointed at Windows test paths).
    import_step = root.find(
        "batchstep[@method='io.github.mzmine.modules.io.import_rawdata_all.AllSpectralDataImportModule']"
    )
    for pname in ("File names", "Spectral library files"):
        p = import_step.find(f"parameter[@name='{pname}']")
        if p is not None:
            for child in list(p):
                p.remove(child)
    md_param = import_step.find("parameter[@name='Metadata file']")
    if md_param is not None:
        md_param.set("selected", "false")
        cf = md_param.find("current_file")
        if cf is not None:
            cf.text = "metadata.csv"

    # 2) Replace SpectralLibrarySearchModule with LipidAnnotationModule
    children = list(root)
    spec_search = None
    spec_idx = None
    for i, step in enumerate(children):
        if step.get("method", "").endswith(".SpectralLibrarySearchModule"):
            spec_search = step
            spec_idx = i
            break
    if spec_search is None:
        raise RuntimeError("SpectralLibrarySearchModule not found in reference")
    lipid = load_lipid_step()
    configure_lipid_step(lipid, polarity)
    root.remove(spec_search)
    root.insert(spec_idx, lipid)

    # 3) Replace export filename with placeholder (CLI -o overrides)
    export = root.find(
        "batchstep[@method='io.github.mzmine.modules.io.export_features_csv.CSVExportModularModule']"
    )
    if export is not None:
        fn = export.find("parameter[@name='Filename']/current_file")
        if fn is not None:
            fn.text = f"aligned_features_{polarity}.csv"

    return tree


def write_pretty(tree: ET.ElementTree, out: Path) -> None:
    ET.indent(tree, space="    ")
    tree.write(out, encoding="UTF-8", xml_declaration=True)
    # MZmine reference uses standalone="no" — match for parity
    txt = out.read_text()
    txt = re.sub(
        r"<\?xml version='1\.0' encoding='UTF-8'\?>",
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>",
        txt,
        count=1,
    )
    out.write_text(txt)


def main() -> int:
    for pol in ("pos", "neg"):
        tree = transform(pol)
        out = HERE / f"pipeline_{pol}.mzbatch"
        write_pretty(tree, out)
        n_steps = len(tree.getroot().findall("batchstep"))
        print(f"wrote {out.name} ({n_steps} batch steps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
