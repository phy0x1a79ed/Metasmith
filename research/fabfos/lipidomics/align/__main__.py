"""Build the four observation feature tables and the ordination page from the MZmine Parquet set."""
import argparse
from pathlib import Path

from . import errors, load, match, ordinate, page, tables

ap = argparse.ArgumentParser(prog="python -m align", description=__doc__)
ap.add_argument("page", type=Path, help="HTML file to write the ordination page to")
out = ap.parse_args().page

inj = load.injections()
checks, frames = {}, {}
for obs, (_, polarity) in load.OBSERVATIONS.items():
    o = inj[inj.observation == obs]
    ions = errors.align_rt(load.reads("ions", inj, obs), polarity)
    model = errors.fit(obs, ions, o)
    o_inj, sp, read_map, raw, mc = match.write(obs, o, ions, model)
    o_inj, scaled, tc = tables.write(obs, inj, ions, o_inj, sp, read_map, raw)
    frames[obs] = (o_inj, scaled)
    checks[obs] = {"error_model": model, "match": mc, "tables": tc}
    print(obs, tc)
for obs, oc in ordinate.run(frames).items():
    checks[obs]["ordination"] = oc
load.save(checks, load.OUT / "checks.json")
page.main(out)
