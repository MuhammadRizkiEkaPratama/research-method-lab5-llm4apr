import csv, sys, json
from pathlib import Path
from scipy.stats import fisher_exact, mannwhitneyu
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out")
rows = list(csv.DictReader(open(OUT / "partC_agentless_per_instance.csv", encoding="utf-8")))
miss = [r for r in rows if r["gold_reached_repair_any_sample"] == "False"]
hit = [r for r in rows if r["gold_reached_repair_any_sample"] == "True"]
t = [[sum(r["resolved"] == "True" for r in miss), len(miss) - sum(r["resolved"] == "True" for r in miss)],
     [sum(r["resolved"] == "True" for r in hit), len(hit) - sum(r["resolved"] == "True" for r in hit)]]
o1 = fisher_exact(t)
u = mannwhitneyu([int(r["tok_total"]) for r in miss], [int(r["tok_total"]) for r in hit], alternative="greater")
o2 = fisher_exact([[21, 142 - 21], [39, 158 - 39]])
med = lambda xs: sorted(xs)[len(xs) // 2]
out = {"fisher_resolve_vs_gold_reach": {"table": t, "p": o1.pvalue},
       "mannwhitney_tokens_miss_gt_hit": {"p": u.pvalue, "median_miss": med([int(r["tok_total"]) for r in miss]), "median_hit": med([int(r["tok_total"]) for r in hit])},
       "fisher_agreement_proxy": {"p": o2.pvalue}}
json.dump(out, open(OUT / "stats.json", "w", encoding="utf-8"), indent=2)
print(json.dumps(out, indent=1))
