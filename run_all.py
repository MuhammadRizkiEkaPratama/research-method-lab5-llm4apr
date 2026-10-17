"""Run the whole pipeline in order, then print the key numbers to check.

Usage:  python run_all.py      (after python get_data.py)
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA, OUT = Path("data"), Path("out")

if not (DATA / "lite_all_eval.json").exists():
    raise SystemExit("No data folder yet. Run:  python get_data.py")

steps = [
    ("analysis.py", [str(DATA), str(OUT)]),
    ("proxy_check.py", [str(DATA), str(OUT)]),
    ("stats_check.py", [str(OUT)]),
    ("figures.py", [str(OUT)]),
    ("verify.py", [str(DATA)]),
]
for script, args in steps:
    print(f"\n=== {script} ===")
    r = subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-3000:])
        raise SystemExit(f"{script} failed (see error above)")
    if script == "verify.py":
        print(r.stdout)
    else:
        print("  ok")

a = json.load(open(OUT / "partA_leaderboard_localization.json", encoding="utf-8"))
b = json.load(open(OUT / "partB_sweagent_cost_cap.json", encoding="utf-8"))
c = json.load(open(OUT / "partC_agentless_summary.json", encoding="utf-8"))
d = json.load(open(OUT / "partD_proxy_agreement.json", encoding="utf-8"))
s = json.load(open(OUT / "stats.json", encoding="utf-8"))

print("\n=== KEY NUMBERS (compare with the expected values in README) ===")
shares = [r["share_of_failures_loc_or_nopatch"] for r in a]
print(f"A. Failures that never edit the gold file: {min(shares):.0%} to {max(shares):.0%} across {len(a)} systems")
g = b[0]
print(f"B. {g['system']}: {g['runs_hit_cost_cap']} runs hit the cost cap, {g['resolved_among_cap']} resolved "
      f"({g['resolve_rate_cap']:.1%}) vs {g['resolve_rate_normal']:.1%} for normal submits")
m = c["gold_never_reached_repair"]
print(f"C. Agentless: {m['n']} issues where gold file never reached repair, {m['resolved']} resolved; "
      f"{c['share_total_tokens_on_gold_never_reached_repair']:.1%} of all tokens; "
      f"repair edits outside given locations: {c['repair_edits_outside_given_locations']}")
print(f"   Fisher p = {s['fisher_resolve_vs_gold_reach']['p']:.1e}, median tokens miss vs hit = "
      f"{s['mannwhitney_tokens_miss_gt_hit']['median_miss']:,} vs {s['mannwhitney_tokens_miss_gt_hit']['median_hit']:,}")
print(f"D. Miss rate when localization samples disagree vs agree: "
      f"{d['disagree']['miss_rate']:.1%} vs {d['agree']['miss_rate']:.1%} (p = {s['fisher_agreement_proxy']['p']:.3f})")
print(f"\nFigures: {OUT / 'fig1_localization_outcomes.png'} and {OUT / 'fig2_agentless_token_waste.png'}")
