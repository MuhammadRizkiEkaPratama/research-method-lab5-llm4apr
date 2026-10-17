"""Can a gold-free signal flag localization misses? Agreement across Agentless's 4 edit-location samples."""
import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out")
AL = ROOT / "agentless" / "agentless_swebench_lite"
def rj(p):
    return {json.loads(l)["instance_id"]: json.loads(l) for l in open(p, encoding="utf-8") if l.strip()}
files_by = defaultdict(list)
for k in range(1, 5):
    for iid, u in rj(AL / f"repair_sample_{k}" / "used_locs.jsonl").items():
        files_by[iid].append(frozenset(f for f, v in (u.get("found_edit_locs") or {}).items() if any(s.strip() for s in v)))
import csv
rows = list(csv.DictReader(open(OUT / "partC_agentless_per_instance.csv", encoding="utf-8")))
res = {"agree": [0, 0, 0, 0], "disagree": [0, 0, 0, 0]}  # n, misses, resolved, tokens
for r in rows:
    sets = files_by[r["instance_id"]]
    key = "agree" if len(set(sets)) == 1 else "disagree"
    miss = r["gold_reached_repair_any_sample"] == "False"
    res[key][0] += 1; res[key][1] += miss; res[key][2] += r["resolved"] == "True"; res[key][3] += int(r["tok_total"])
out = {k: {"n": v[0], "gold_never_reached_repair": v[1], "miss_rate": round(v[1] / v[0], 3), "resolve_rate": round(v[2] / v[0], 3), "mean_tokens": round(v[3] / v[0])} for k, v in res.items()}
json.dump(out, open(OUT / "partD_proxy_agreement.json", "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=1))
