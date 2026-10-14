from huggingface_hub import snapshot_download
import sys
for rid in sys.argv[1:]:
    try:
        p = snapshot_download(rid); print("OK", rid, p)
    except Exception as e:
        print("FAIL", rid, repr(e)[:300])
