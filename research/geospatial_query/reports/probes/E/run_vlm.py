"""Open-weight vision-language models asked for coordinates directly. Usage: run_vlm.py <hf id> <tag> <max_new_tokens> <think:0|1> [limit]"""
import csv, json, os, re, sys, time, torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor
torch.set_num_threads(8)
H = os.path.dirname(os.path.abspath(__file__))
mid, tag, mnt, think = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == "1"
limit = int(sys.argv[5]) if len(sys.argv) > 5 else 999
proc = AutoProcessor.from_pretrained(mid, min_pixels=128 * 28 * 28, max_pixels=400 * 28 * 28)
m = AutoModelForImageTextToText.from_pretrained(mid, dtype=torch.bfloat16).eval()
Q = ("Where was this photo taken? " + ("Reason briefly about visible clues, then give " if think else "Give ") +
     "your best estimate of the latitude and longitude in decimal degrees, formatted exactly as <answer>lat, lon</answer>.")
if os.environ.get("NSEW"):
    Q = Q.replace("formatted exactly as <answer>lat, lon</answer>.", "using hemisphere letters instead of minus signs, formatted exactly like <answer>48.86 N, 2.35 E</answer>.")
num = r"(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([NSns])?\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*°?\s*([EWew])?"
def parse(t):
    a = re.findall(r"<answer>(.*?)</answer>", t, re.S); s = a[-1] if a else t
    ms = re.findall(num, s)
    if not ms: return None
    la, ns, lo, ew = ms[-1]; la, lo = float(la), float(lo)
    if ns.upper() == "S": la = -abs(la)
    if ew.upper() == "W": lo = -abs(lo)
    return (la, lo) if abs(la) <= 90 and abs(lo) <= 180 else None
out = []; t0 = time.time()
for r in list(csv.DictReader(open(os.path.join(H, "testset.csv"))))[:limit]:
    im = Image.open(os.path.join(H, r["image_file"])).convert("RGB")
    msgs = [{"role": "user", "content": [{"type": "image", "image": im}, {"type": "text", "text": Q}]}]
    x = proc.apply_chat_template(msgs, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt")
    with torch.no_grad(): y = m.generate(**x, max_new_tokens=mnt, do_sample=False)
    txt = proc.batch_decode(y[:, x["input_ids"].shape[1]:], skip_special_tokens=True)[0]
    p = parse(txt)
    out.append(dict(id=r["id"], pred_lat="" if p is None else p[0], pred_lon="" if p is None else p[1], conf="", topk=json.dumps(txt[-400:])))
    print(r["id"], p, round(time.time() - t0), txt[-120:].replace("\n", " "), flush=True)
    with open(os.path.join(H, "preds", f"{tag}.partial.json"), "w") as fh: json.dump(out, fh)
    if limit >= 50:
        with open(os.path.join(H, "preds", f"{tag}.csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, list(out[0].keys())); w.writeheader(); w.writerows(out)
