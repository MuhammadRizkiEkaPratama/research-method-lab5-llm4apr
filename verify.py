"""Independent cross-checks against sources not used in the main analysis."""
import json, sys
from pathlib import Path
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
lite = json.load(open(ROOT / "lite_all_eval.json", encoding="utf-8"))
# 1) resolved sets vs moatless 'resolved_by' (independent compilation)
by = {}
for x in lite:
    for r in x.get("resolved_by") or []:
        by.setdefault(r["name"], set()).add(x["instance_id"])
for key in ["20240402_sweagent_gpt4", "20240630_agentless_gpt4o", "20240621_autocoderover-v20240620", "20240617_moatless_gpt4o"]:
    ours = set(json.load(open(ROOT / "preds" / key / "results.json", encoding="utf-8"))["resolved"])
    theirs = by.get(key)
    print(key, "ours", len(ours), "moatless-compiled", None if theirs is None else len(theirs), "overlap", None if theirs is None else len(ours & theirs))
# 2) SWE-agent GPT-4 official file-level F1 (results/file_f1.json) vs paper's 59.05 (SWE-bench full) -- report distribution
f1 = json.load(open(ROOT / "preds" / "20240402_sweagent_gpt4" / "file_f1.json", encoding="utf-8"))["f1_scores"]
print("official file_f1 entries", len(f1), "mean", round(sum(f1) / len(f1), 4), "zero", sum(1 for v in f1 if v == 0), "one", sum(1 for v in f1 if v == 1))
