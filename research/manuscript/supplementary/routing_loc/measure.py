#!/usr/bin/env python3
"""Count the hand-written channel routing nf-core/mag 5.5.0 needs for benchmark E1's configuration,
and the typed declarations Metasmith's E2 transforms carry for the same tool calls.

    python measure.py --nfcore <nf-core/mag 5.5.0 checkout> [--bench <bench-E2>/research/metasmith_benchmark]

--bench refreshes inputs/ from the bench-E2 worktree. Without it, inputs/ is read as committed.
Writes lines.tsv, summary.tsv, modules.tsv and metasmith.tsv next to this script.
"""

import argparse
import ast
import csv
import re
import shutil
import subprocess
import sys
import warnings
from collections import defaultdict
from pathlib import Path

NFCORE_SHA = "56abab5b023ce953c9c43fe21090d156ad0e18af"
HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs"
ARMS = ("short", "long")

# bench-E2 path (relative to research/metasmith_benchmark) -> inputs/ path
INPUT_FILES = {
    "drivers/e1_nfcore/control.config": "e1/control.config",
    "drivers/e1_nfcore/fir.config": "e1/fir.config",
    "drivers/e1_nfcore/run_e1.sbatch": "e1/run_e1.sbatch",
    "results/e1/e1_runtime_by_process.tsv": "e1/e1_runtime_by_process.tsv",
    "results/e1/dag/e1_short.dot": "e1/e1_short.dot",
    "results/e1/dag/e1_long.dot": "e1/e1_long.dot",
    "library/data_types/e2.yml": "e2/e2.yml",
    "drivers/e2_cami.py": "e2/e2_cami.py",
}
E2_SCORING = {"amber", "gold_standard"}
E1_HAND_RERUNS = {"METABAT2_B19_RERUN", "B19_MERGE_BOOKKEEPING", "B19_ROWS_BOOKKEEPING"}

# Process names in e1_runtime_by_process.tsv (the findings map's names) -> nf-core process aliases.
PROCESS_ALIASES = {
    "COMEBIN": {"short": ["COMEBIN_RUNCOMEBIN"], "long": ["COMEBIN_RUNCOMEBIN"]},
    "DASTOOL": {"short": ["DASTOOL_DASTOOL"], "long": ["DASTOOL_DASTOOL"]},
    "FASTATOCONTIG2BIN": {"short": ["DASTOOL_FASTATOCONTIG2BIN"], "long": ["DASTOOL_FASTATOCONTIG2BIN"]},
    "GUNZIP": {"short": ["GUNZIP_SHORTREAD_ASSEMBLIES"], "long": ["GUNZIP_LONGREAD_ASSEMBLIES"]},
    "JGISUMMARIZEBAMCONTIGDEPTHS": {"short": ["METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS_SHORTREAD"],
                                    "long": ["METABAT2_JGISUMMARIZEBAMCONTIGDEPTHS_LONGREAD"]},
    "METABAT2": {"short": ["METABAT2_METABAT2"], "long": ["METABAT2_METABAT2"]},
}

# E1 params that are not in control.config/fir.config: set on the run_e1.sbatch command line.
LAUNCH_PARAMS = {"input": "<samplesheet>", "outdir": "<outdir>"}
# skip_quast entered control.config after E1 long had run QUAST, QUAST_BINS and CONCAT_QUAST_SUMMARY
# to completion (inputs/e1/e1_runtime_by_process.tsv, inputs/e1/e1_long.dot). E1 short ran none.
ARM_PARAMS = {"short": {"skip_quast": True}, "long": {"skip_quast": False}}

# Take-block names that carry a param into a subworkflow, and derived values the if-evaluator needs.
ALIASES = {
    "subworkflows/local/preprocessing_shortread/main.nf": {"val_skip_qc": "params.skip_shortread_qc",
                                                          "val_skip_fastqc": "params.skip_fastqc"},
    "subworkflows/local/preprocessing_longread/main.nf": {"val_skip_qc": "params.skip_longread_qc"},
    "subworkflows/local/utils_nfcore_mag_pipeline/main.nf": {"monochrome_logs": "params.monochrome_logs",
                                                            "email": "params.email",
                                                            "email_on_fail": "params.email_on_fail"},
    "subworkflows/nf-core/utils_nextflow_pipeline/main.nf": {"print_version": "params.version",
                                                            "dump_parameters": "true",
                                                            "outdir": "params.outdir",
                                                            "check_conda_channels": "false"},
    "subworkflows/nf-core/utils_nfschema_plugin/main.nf": {"help": "params.help", "help_full": "params.help_full",
                                                          "parameters_schema": "null",
                                                          "validate_params": "params.validate_params",
                                                          "cli_typecast": "null"},
    # mag.nf:116, gtdb = params.skip_binqc || params.skip_gtdbtk ? false : params.gtdb_db
    "workflows/mag.nf": {"gtdb": "(params.skip_binqc || params.skip_gtdbtk) ? false : params.gtdb_db"},
}
# A function whose body computes a channel join key is routing, not utility code.
ROUTING_FUNCTIONS = {"mappingKey"}

OPERATORS = ("map join combine groupTuple mix branch filter collect flatten transpose multiMap cross ifEmpty set "
             "first toList toSortedList unique distinct concat splitFasta splitCsv collectFile subscribe view tap "
             "last take count buffer reduce flatMap dump").split()
OPERATOR_RE = re.compile(r"\.\s*(%s)\b\s*[({]" % "|".join(OPERATORS))
FACTORY_RE = re.compile(r"\b[Cc]hannel\s*\.\s*(empty|of|fromPath|fromList|value|topic|fromFilePairs)\b")
VERSIONS_RE = re.compile(r"\bch_versions\b|^\s*versions\s*=|topic_versions|softwareVersionsToYAML|ch_collated_versions"
                         r"|[Cc]hannel\s*\.\s*topic\(\s*\"versions\"")
CALL_RE = re.compile(r"(?<![.\w])([A-Za-z_]\w*)\s*\(")
NOT_CALLS = {"if", "for", "while", "switch", "catch", "return", "def", "workflow", "file", "error", "exit", "log",
             "groupKey", "tuple", "path", "val"}
INCLUDE_RE = re.compile(r"^\s*include\s*\{\s*(\w+)(?:\s+as\s+(\w+))?\s*\}\s*from\s*['\"]([^'\"]+)['\"]")


# ---------------------------------------------------------------- lexing

class Line:
    __slots__ = ("no", "raw", "code", "struct", "braces")

    def __init__(self, no, raw):
        self.no, self.raw, self.code, self.struct, self.braces = no, raw, "", "", []

    @property
    def has_code(self):
        return self.code.strip() != ""


def lex(text):
    """Split Groovy into lines of `code` (comments removed) and `struct` (string contents blanked)."""
    raw_lines = text.split("\n")
    lines = [Line(i + 1, r) for i, r in enumerate(raw_lines)]
    stack = ["code"]  # code | lc | bc | sq | dq | tsq | tdq | interp
    interp_depth = []
    li, i, n = 0, 0, len(text)
    code, struct = [], []

    def flush():
        nonlocal code, struct, li
        lines[li].code, lines[li].struct = "".join(code), "".join(struct)
        code, struct = [], []
        li += 1

    while i < n:
        ch, nxt, st = text[i], text[i + 1:i + 2], stack[-1]
        if ch == "\n":
            if st == "lc":
                stack.pop()
            flush()
            i += 1
            continue
        if st in ("code", "interp"):
            if ch == "/" and nxt == "/":
                stack.append("lc"); i += 2; continue
            if ch == "/" and nxt == "*":
                stack.append("bc"); i += 2; continue
            if text.startswith('"""', i):
                stack.append("tdq"); code.append('"""'); struct.append('"""'); i += 3; continue
            if text.startswith("'''", i):
                stack.append("tsq"); code.append("'''"); struct.append("'''"); i += 3; continue
            if ch == '"':
                stack.append("dq"); code.append(ch); struct.append(ch); i += 1; continue
            if ch == "'":
                stack.append("sq"); code.append(ch); struct.append(ch); i += 1; continue
            if st == "interp":
                if ch == "{":
                    interp_depth[-1] += 1
                elif ch == "}":
                    if interp_depth[-1] == 0:
                        interp_depth.pop(); stack.pop(); code.append(ch); struct.append(" "); i += 1; continue
                    interp_depth[-1] -= 1
                code.append(ch); struct.append(" "); i += 1; continue
            code.append(ch); struct.append(ch); i += 1; continue
        if st == "lc":
            i += 1; continue
        if st == "bc":
            if ch == "*" and nxt == "/":
                stack.pop(); i += 2; continue
            i += 1; continue
        # inside a string
        if ch == "\\":
            code.append(text[i:i + 2]); struct.append("  "[:len(text[i:i + 2])]); i += 2; continue
        if st in ("dq", "tdq") and ch == "$" and nxt == "{":
            stack.append("interp"); interp_depth.append(0); code.append("${"); struct.append("  "); i += 2; continue
        if (st == "dq" and ch == '"') or (st == "sq" and ch == "'"):
            stack.pop(); code.append(ch); struct.append(ch); i += 1; continue
        if (st == "tdq" and text.startswith('"""', i)) or (st == "tsq" and text.startswith("'''", i)):
            stack.pop(); code.append(text[i:i + 3]); struct.append(text[i:i + 3]); i += 3; continue
        code.append(ch); struct.append(" "); i += 1
    if li < len(lines):
        flush()
    return lines


# ---------------------------------------------------------------- blocks

class Block:
    def __init__(self, kind, open_line, depth, header, parent):
        self.kind, self.open_line, self.depth, self.header, self.parent = kind, open_line, depth, header, parent
        self.close_line = None
        self.name = None
        self.cond = None
        self.chain_prev = None
        self.children = []


def classify_brace(prefix):
    p = prefix.strip()
    m = re.match(r"^workflow(?:\s+(\w+))?$", p)
    if m:
        return "workflow", m.group(1) or "<entry>", None
    m = re.match(r"^def\s+(\w+)\s*\(.*\)$", p)
    if m:
        return "function", m.group(1), None
    m = re.match(r"^(?:else\s+)?if\s*\((.*)\)$", p)
    if m:
        return ("elif" if p.startswith("else") else "if"), None, m.group(1)
    if p == "else":
        return "else", None, None
    if re.match(r"^workflow\.on\w+$", p):
        return "handler", None, None
    if p.startswith("process") or p.startswith("params"):
        return "config", None, None
    return "closure", None, None


def parse_blocks(lines):
    root = Block("file", 0, -1, "", None)
    stack = [root]
    last_closed = {}
    blocks = []
    for ln in lines:
        s = ln.struct
        seg_start = 0
        for pos, ch in enumerate(s):
            if ch == "{":
                kind, name, cond = classify_brace(s[seg_start:pos])
                if cond is not None:
                    cond = classify_brace(ln.code[seg_start:pos])[2]
                depth = len(stack) - 1
                b = Block(kind, ln.no, depth, s[seg_start:pos], stack[-1])
                b.name, b.cond = name, cond
                if kind in ("elif", "else"):
                    prev = last_closed.get(depth)
                    if prev is not None and prev.kind in ("if", "elif"):
                        b.chain_prev = prev
                    else:
                        raise ValueError(f"line {ln.no}: else without if")
                stack[-1].children.append(b)
                stack.append(b)
                blocks.append(b)
                ln.braces.append((pos, "{", b))
                seg_start = pos + 1
            elif ch == "}":
                b = stack.pop()
                b.close_line = ln.no
                last_closed[len(stack) - 1] = b
                ln.braces.append((pos, "}", b))
                seg_start = pos + 1
            elif ch == ";":
                seg_start = pos + 1
    if len(stack) != 1:
        raise ValueError("unbalanced braces")
    return root, blocks


# ---------------------------------------------------------------- params

def parse_value(v):
    v = v.strip().rstrip(",")
    v = re.sub(r"\s+//.*$", "", v).strip()
    if v == "null":
        return None
    if v in ("true", "false"):
        return v == "true"
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d*", v):
        return float(v)
    m = re.fullmatch(r"(['\"])(.*)\1", v)
    if m:
        return m.group(2)
    return "<expr:%s>" % v


def parse_params_blocks(text):
    out = {}
    depth_params = False
    brace = 0
    for ln in lex(text):
        s = ln.code
        if re.match(r"^\s*params\s*\{", s):
            depth_params, brace = True, 0
        if depth_params:
            m = re.match(r"^\s*(\w+)\s*=\s*(.+)$", s)
            if m and brace == 1:
                out[m.group(1)] = parse_value(m.group(2))
            brace += s.count("{") - s.count("}")
            if brace <= 0:
                depth_params = False
    return out


def resolve_params(nfcore, arm):
    params = parse_params_blocks((nfcore / "nextflow.config").read_text())
    params.update(parse_params_blocks((INPUTS / "e1/fir.config").read_text()))
    params.update(parse_params_blocks((INPUTS / "e1/control.config").read_text()))
    params.update(LAUNCH_PARAMS)
    params.update(ARM_PARAMS[arm])
    return params


UNKNOWN = object()


def evaluate(cond, params, aliases):
    expr = cond
    for _ in range(3):
        for name, sub in aliases.items():
            expr = re.sub(r"(?<![.\w])%s(?![\w(])" % re.escape(name), "(%s)" % sub, expr)
    expr = re.sub(r"\(([^()]*)\)\s*\?\s*([^:]+):\s*(.+)", r"((\2) if (\1) else (\3))", expr)
    expr = re.sub(r"params\.(\w+)", lambda m: repr(params.get(m.group(1))), expr)
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"!(?!=)", " not ", expr)
    expr = re.sub(r"\bnull\b", "None", expr)
    expr = re.sub(r"\btrue\b", "True", expr)
    expr = re.sub(r"\bfalse\b", "False", expr)
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))
    except Exception:
        return UNKNOWN


def prune(blocks, params, aliases):
    """Line numbers of if/else branches that cannot run under params, and the set of evaluated if blocks."""
    dropped = set()
    evaluated = set()
    heads = [b for b in blocks if b.kind == "if"]
    by_prev = {b.chain_prev: b for b in blocks if b.chain_prev is not None}
    for head in heads:
        chain = [head]
        while chain[-1] in by_prev:
            chain.append(by_prev[chain[-1]])
        keep = [True] * len(chain)
        decided = False
        for k, b in enumerate(chain):
            if decided:
                keep[k] = False
                continue
            if b.kind == "else":
                evaluated.add(b)
                break
            v = evaluate(b.cond, params, aliases)
            if v is UNKNOWN:
                break
            evaluated.add(b)
            if v:
                decided = True
            else:
                keep[k] = False
        for k, b in enumerate(chain):
            if keep[k]:
                continue
            lo, hi = b.open_line, b.close_line
            if k > 0 and keep[k - 1] and chain[k - 1].close_line == lo:
                lo += 1
            if k + 1 < len(chain) and keep[k + 1] and chain[k + 1].open_line == hi:
                hi -= 1
            dropped.update(range(lo, hi + 1))
    return dropped, evaluated


# ---------------------------------------------------------------- the nf-core source tree

class NfFile:
    def __init__(self, root, rel):
        self.rel = rel
        self.path = root / rel
        self.lines = lex(self.path.read_text())
        self.root_block, self.blocks = parse_blocks(self.lines)
        self.includes = {}
        for ln in self.lines:
            m = INCLUDE_RE.match(ln.code)
            if m:
                self.includes[m.group(2) or m.group(1)] = (m.group(1), m.group(3), ln.no)
        self.workflows = {b.name: b for b in self.root_block.children if b.kind == "workflow"}
        self.functions = {b.name: b for b in self.root_block.children if b.kind == "function"}
        self.line_block = {}
        for b in self.root_block.children:
            if b.kind in ("workflow", "function"):
                for no in range(b.open_line, b.close_line + 1):
                    self.line_block[no] = b

    def resolve_target(self, target):
        if target.startswith("plugin/"):
            return None
        p = (self.path.parent / target).resolve()
        for cand in (p, p.with_suffix(".nf") if p.suffix != ".nf" else p, p / "main.nf"):
            if cand.is_file():
                return cand
        raise FileNotFoundError(f"{self.rel}: include {target}")


class Tree:
    def __init__(self, root):
        self.root = root.resolve()
        self.files = {}

    def get(self, path):
        rel = str(Path(path).resolve().relative_to(self.root))
        if rel not in self.files:
            self.files[rel] = NfFile(self.root, rel)
        return self.files[rel]

    def is_module(self, path):
        text = Path(path).read_text()
        return re.search(r"^\s*process\s+\w+\s*\{", text, re.M) is not None


def walk(tree, params, arm_tasks=None):
    """Reachable blocks from main.nf's entry workflow under params; kept lines; invoked processes."""
    prune_cache = {}

    def pruned(f):
        if f.rel not in prune_cache:
            prune_cache[f.rel] = prune(f.blocks, params, ALIASES.get(f.rel, {}))
        return prune_cache[f.rel]

    main = tree.get(tree.root / "main.nf")
    entry = main.workflows["<entry>"]
    reached = {}           # (rel, block open line) -> (file, block)
    calls = defaultdict(set)  # (rel, block) -> set of (kind, file rel, name)
    used_includes = defaultdict(set)  # rel -> include line numbers used by kept code
    processes = {}         # alias -> module path
    block_processes = defaultdict(set)
    work = [(main, entry)]
    while work:
        f, b = work.pop()
        key = (f.rel, b.open_line)
        if key in reached:
            continue
        reached[key] = (f, b)
        dropped, _ = pruned(f)
        for no in range(b.open_line, b.close_line + 1):
            if no in dropped:
                continue
            s = f.lines[no - 1].struct
            for m in CALL_RE.finditer(s):
                name = m.group(1)
                if name in NOT_CALLS:
                    continue
                local = f.functions.get(name) or f.workflows.get(name)
                if local is not None and local is not b:
                    work.append((f, local))
                    calls[key].add(("block", f.rel, local.open_line))
                elif name in f.includes:
                    orig, target, inc_line = f.includes[name]
                    used_includes[f.rel].add(inc_line)
                    path = f.resolve_target(target)
                    if path is None:
                        continue
                    if tree.is_module(path):
                        processes[name] = path
                        block_processes[key].add(name)
                        continue
                    g = tree.get(path)
                    tgt = g.workflows.get(orig) or g.functions.get(orig)
                    if tgt is None:
                        raise KeyError(f"{g.rel}: {orig}")
                    work.append((g, tgt))
                    calls[key].add(("block", g.rel, tgt.open_line))
            # NAME.out references keep an include in use even with no call on this line
            for m in re.finditer(r"\b([A-Z][A-Z0-9_]*)\.out\b", s):
                if m.group(1) in f.includes:
                    used_includes[f.rel].add(f.includes[m.group(1)][2])
    return reached, calls, used_includes, processes, block_processes, prune_cache


def transitive_processes(reached, calls, block_processes):
    memo = {}

    def go(key, seen=()):
        if key in memo:
            return memo[key]
        out = set(block_processes.get(key, ()))
        for kind, rel, ref in calls.get(key, ()):
            if kind == "block":
                k2 = (rel, ref)
                if k2 not in seen:
                    out |= go(k2, seen + (key,))
        memo[key] = out
        return out

    return {k: go(k) for k in reached}


def source_has_process(tree, f, b, memo=None):
    """Whether b, ignoring params, can reach a process through its calls."""
    memo = {} if memo is None else memo
    key = (f.rel, b.open_line)
    if key in memo:
        return memo[key]
    memo[key] = False
    found = False
    for no in range(b.open_line, b.close_line + 1):
        for m in CALL_RE.finditer(f.lines[no - 1].struct):
            name = m.group(1)
            local = f.functions.get(name) or f.workflows.get(name)
            if local is not None and local is not b:
                found = found or source_has_process(tree, f, local, memo)
            elif name in f.includes:
                orig, target, _ = f.includes[name]
                path = f.resolve_target(target)
                if path is None:
                    continue
                if tree.is_module(path):
                    found = True
                else:
                    g = tree.get(path)
                    tgt = g.workflows.get(orig) or g.functions.get(orig)
                    found = found or source_has_process(tree, g, tgt, memo)
    memo[key] = found
    return found


# ---------------------------------------------------------------- classification

def statements(f, b, lines_kept):
    """Group the kept lines of a workflow block into statements. Control lines stand alone."""
    out = []
    cur = []
    depth = 0
    control_kinds = {"workflow", "if", "elif", "else", "function", "handler"}
    for no in range(b.open_line, b.close_line + 1):
        if no not in lines_kept:
            continue
        ln = f.lines[no - 1]
        if not ln.has_code:
            continue
        ctrl = [x for x in ln.braces if x[2].kind in control_kinds]
        stripped = ln.struct.strip()
        is_label = re.match(r"^(take|main|emit)\s*:", stripped) is not None
        if (ctrl and depth == 0) or is_label:
            if cur:
                out.append(cur)
                cur = []
            out.append([no])
            continue
        cur.append(no)
        for ch in ln.struct:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
        for _, ch, blk in ln.braces:
            if blk.kind == "closure":
                depth += 1 if ch == "{" else -1
        nxt = next((f.lines[k - 1] for k in range(no + 1, b.close_line + 1)
                    if k in lines_kept and f.lines[k - 1].has_code), None)
        cont = depth > 0 or re.search(r"(=|\?|:|,|\(|\+|\|\||&&|->)\s*$", ln.struct.rstrip()) is not None
        if nxt is not None and re.match(r"^\s*[.?:]", nxt.struct):
            cont = True
        if not cont:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def enclosing(f, no):
    """Kinds of blocks enclosing line `no` (outermost first), including blocks opened on the line."""
    kinds = []
    b = f.line_block.get(no)
    if b is None:
        return kinds

    def descend(blk):
        kinds.append(blk)
        for c in blk.children:
            if c.open_line <= no <= c.close_line:
                descend(c)
                return
    descend(b)
    return kinds


def classify_file(f, keep_lines, evaluated):
    """bucket, subtype for each kept line of f."""
    result = {}
    for no in sorted(keep_lines):
        ln = f.lines[no - 1]
        if no not in f.line_block:
            if INCLUDE_RE.match(ln.code):
                result[no] = ("invocation", "include")
            else:
                result[no] = ("other", "top-level")
    for blk in f.root_block.children:
        if blk.kind == "function":
            routing_fn = blk.name in ROUTING_FUNCTIONS
            for no in range(blk.open_line, blk.close_line + 1):
                if no not in keep_lines or not f.lines[no - 1].has_code:
                    continue
                if routing_fn and is_control_line(f, no, evaluated):
                    result[no] = ("config", "param-if")
                else:
                    result[no] = ("routing", "join-key function") if routing_fn else ("other", "function")
        elif blk.kind == "workflow":
            classify_workflow(f, blk, keep_lines, evaluated, result)
    return result


def is_control_line(f, no, evaluated, any_if=False):
    ln = f.lines[no - 1]
    s = ln.struct.strip()
    if not ln.braces:
        return False
    ifs = [x for x in ln.braces if x[2].kind in ("if", "elif", "else")]
    if not ifs:
        return False
    if not any_if and not any(x[2] in evaluated or chain_evaluated(x[2], evaluated) for x in ifs):
        return False
    rest = re.sub(r"(?:else\s+)?if\s*\(.*\)", "", s)
    rest = re.sub(r"\belse\b", "", rest)
    return re.fullmatch(r"[{}\s]*", rest) is not None


def chain_evaluated(b, evaluated):
    while b is not None:
        if b in evaluated:
            return True
        b = b.chain_prev
    return False


def classify_workflow(f, wf, keep_lines, evaluated, result):
    section = None
    sec_of = {}
    for no in range(wf.open_line, wf.close_line + 1):
        m = re.match(r"^\s*(take|main|emit)\s*:", f.lines[no - 1].struct)
        if m:
            section = m.group(1)
        sec_of[no] = section
    for st in statements(f, wf, keep_lines):
        first = f.lines[st[0] - 1]
        text = " ".join(f.lines[k - 1].struct for k in st)
        s0 = first.struct.strip()
        sec = sec_of[st[0]]
        if len(st) == 1 and (st[0] == wf.open_line or st[0] == wf.close_line) and \
                any(x[2] is wf for x in first.braces):
            result[st[0]] = ("invocation", "workflow header")
            continue
        if re.match(r"^(take|main|emit)\s*:", s0):
            result[st[0]] = ("invocation", "label")
            continue
        if sec == "take":
            for k in st:
                result[k] = ("invocation", "take")
            continue
        if len(st) == 1 and first.braces and any(x[2].kind in ("if", "elif", "else") for x in first.braces) \
                and not any(x[2].kind == "closure" for x in first.braces):
            inside_closure = any(b.kind == "closure" for b in enclosing(f, st[0])
                                 if not any(x[2] is b for x in first.braces))
            if inside_closure:
                result[st[0]] = ("routing", "closure body")
            elif is_control_line(f, st[0], evaluated):
                result[st[0]] = ("config", "param-if")
            elif is_control_line(f, st[0], evaluated, any_if=True):
                result[st[0]] = ("config", "data-if")
            else:
                result[st[0]] = ("other", "control")
            continue
        if len(st) == 1 and first.braces and any(x[2].kind == "handler" for x in first.braces):
            result[st[0]] = ("other", "handler")
            continue
        encl = enclosing(f, st[0])
        in_closure = any(b.kind == "closure" for b in encl if not any(x[2] is b and x[1] == "{" for x in first.braces))
        in_handler = any(b.kind == "handler" for b in encl)
        if in_handler:
            for k in st:
                result[k] = ("other", "handler")
            continue
        if VERSIONS_RE.search(first.struct) or (sec == "emit" and re.match(r"^versions\s*=", s0)):
            for k in st:
                result[k] = ("versions", "")
            continue
        if in_closure:
            for k in st:
                result[k] = ("routing", "closure body")
            continue
        has_op = OPERATOR_RE.search(text) or FACTORY_RE.search(text) or \
            any(x[2].kind == "closure" for k in st for x in f.lines[k - 1].braces)
        multiqc = "multiqc" in text.lower()
        call = re.match(r"^([A-Z][A-Z0-9_]*)\s*\(", s0)
        if call:
            for k in st:
                lk = f.lines[k - 1]
                if OPERATOR_RE.search(lk.struct) or FACTORY_RE.search(lk.struct) or \
                        any(x[2].kind == "closure" for x in lk.braces) or \
                        any(b.kind == "closure" for b in enclosing(f, k) if b.open_line != k):
                    result[k] = ("routing", "operator in call")
                else:
                    result[k] = ("invocation", "call")
            continue
        if has_op:
            sub = "multiqc" if multiqc else ("factory" if FACTORY_RE.search(text) and not OPERATOR_RE.search(text)
                                             and not any(x[2].kind == "closure" for k in st
                                                         for x in f.lines[k - 1].braces) else "operator")
            for k in st:
                result[k] = ("routing", sub)
            continue
        if "params." in text and "?" in text:
            for k in st:
                result[k] = ("config", "param-ternary")
            continue
        if re.match(r"^(def\s+)?\w+\s*=\s*[\w.]+\s*$", text.strip()):
            for k in st:
                result[k] = ("invocation", "emit" if sec == "emit" else "alias")
            continue
        for k in st:
            result[k] = ("other", "statement")


# ---------------------------------------------------------------- modules and config

def module_lines(path):
    """Non-blank, non-comment lines of a process module, without its stub: section (never run)."""
    lines = lex(Path(path).read_text())
    out = 0
    in_stub = False
    for ln in lines:
        if re.match(r"^\s*stub\s*:", ln.struct):
            in_stub = True
        if in_stub:
            if ln.struct.strip() == "}" and ln.raw.startswith("}"):
                in_stub = False
            continue
        if ln.has_code:
            out += 1
    return out


def module_io(path):
    lines = lex(Path(path).read_text())
    section = None
    decls = {"input": [], "output": []}
    buf = ""
    for ln in lines:
        s = ln.struct.strip()
        m = re.match(r"^(input|output|when|script|shell|exec|stub)\s*:", s)
        if m:
            if buf:
                decls[section].append(buf)
                buf = ""
            section = m.group(1) if m.group(1) in ("input", "output") else None
            continue
        if section and s:
            code = ln.code.strip()
            if re.match(r"^(tuple|path|val|env|stdin|stdout|eval|file)\b", code) and buf:
                decls[section].append(buf)
                buf = ""
            buf = (buf + " " + code).strip()
    if buf and section:
        decls[section].append(buf)
    return decls


def signature(decl):
    d = re.sub(r",\s*(emit|topic|optional|arity)\s*:\s*[^,]+", "", decl)
    is_versions = re.search(r"versions", decl) is not None and (
        "versions.yml" in decl or "topic: versions" in decl.replace("  ", " ") or "emit: versions" in decl)
    quals = re.findall(r"\b(val|path|env|eval|stdin|stdout|file)\b\s*(\(([^()]*(?:\([^()]*\))?[^()]*)\)|\"[^\"]*\"|'[^']*')?", d)
    parts = []
    for q, _, arg in quals:
        if q == "val" and arg and re.fullmatch(r"\w+", arg.strip()):
            parts.append(f"val({arg.strip()})")
        else:
            parts.append(q)
    head = "tuple " if d.strip().startswith("tuple") else ""
    return head + ", ".join(parts), is_versions


def modules_config_entries(nfcore, aliases):
    text = (nfcore / "conf/modules.config").read_text()
    lines = lex(text)
    entries = []
    stack = []
    for ln in lines:
        for pos, ch in enumerate(ln.struct):
            if ch == "{":
                pre = ln.code[:pos]
                m = re.search(r"withName\s*:\s*['\"]?([^'\"{]+?)['\"]?\s*$", pre)
                stack.append([m.group(1).strip() if m else None, ln.no, 0])
            elif ch == "}":
                sel, start, _ = stack.pop()
                if sel is not None:
                    entries.append((sel, start, ln.no))
    out = []
    for sel, start, end in entries:
        matched = [a for a in aliases if re.fullmatch(sel, a)]
        if matched:
            n = sum(1 for ln in lines[start - 1:end] if ln.has_code)
            out.append((sel, start, end, n, matched))
    return out


def meta_keys(texts):
    keys = set()
    meta_var = r"(?:meta\w*|\w+_meta|metas)"
    for t in texts:
        for m in re.finditer(r"\b%s\s*\.\s*([a-z_]\w*)\b(?!\s*\()" % meta_var, t):
            keys.add(m.group(1))
        for m in re.finditer(r"\b%s\s*\[\s*['\"](\w+)['\"]\s*\]" % meta_var, t):
            keys.add(m.group(1))
        for m in re.finditer(r"\b%s\s*[+-]\s*\[([^\]]*)\]" % meta_var, t):
            keys.update(re.findall(r"(\w+)\s*:", m.group(1)))
        for m in re.finditer(r"subMap\(\s*\[?([^)\]]*)\]?\s*\)", t):
            keys.update(re.findall(r"['\"](\w+)['\"]", m.group(1)))
        for m in re.finditer(r"\[\s*\[\s*(\w+)\s*:", t):
            keys.add(m.group(1))
        if re.search(r"\bdef\s+meta\w*\s*=\s*\[", t):
            keys.update(re.findall(r"(?<![\w.])(\w+)\s*:(?!:)", t.split("=", 1)[1]))
    return keys


# ---------------------------------------------------------------- Metasmith side

def parse_e2_types(path):
    """Minimal reader for e2.yml: type -> {extends: [...], properties: {...}}."""
    types = {}
    cur = None
    section = None
    for raw in Path(path).read_text().split("\n"):
        line = re.sub(r"\s+#.*$", "", raw) if not raw.strip().startswith("#") else ""
        if not line.strip():
            continue
        ind = len(line) - len(line.lstrip())
        s = line.strip()
        if ind == 2 and s.endswith(":"):
            cur = s[:-1]
            types[cur] = {"extends": [], "properties": {}}
            section = None
        elif ind >= 4 and cur and section == "extends" and s.startswith("- "):
            types[cur]["extends"].append(s[2:].strip())
        elif ind == 4 and cur:
            section = s[:-1] if s.endswith(":") else None
        elif ind == 6 and cur and section == "properties":
            k, _, v = s.partition(":")
            types[cur]["properties"][k.strip()] = v.strip()
    return types


def parse_transform(path):
    tree = ast.parse(Path(path).read_text())
    reqs, prods, parents, group_by = [], [], 0, None
    var_type = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            call = node.value
            fn = call.func
            if isinstance(fn, ast.Attribute) and fn.attr in ("AddRequirement", "AddProduct"):
                arg = call.args[0]
                tname = arg.args[0].value
                var = node.targets[0].id
                var_type[var] = tname
                par = [k for k in call.keywords if k.arg == "parents"]
                n_par = len(par[0].value.elts) if par else 0
                parents += n_par
                (reqs if fn.attr == "AddRequirement" else prods).append((var, tname, n_par))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "TransformInstance":
            for k in node.keywords:
                if k.arg == "group_by":
                    group_by = var_type.get(k.value.id, k.value.id)
    return reqs, prods, parents, group_by


NEXTFLOW_TOKENS = re.compile(r"\b(Channel|channel\.|groupTuple|multiMap|combine\(|\.mix\(|workflow\s*\{|process\s+\w+\s*\{"
                             r"|take:|emit:|\.join\(\s*\w+\s*,\s*by)")


def python_code_lines(path):
    n = 0
    for raw in Path(path).read_text().split("\n"):
        s = raw.strip()
        if s and not s.startswith("#"):
            n += 1
    return n


# ---------------------------------------------------------------- main

def copy_inputs(bench):
    for src, dst in INPUT_FILES.items():
        d = INPUTS / dst
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bench / src, d)
    tdir = INPUTS / "e2/transforms"
    tdir.mkdir(parents=True, exist_ok=True)
    for p in sorted((bench / "library/transforms/e2").glob("*.py")):
        shutil.copy2(p, tdir / p.name)
    findings = (bench / "findings/E1_E2_REPRODUCTION.md").read_text()
    m = re.search(r"^## nf-core processes against metasmith steps\n.*?(?=^## )", findings, re.M | re.S)
    (INPUTS / "e1/process_map.md").write_text(
        "<!-- excerpt of findings/E1_E2_REPRODUCTION.md, copied by measure.py -->\n" + m.group(0))


def ran_processes():
    """arm -> {nf-core alias: n_tasks} for processes with at least one completed task."""
    out = {a: {} for a in ARMS}
    with open(INPUTS / "e1/e1_runtime_by_process.tsv") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            name, arm, n = row["process"], row["arm"], int(row["n_tasks"])
            if name in E1_HAND_RERUNS or n == 0:
                continue
            for alias in PROCESS_ALIASES.get(name, {}).get(arm, [name]):
                out[arm][alias] = n
    return out


def dag_processes(arm):
    text = (INPUTS / f"e1/e1_{arm}.dot").read_text()
    return {m.group(1).split(":")[-1] for m in re.finditer(r'label="(NFCORE_MAG:[A-Z0-9_:]+)"', text)}


def main():
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nfcore", required=True, type=Path, help="nf-core/mag checkout at tag 5.5.0")
    ap.add_argument("--bench", type=Path, help="bench-E2 research/metasmith_benchmark; refreshes inputs/")
    ap.add_argument("--out", type=Path, default=HERE)
    args = ap.parse_args()

    sha = subprocess.run(["git", "-C", str(args.nfcore), "rev-parse", "HEAD"], capture_output=True, text=True,
                         check=True).stdout.strip()
    if sha != NFCORE_SHA:
        sys.exit(f"nf-core/mag checkout is {sha}, expected 5.5.0 = {NFCORE_SHA}")
    if args.bench:
        copy_inputs(args.bench)

    ran = ran_processes()
    tree = Tree(args.nfcore)
    per_arm = {}
    notes = []
    for arm in ARMS:
        params = resolve_params(args.nfcore, arm)
        reached, calls, used_inc, procs, block_procs, prune_cache = walk(tree, params)
        invoked = set(procs)
        dag = dag_processes(arm)
        if invoked != dag:
            sys.exit(f"{arm}: processes invoked by pruned code differ from E1's DAG:\n"
                     f"  code only: {sorted(invoked - dag)}\n  DAG only: {sorted(dag - invoked)}")
        notes.append(f"{arm}: {len(invoked)} processes invoked by the pruned code = the {len(dag)} in E1's DAG")
        trans = transitive_processes(reached, calls, block_procs)
        active = {}
        for key, (f, b) in reached.items():
            tp = trans[key]
            if b.kind == "workflow" and source_has_process(tree, f, b) and not (tp & set(ran[arm])):
                continue
            active[key] = (f, b)
        keep = defaultdict(set)
        evaluated = {}
        for key, (f, b) in active.items():
            dropped, ev = prune_cache[f.rel]
            evaluated[f.rel] = ev
            for no in range(b.open_line, b.close_line + 1):
                if no not in dropped and f.lines[no - 1].has_code:
                    keep[f.rel].add(no)
        for rel, lines_used in used_inc.items():
            f = tree.files[rel]
            for no in lines_used:
                b = f.line_block.get(no)
                keep[rel].add(no)
            evaluated.setdefault(rel, prune_cache[rel][1])
        per_arm[arm] = dict(keep=keep, evaluated=evaluated, reached=reached, active=active, procs=procs,
                            invoked=invoked)

    # union classification
    touched = sorted(set(per_arm["short"]["reached"]) | set(per_arm["long"]["reached"]))
    touched_files = sorted({rel for rel, _ in touched})
    rows = []
    bucket_lines = defaultdict(lambda: defaultdict(set))  # scope -> bucket -> {(rel, no)}
    for rel in touched_files:
        f = tree.files[rel]
        union_keep = per_arm["short"]["keep"].get(rel, set()) | per_arm["long"]["keep"].get(rel, set())
        ev = per_arm["short"]["evaluated"].get(rel, set()) | per_arm["long"]["evaluated"].get(rel, set())
        cls = classify_file(f, union_keep, ev)
        for ln in f.lines:
            if not ln.has_code:
                continue
            arms_in = [a for a in ARMS if ln.no in per_arm[a]["keep"].get(rel, set())]
            if arms_in:
                bucket, sub = cls.get(ln.no, ("other", "unclassified"))
                status = "exercised"
                for a in arms_in:
                    bucket_lines[a][bucket].add((rel, ln.no))
                bucket_lines["union"][bucket].add((rel, ln.no))
            else:
                bucket, sub, status = "", "", "not exercised"
            rows.append(dict(file=rel, line=ln.no, status=status, arms=",".join(arms_in), bucket=bucket,
                             subtype=sub, text=ln.raw.strip()))

    out = args.out
    with open(out / "lines.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # modules and modules.config
    mod_rows = []
    mod_totals = {}
    config_totals = {}
    for scope in ARMS + ("union",):
        aliases = set(ran["short"]) | set(ran["long"]) if scope == "union" else set(ran[scope])
        procs = {**per_arm["short"]["procs"], **per_arm["long"]["procs"]}
        missing = aliases - set(procs)
        if missing:
            sys.exit(f"{scope}: ran but not invoked by the pruned code: {sorted(missing)}")
        mods = {}
        for a in sorted(aliases):
            mods.setdefault(procs[a], []).append(a)
        mod_totals[scope] = sum(module_lines(p) for p in mods)
        entries = modules_config_entries(args.nfcore, aliases)
        config_totals[scope] = sum(e[3] for e in entries)
        if scope == "union":
            for p, al in sorted(mods.items()):
                mod_rows.append(dict(kind="module", name=str(Path(p).relative_to(tree.root)),
                                     processes="|".join(al), lines=module_lines(p),
                                     short_tasks=sum(ran["short"].get(a, 0) for a in al),
                                     long_tasks=sum(ran["long"].get(a, 0) for a in al)))
            for sel, start, end, n, matched in entries:
                mod_rows.append(dict(kind="modules.config", name=f"withName: {sel} (conf/modules.config:{start}-{end})",
                                     processes="|".join(matched), lines=n,
                                     short_tasks=sum(ran["short"].get(a, 0) for a in matched),
                                     long_tasks=sum(ran["long"].get(a, 0) for a in matched)))
            union_mods = mods
            union_entries = entries
    with open(out / "modules.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(mod_rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(mod_rows)

    # nf-core counterparts: tuple signatures and meta keys
    in_sigs, out_sigs, n_in, n_out, n_ver = set(), set(), 0, 0, 0
    for p in union_mods:
        io = module_io(p)
        for d in io["input"]:
            sig, _ = signature(d)
            in_sigs.add(sig); n_in += 1
        for d in io["output"]:
            sig, is_ver = signature(d)
            if is_ver:
                n_ver += 1
                continue
            out_sigs.add(sig); n_out += 1
    exercised_text = [tree.files[r["file"]].lines[r["line"] - 1].code for r in rows
                      if r["status"] == "exercised" and r["bucket"] != "other"]
    cls_by_line = {(r["file"], r["line"]): r["bucket"] for r in rows if r["status"] == "exercised"}
    # statements spanning lines (def meta = [ ... ]) need joined text
    joined = []
    for rel in touched_files:
        f = tree.files[rel]
        keep = per_arm["short"]["keep"].get(rel, set()) | per_arm["long"]["keep"].get(rel, set())
        for blk in f.root_block.children:
            if blk.kind == "workflow":
                for st in statements(f, blk, keep):
                    if cls_by_line.get((rel, st[0])) != "other":
                        joined.append(" ".join(f.lines[k - 1].code for k in st))
    wf_keys = meta_keys(exercised_text + joined)
    cfg_lines = lex((args.nfcore / "conf/modules.config").read_text())
    cfg_text = [ln.code for sel, s, e, n, m in union_entries for ln in cfg_lines[s - 1:e]]
    cfg_keys = meta_keys(cfg_text)

    # Metasmith side
    e2_types = parse_e2_types(INPUTS / "e2/e2.yml")
    transforms = {}
    for p in sorted((INPUTS / "e2/transforms").glob("*.py")):
        if p.stem in E2_SCORING:
            continue
        transforms[p.stem] = parse_transform(p)
    referenced = set()
    ms_rows = []
    nf_hits = []
    for name, (reqs, prods, parents, gb) in transforms.items():
        for _, t, _ in reqs + prods:
            referenced.add(t.split("::", 1)[1])
        env_reqs = [r for r in reqs if r[1].endswith(".env")]
        ms_rows.append(dict(transform=name, requires_data=len(reqs) - len(env_reqs), requires_env=len(env_reqs),
                            produces=len(prods), parents_edges=parents, group_by=gb or "",
                            python_lines=python_code_lines(INPUTS / "e2/transforms" / f"{name}.py")))
        for i, raw in enumerate((INPUTS / "e2/transforms" / f"{name}.py").read_text().split("\n"), 1):
            if NEXTFLOW_TOKENS.search(raw):
                nf_hits.append(f"{name}.py:{i}")
    for raw in (INPUTS / "e2/e2_cami.py").read_text().split("\n"):
        if NEXTFLOW_TOKENS.search(raw):
            nf_hits.append("e2_cami.py")
    closure = set(referenced)
    frontier = list(referenced)
    while frontier:
        t = frontier.pop()
        for parent in e2_types.get(t, {}).get("extends", []):
            if parent not in closure:
                closure.add(parent)
                frontier.append(parent)
    unknown = closure - set(e2_types)
    if unknown:
        sys.exit(f"types not in e2.yml: {sorted(unknown)}")
    data_types = sorted(t for t in closure if not t.endswith(".env"))
    env_types = sorted(t for t in closure if t.endswith(".env"))
    ancestors_only = sorted(t for t in closure - referenced)
    props_data = sum(len(e2_types[t]["properties"]) for t in data_types)
    props_data_nodesc = sum(1 for t in data_types for k in e2_types[t]["properties"] if k != "_")
    props_env = sum(len(e2_types[t]["properties"]) for t in env_types)
    extends_edges = sum(len(e2_types[t]["extends"]) for t in data_types)
    with open(out / "metasmith.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ms_rows[0]), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(ms_rows)

    # summary
    S = []

    def add(section, metric, value, note=""):
        S.append(dict(section=section, metric=metric, value=value, note=note))

    add("source", "nf-core/mag commit", sha, "tag 5.5.0")
    for scope in ("union",) + ARMS:
        bl = bucket_lines[scope]
        wf_total = sum(len(v) for v in bl.values())
        routing = len(bl["routing"])
        denom = wf_total + mod_totals[scope] + config_totals[scope]
        for b in ("routing", "config", "invocation", "versions", "other"):
            add(scope, f"workflow lines: {b}", len(bl[b]))
        add(scope, "workflow lines: PRUNED (exercised)", wf_total, "headline denominator, workflow+subworkflow only")
        add(scope, "process module lines (modules/**/main.nf, no stub)", mod_totals[scope])
        add(scope, "conf/modules.config entry lines", config_totals[scope])
        add(scope, "routing % of workflow lines", f"{100 * routing / wf_total:.1f}")
        add(scope, "routing % of workflow lines without `other`", f"{100 * routing / (wf_total - len(bl['other'])):.1f}",
            "drops non-channel Groovy: validation, banners, citations, email")
        add(scope, "routing % of workflow + modules + modules.config", f"{100 * routing / denom:.1f}",
            f"denominator {denom}")
    ft_lines = sum(1 for r in rows)
    add("union", "FILES TOUCHED: files", len(touched_files))
    add("union", "FILES TOUCHED: lines (upper bound)", ft_lines, "every non-blank non-comment line of each file")
    sub = defaultdict(int)
    for r in rows:
        if r["status"] == "exercised":
            sub[(r["bucket"], r["subtype"])] += 1
    for (b, s), n in sorted(sub.items()):
        add("union subtypes", f"{b}/{s or '-'}", n)
    boiler = sum(1 for r in rows if r["status"] == "exercised" and
                 (r["file"].startswith("subworkflows/nf-core/utils_") or r["file"] == "main.nf" or
                  (r["file"].endswith("utils_nfcore_mag_pipeline/main.nf"))))
    add("union", "of which nf-core template/utility files", boiler,
        "main.nf, subworkflows/nf-core/utils_*, utils_nfcore_mag_pipeline")
    for a in ARMS:
        add(a, "processes ran (tasks > 0)", len(ran[a]), "B19 hand reruns excluded")
    add("union", "processes ran (tasks > 0)", len(set(ran["short"]) | set(ran["long"])))
    add("nf-core counterpart", "process input declarations", n_in)
    add("nf-core counterpart", "distinct input tuple signatures", len(in_sigs), "val names kept, path globs dropped")
    add("nf-core counterpart", "process output declarations (excl. versions)", n_out)
    add("nf-core counterpart", "distinct output tuple signatures", len(out_sigs))
    add("nf-core counterpart", "distinct input+output signatures", len(in_sigs | out_sigs))
    add("nf-core counterpart", "versions output declarations", n_ver)
    add("nf-core counterpart", "meta keys read/set in exercised workflow code", len(wf_keys), " ".join(sorted(wf_keys)))
    add("nf-core counterpart", "meta keys read in their modules.config entries", len(cfg_keys), " ".join(sorted(cfg_keys)))
    add("metasmith", "transforms", len(transforms), "union of both arms, amber and gold_standard excluded")
    add("metasmith", "requires (data) declarations", sum(r["requires_data"] for r in ms_rows))
    add("metasmith", "requires (env) declarations", sum(r["requires_env"] for r in ms_rows))
    add("metasmith", "produces declarations", sum(r["produces"] for r in ms_rows))
    add("metasmith", "parents= lineage edges", sum(r["parents_edges"] for r in ms_rows))
    add("metasmith", "group_by declarations", sum(1 for r in ms_rows if r["group_by"]))
    add("metasmith", "distinct data types (referenced + ancestors)", len(data_types), " ".join(data_types))
    add("metasmith", "of which ancestors only", len(ancestors_only), " ".join(ancestors_only))
    add("metasmith", "extends edges on those types", extends_edges)
    add("metasmith", "properties declared on those data types", props_data, f"{props_data_nodesc} without the `_` description")
    add("metasmith", "env types", len(env_types), " ".join(env_types))
    add("metasmith", "properties declared on env types", props_env)
    add("metasmith", "hand-written routing lines", len(nf_hits),
        "Nextflow DSL tokens in E2 transforms and e2_cami.py: " + (", ".join(nf_hits) or "none"))
    md_keys = set()
    for name in transforms:
        t = (INPUTS / "e2/transforms" / f"{name}.py").read_text()
        md_keys.update(re.findall(r"read_text\(\)\)\[[\"'](\w+)[\"']\]", t))
        md_keys.update(re.findall(r"read_set\[[\"'](\w+)[\"']\]", t))
    add("metasmith", "read_metadata keys read inside transform protocols", len(md_keys), " ".join(sorted(md_keys)))
    add("metasmith", "transform Python lines (non-blank, non-comment)", sum(r["python_lines"] for r in ms_rows),
        "whole files: declarations + protocol + helpers")
    for nline in notes:
        add("check", "DAG agreement", nline)
    with open(out / "summary.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["section", "metric", "value", "note"], delimiter="\t",
                           lineterminator="\n")
        w.writeheader()
        w.writerows(S)
    for r in S:
        print(f"{r['section']:22} {r['metric']:55} {r['value']}  {r['note'][:90]}")


if __name__ == "__main__":
    main()
