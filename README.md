# Pilot: localization failures vs. token cost in LLM4APR (SWE-bench Lite)

Small reproducible analysis supporting a research gap statement. All data is public and fetched from GitHub only.

## Data sources

| What | Where |
|---|---|
| Gold patches for the 300 Lite issues | `moatless/evaluation/swebench_lite_all_evaluations.json` in github.com/aorwall/moatless-tools @ `011ead5` |
| Leaderboard predictions (`all_preds.jsonl`) | github.com/SWE-bench/experiments @ `05ad61f` (last commit before predictions moved to S3), `evaluation/lite/<run>/` |
| Resolved lists, SWE-agent end conditions, file F1 | same repo @ `40f164d`, `evaluation/lite/<run>/results/` |
| Agentless 1.5 + GPT-4o per-stage outputs with token usage | `agentless_swebench_lite.zip`, Agentless v1.5.0 GitHub release (~720 MB) |

## Quick start

```
pip install matplotlib scipy
python get_data.py     # downloads ~725 MB from GitHub into ./data (re-runnable)
python run_all.py      # runs every step, writes ./out, prints the key numbers
```

Use `py` instead of `python` on Windows if `python` is not found. All data comes from GitHub (raw.githubusercontent.com and a release asset), so a VPN may be needed on networks that block GitHub.

## Expected key numbers

If your run matches these, the pipeline reproduced correctly:

```
A. Failures that never edit the gold file: 27% to 58% across 10 systems
B. SWE-agent + GPT-4: 97 runs hit the cost cap, 4 resolved (4.1%) vs 24.6% for normal submits
C. Agentless: 60 issues where gold file never reached repair, 1 resolved; 23.9% of all tokens; repair edits outside given locations: 0/12983
   Fisher p = 2.1e-10, median tokens miss vs hit = 64,279 vs 55,065
D. Miss rate when localization samples disagree vs agree: 24.7% vs 14.8% (p = 0.042)
```

## Scripts

| Script | Does |
|---|---|
| `get_data.py` | Downloads gold patches, leaderboard predictions/results (pinned commits) and the Agentless archive; extracts only needed files |
| `analysis.py` | Parts A–C: localization outcome per system, SWE-agent cost-cap outcomes, Agentless per-issue tokens vs localization |
| `proxy_check.py` | Part D: does disagreement between localization samples flag a miss (without using gold)? |
| `stats_check.py` | Fisher exact and Mann–Whitney tests |
| `figures.py` | `fig1_localization_outcomes.png`, `fig2_agentless_token_waste.png` |
| `verify.py` | Cross-checks resolved sets against an independent compilation and the official SWE-agent file F1 |
| `run_all.py` | Runs the five analysis scripts in order |

## Definitions

- **Gold file hit**: every non-test file changed by the gold patch is also changed by the system's patch (file level, strict).
- **Gold reached repair** (Agentless): every gold file appears in the edit locations handed to at least one of the 4 repair samples. Repair never edited a file outside its given locations (0 of 12,983 generated edits), so a miss here means the repair stage cannot touch the gold file.
- **Tokens**: prompt + completion tokens logged by Agentless for localization, repair and reproduction-test generation. Embedding retrieval is not included, so totals are a lower bound. USD uses GPT-4o (2024-05-13) list price, $5 / $15 per 1M input / output tokens.

## Known limitations

- Strict file-level matching undercounts valid alternative fixes (2–6 resolved issues per system edit a different file than gold).
- Per-issue token data exists only for Agentless here; SWE-agent per-issue trajectories are hosted on S3/HuggingFace and are not used.
- Lite only; results may differ on SWE-bench Verified and with newer models.
