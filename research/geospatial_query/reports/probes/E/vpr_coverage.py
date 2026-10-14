"""For every test photo: how many Panoramax pictures (other collections) lie within 300 m of the true location."""
import csv, json, os, time, requests
H = os.path.dirname(os.path.abspath(__file__)); UA = {"User-Agent": "geoprobe/0.1 (research)"}
out = []
for r in csv.DictReader(open(os.path.join(H, "testset.csv"))):
    own = r["source_url"].split("/collections/")[1].split("/")[0] if r["source"] == "panoramax" else ""
    lat, lon = float(r["true_lat"]), float(r["true_lon"])
    j = requests.get("https://api.panoramax.xyz/api/search", params=dict(place_position=f"{lon},{lat}", place_distance="0-300", limit=200), headers=UA, timeout=60).json()
    f = j.get("features", [])
    other = [x for x in f if x["collection"] != own]
    out.append(dict(id=r["id"], source=r["source"], n_300m=len(f), n_other_collections=len(other), n_collections=len({x["collection"] for x in other})))
    print(out[-1], flush=True); time.sleep(0.5)
json.dump(out, open(os.path.join(H, "vpr_coverage.json"), "w"), indent=1)
print(sum(o["n_other_collections"] >= 5 for o in out), "photos with >=5 other-collection refs within 300 m")
