"""Pilot analysis: localization failures vs. token cost on SWE-bench Lite.

Data (all public):
  - Gold patches: moatless-tools/moatless/evaluation/swebench_lite_all_evaluations.json (300 Lite instances)
  - Leaderboard predictions + resolved lists: github.com/SWE-bench/experiments (evaluation/lite/*)
  - Agentless-1.5 + GPT-4o per-stage artifacts incl. token usage: Agentless v1.5.0 GitHub release
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out")
OUT.mkdir(parents=True, exist_ok=True)

DIFF_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.M)


def patch_files(patch):
    if not patch:
        return set()
    return {m.group(2) for m in DIFF_RE.finditer(patch)}


def is_test_file(p):
    return "/tests/" in p or "/test/" in p or p.split("/")[-1].startswith("test_") or p.startswith("tests/")


# ---------- gold ----------
lite = json.load(open(ROOT / "lite_all_eval.json", encoding="utf-8"))
GOLD = {x["instance_id"]: patch_files(x["golden_patch"]) for x in lite}
IDS = sorted(GOLD)
assert len(IDS) == 300

# ---------- Part A: leaderboard systems ----------
SYSTEMS = {
    "20240402_sweagent_claude3opus": "SWE-agent + Claude 3 Opus",
    "20240402_sweagent_gpt4": "SWE-agent + GPT-4",
    "20240728_sweagent_gpt4o": "SWE-agent + GPT-4o",
    "20240620_sweagent_claude3.5sonnet": "SWE-agent + Claude 3.5 Sonnet",
    "20240530_autocoderover-v20240408": "AutoCodeRover (Apr 2024)",
    "20240617_moatless_gpt4o": "Moatless + GPT-4o",
    "20240630_agentless_gpt4o": "Agentless + GPT-4o",
    "20240621_autocoderover-v20240620": "AutoCodeRover (Jun 2024)",
    "20241028_agentless-1.5_gpt4o": "Agentless 1.5 + GPT-4o",
    "20241025_OpenHands-CodeAct-2.1-sonnet-20241022": "OpenHands + Claude 3.5 Sonnet (new)",
}

rows_a = []
for key, label in SYSTEMS.items():
    d = ROOT / "preds" / key
    preds = {}
    for line in open(d / "all_preds.jsonl", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        p = json.loads(line)
        preds[p["instance_id"]] = p.get("model_patch") or ""
    resolved = set(json.load(open(d / "results.json", encoding="utf-8"))["resolved"]) & set(IDS)
    c = Counter()
    resolved_wrong_file = 0
    for iid in IDS:
        pf = {f for f in patch_files(preds.get(iid, "")) if not is_test_file(f)}
        hit = GOLD[iid] <= pf
        if iid in resolved:
            c["resolved"] += 1
            if not hit:
                resolved_wrong_file += 1
        elif not pf:
            c["no_patch"] += 1
        elif hit:
            c["right_file_failed"] += 1
        else:
            c["wrong_file"] += 1
    unresolved = 300 - c["resolved"]
    rows_a.append({
        "system": label,
        "resolved": c["resolved"],
        "right_file_failed": c["right_file_failed"],
        "wrong_file": c["wrong_file"],
        "no_patch": c["no_patch"],
        "resolved_without_all_gold_files": resolved_wrong_file,
        "share_of_failures_loc_or_nopatch": round((c["wrong_file"] + c["no_patch"]) / unresolved, 3),
    })

json.dump(rows_a, open(OUT / "partA_leaderboard_localization.json", "w", encoding="utf-8"), indent=2)

# ---------- Part B: SWE-agent end conditions (official aggregate files) ----------
rows_b = []
for key in ["20240402_sweagent_gpt4", "20240402_sweagent_claude3opus"]:
    d = ROOT / "preds" / key
    ec = json.load(open(d / "end_condition.json", encoding="utf-8"))
    ecr = json.load(open(d / "end_condition_resolved.json", encoding="utf-8"))
    cap = ec.get("submitted (exit_cost)", 0) + ec.get("exit_cost", 0)
    cap_res = ecr.get("submitted (exit_cost)", 0) + ecr.get("exit_cost", 0)
    nat = ec.get("submitted", 0)
    nat_res = ecr.get("submitted", 0)
    rows_b.append({
        "system": SYSTEMS[key],
        "runs_hit_cost_cap": cap, "resolved_among_cap": cap_res,
        "runs_submitted_normally": nat, "resolved_among_normal": nat_res,
        "resolve_rate_cap": round(cap_res / cap, 3) if cap else None,
        "resolve_rate_normal": round(nat_res / nat, 3) if nat else None,
    })
json.dump(rows_b, open(OUT / "partB_sweagent_cost_cap.json", "w", encoding="utf-8"), indent=2)

# ---------- Part C: Agentless-1.5 per-instance tokens vs localization ----------
AL = ROOT / "agentless" / "agentless_swebench_lite"


def usage_tokens(u):
    if not u:
        return 0, 0
    return u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


def read_jsonl(p):
    out = {}
    for line in open(p, encoding="utf-8"):
        if line.strip():
            x = json.loads(line)
            out[x["instance_id"]] = x
    return out


tok = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # iid -> stage -> [in, out]


def add(iid, stage, u):
    i, o = usage_tokens(u)
    tok[iid][stage][0] += i
    tok[iid][stage][1] += o


for iid, x in read_jsonl(AL / "file_level" / "loc_outputs.jsonl").items():
    add(iid, "localization", (x.get("file_traj") or {}).get("usage"))
for iid, x in read_jsonl(AL / "file_level_irrelevant" / "loc_outputs.jsonl").items():
    add(iid, "localization", (x.get("file_traj") or {}).get("usage"))
for iid, x in read_jsonl(AL / "related_elements" / "loc_outputs.jsonl").items():
    add(iid, "localization", (x.get("related_loc_traj") or {}).get("usage"))
for iid, x in read_jsonl(AL / "edit_location_samples" / "loc_outputs.jsonl").items():
    t = x.get("edit_loc_traj") or {}
    if isinstance(t, list):
        for tt in t:
            add(iid, "localization", tt.get("usage"))
    else:
        add(iid, "localization", t.get("usage"))
for iid, x in read_jsonl(AL / "reproduction_test_samples" / "output.jsonl").items():
    for tt in x.get("traj") or []:
        add(iid, "reproduction_tests", tt.get("usage"))

combined_files = {iid: set(x.get("found_files") or []) for iid, x in read_jsonl(AL / "file_level_combined" / "combined_locs.jsonl").items()}

per_sample_gold_hit = defaultdict(list)  # iid -> [bool per repair sample]
repair_tok_by_sample = defaultdict(list)  # iid -> [(in,out) per sample]
edited_outside_locs = 0
edited_total = 0
for k in range(1, 5):
    used = read_jsonl(AL / f"repair_sample_{k}" / "used_locs.jsonl")
    outs = read_jsonl(AL / f"repair_sample_{k}" / "output.jsonl")
    for iid in IDS:
        u = used.get(iid, {})
        loc_files = {f for f, v in (u.get("found_edit_locs") or {}).items() if any(s.strip() for s in v)}
        per_sample_gold_hit[iid].append(GOLD[iid] <= loc_files)
        x = outs.get(iid, {})
        ti = to = 0
        for tt in x.get("traj") or []:
            i, o = usage_tokens(tt.get("usage"))
            ti += i
            to += o
        repair_tok_by_sample[iid].append((ti, to))
        tok[iid]["repair"][0] += ti
        tok[iid]["repair"][1] += to
        for fl in x.get("file_names") or []:
            for f in fl or []:
                if f:
                    edited_total += 1
                    if f not in loc_files:
                        edited_outside_locs += 1

ag_resolved = set(json.load(open(ROOT / "preds" / "20241028_agentless-1.5_gpt4o" / "results.json", encoding="utf-8"))["resolved"])
ag_preds = {json.loads(l)["instance_id"]: json.loads(l)["model_patch"] for l in open(AL / "all_preds.jsonl", encoding="utf-8") if l.strip()}

PRICE_IN, PRICE_OUT = 5.0, 15.0  # USD per 1M tokens, gpt-4o-2024-05-13 list price

rows_c = []
for iid in IDS:
    stages = tok[iid]
    t_in = sum(v[0] for v in stages.values())
    t_out = sum(v[1] for v in stages.values())
    rows_c.append({
        "instance_id": iid,
        "resolved": iid in ag_resolved,
        "gold_in_file_stage": GOLD[iid] <= combined_files.get(iid, set()),
        "gold_reached_repair_any_sample": any(per_sample_gold_hit[iid]),
        "samples_with_gold": sum(per_sample_gold_hit[iid]),
        "final_patch_hits_gold": GOLD[iid] <= {f for f in patch_files(ag_preds.get(iid, "")) if not is_test_file(f)},
        "tok_localization": sum(stages["localization"]),
        "tok_repair": sum(stages["repair"]),
        "tok_repair_wasted_samples": sum(a + b for (a, b), hit in zip(repair_tok_by_sample[iid], per_sample_gold_hit[iid]) if not hit),
        "tok_reproduction": sum(stages["reproduction_tests"]),
        "tok_total": t_in + t_out,
        "usd_total": round(t_in / 1e6 * PRICE_IN + t_out / 1e6 * PRICE_OUT, 4),
    })

with open(OUT / "partC_agentless_per_instance.csv", "w", encoding="utf-8") as f:
    cols = list(rows_c[0].keys())
    f.write(",".join(cols) + "\n")
    for r in rows_c:
        f.write(",".join(str(r[c]) for c in cols) + "\n")


def summarize(rows, cond):
    sel = [r for r in rows if cond(r)]
    n = len(sel)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "resolved": sum(r["resolved"] for r in sel),
        "resolve_rate": round(sum(r["resolved"] for r in sel) / n, 3),
        "tok_total_sum": sum(r["tok_total"] for r in sel),
        "tok_total_mean": round(sum(r["tok_total"] for r in sel) / n),
        "tok_repair_sum": sum(r["tok_repair"] for r in sel),
        "usd_sum": round(sum(r["usd_total"] for r in sel), 2),
    }


T = sum(r["tok_total"] for r in rows_c)
R = sum(r["tok_repair"] for r in rows_c)
summary_c = {
    "all": summarize(rows_c, lambda r: True),
    "gold_never_reached_repair": summarize(rows_c, lambda r: not r["gold_reached_repair_any_sample"]),
    "gold_reached_repair": summarize(rows_c, lambda r: r["gold_reached_repair_any_sample"]),
    "gold_lost_at_file_stage": summarize(rows_c, lambda r: not r["gold_in_file_stage"]),
    "resolved": summarize(rows_c, lambda r: r["resolved"]),
    "unresolved": summarize(rows_c, lambda r: not r["resolved"]),
    "share_total_tokens_on_unresolved": round(sum(r["tok_total"] for r in rows_c if not r["resolved"]) / T, 3),
    "share_total_tokens_on_gold_never_reached_repair": round(sum(r["tok_total"] for r in rows_c if not r["gold_reached_repair_any_sample"]) / T, 3),
    "share_repair_tokens_in_samples_missing_gold": round(sum(r["tok_repair_wasted_samples"] for r in rows_c) / R, 3),
    "share_tokens_by_stage": {s: round(sum(sum(tok[i][s]) for i in IDS) / T, 3) for s in ["localization", "repair", "reproduction_tests"]},
    "resolved_although_gold_never_reached_repair": sum(1 for r in rows_c if r["resolved"] and not r["gold_reached_repair_any_sample"]),
    "repair_edits_outside_given_locations": f"{edited_outside_locs}/{edited_total}",
    "price_assumption_usd_per_1M": {"input": PRICE_IN, "output": PRICE_OUT},
}
json.dump(summary_c, open(OUT / "partC_agentless_summary.json", "w", encoding="utf-8"), indent=2)

print(json.dumps(rows_a, indent=1))
print(json.dumps(rows_b, indent=1))
print(json.dumps(summary_c, indent=1))
