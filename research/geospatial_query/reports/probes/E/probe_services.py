"""Evidence for the hosted geolocators (GeoSpy/Graylark Raven, Picarta) and the PIGEON weights statement. Writes services.json."""
import base64, json, os, re, requests
H = os.path.dirname(os.path.abspath(__file__)); UA = {"User-Agent": "Mozilla/5.0"}
ev = {}
def txt(r, n=300): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", r.text))[:n]
img = base64.b64encode(open(os.path.join(H, "images", "p01.jpg"), "rb").read()).decode()
r = requests.post("https://api.picarta.ai/v1/geolocalize", json=dict(TOKEN="", IMAGE=img, TOP_K=1), headers=UA, timeout=60)
ev["picarta_api_no_token"] = dict(url="https://api.picarta.ai/v1/geolocalize", status=r.status_code, body=r.text[:300])
r = requests.get("https://picarta.ai/pricing", headers=UA, timeout=30)
ev["picarta_pricing"] = dict(url="https://picarta.ai/pricing", status=r.status_code, text=txt(r, 700))
r = requests.get("https://api.picarta.ai/v1/admin1/CA", headers=UA, timeout=30)
ev["picarta_admin1_public"] = dict(url="https://api.picarta.ai/v1/admin1/CA", status=r.status_code, body=r.text[:120])
r = requests.get("https://app.geospy.ai", headers=UA, timeout=30, allow_redirects=True)
ev["geospy_app"] = dict(url="https://app.geospy.ai", final=r.url, status=r.status_code, text=txt(r, 300))
r = requests.get("https://geospy.ai", headers=UA, timeout=30)
ev["geospy_home"] = dict(url="https://geospy.ai", status=r.status_code, text=txt(r, 600))
r = requests.get("https://raw.githubusercontent.com/LukasHaas/PIGEON/main/README.md", timeout=30)
m = re.search(r".*weights are not provided.*", r.text)
ev["pigeon"] = dict(url="https://github.com/LukasHaas/PIGEON", status=r.status_code, quote=m.group(0) if m else "")
json.dump(ev, open(os.path.join(H, "services.json"), "w"), indent=1)
print(json.dumps(ev, indent=1))
