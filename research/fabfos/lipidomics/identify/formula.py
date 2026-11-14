"""T2 -- molecular formulas from a neutral monoisotopic mass.

Only 3 of the 29 hits carry a formula from the facility. The other 26 need one
before LIPID MAPS can be asked anything, because that service indexes by formula
and not by mass.

Enumeration is over CHNOPS within lipid-plausible bounds, filtered by
ring-plus-double-bond equivalents and the Kind & Fiehn element-ratio heuristics,
so the output stays short enough to read rather than combinatorial. This is a
constraint on *plausibility*, not a claim of correctness: a formula surviving the
filter is a candidate, and on its own it caps out at MSI level 4.
"""
from __future__ import annotations

from dataclasses import dataclass

MASS = {
    "C": 12.0,
    "H": 1.007825032,
    "N": 14.003074005,
    "O": 15.994914620,
    "P": 30.973761632,
    "S": 31.972071174,
}

# Bounds sized for the 298-984 Da lipid range these hits span.
BOUNDS = {"C": (0, 75), "N": (0, 3), "O": (0, 22), "P": (0, 3), "S": (0, 2)}
RDBE_RANGE = (0.0, 40.0)
HC_RANGE = (0.2, 3.1)
# Deliberately broad. At 5 ppm on a ~900 Da molecule the formula space is
# degenerate -- the three known features come back at ranks 2, 3 and 6 by mass
# alone -- so the discrimination is left to whether LIPID MAPS and RefMet
# actually hold a compound with that formula, rather than to a tighter
# chemical prior that would risk filtering out the right answer.
MAX_RESULTS = 20


@dataclass(frozen=True)
class Formula:
    C: int
    H: int
    N: int
    O: int
    P: int
    S: int
    mass: float
    ppm_error: float
    rdbe: float

    def __str__(self) -> str:
        out = ""
        for el in ("C", "H", "N", "O", "P", "S"):
            n = getattr(self, el)
            if n:
                out += el + (str(n) if n > 1 else "")
        return out


def _rdbe(c: int, h: int, n: int, p: int) -> float:
    return c - h / 2 + n / 2 + p / 2 + 1


def _plausible(c: int, h: int, n: int, o: int, p: int, s: int) -> bool:
    if c == 0 or h == 0:
        return False
    hc = h / c
    if not (HC_RANGE[0] <= hc <= HC_RANGE[1]):
        return False
    if n / c > 1.3 or o / c > 1.2 or p / c > 0.3 or s / c > 0.8:
        return False
    # Phosphorus in biology is phosphate: it brings oxygens with it.
    if p and o < 3 * p:
        return False
    return True


def generate(neutral_mass: float, ppm_tol: float = 5.0,
             max_results: int = MAX_RESULTS) -> list[Formula]:
    """Plausible CHNOPS formulas for a neutral monoisotopic mass, best first."""
    window = neutral_mass * ppm_tol / 1e6
    out: list[Formula] = []
    for p in range(BOUNDS["P"][0], BOUNDS["P"][1] + 1):
        m_p = p * MASS["P"]
        if m_p > neutral_mass:
            break
        for s in range(BOUNDS["S"][0], BOUNDS["S"][1] + 1):
            m_ps = m_p + s * MASS["S"]
            if m_ps > neutral_mass:
                break
            for n in range(BOUNDS["N"][0], BOUNDS["N"][1] + 1):
                m_psn = m_ps + n * MASS["N"]
                if m_psn > neutral_mass:
                    break
                for o in range(BOUNDS["O"][0], BOUNDS["O"][1] + 1):
                    m_psno = m_psn + o * MASS["O"]
                    if m_psno > neutral_mass + window:
                        break
                    rest = neutral_mass - m_psno
                    for c in range(BOUNDS["C"][0], BOUNDS["C"][1] + 1):
                        r = rest - c * MASS["C"]
                        if r < -window:
                            break
                        h = round(r / MASS["H"])
                        if h < 0:
                            continue
                        mass = m_psno + c * MASS["C"] + h * MASS["H"]
                        err = mass - neutral_mass
                        if abs(err) > window:
                            continue
                        if not _plausible(c, h, n, o, p, s):
                            continue
                        rd = _rdbe(c, h, n, p)
                        if not (RDBE_RANGE[0] <= rd <= RDBE_RANGE[1]):
                            continue
                        if abs(rd - round(rd)) > 1e-9:
                            continue  # neutral CHNOPS molecules have integer RDBE
                        out.append(
                            Formula(c, h, n, o, p, s, mass,
                                    -err / neutral_mass * 1e6, rd)
                        )
    # Nearest in mass first; phosphorus-bearing formulas break ties, because
    # every lipid class this experiment is about is a phospholipid.
    out.sort(key=lambda f: (abs(f.ppm_error), 0 if f.P else 1))
    return out[:max_results]


if __name__ == "__main__":
    # Sanity: the three features the facility did annotate must reappear.
    for mass, truth in ((930.69315, "C52H99O11P"),
                        (984.74038, "C56H105O11P"),
                        (757.48775, "C40H72NO10P")):
        got = generate(mass)
        names = [str(f) for f in got]
        rank = names.index(truth) + 1 if truth in names else None
        print(f"{mass:>10.5f}  truth {truth:<14} rank {rank}  of {len(got)}")
        for f in got[:5]:
            print(f"             {str(f):<16} {f.ppm_error:+6.2f} ppm  RDBE {f.rdbe:g}")
