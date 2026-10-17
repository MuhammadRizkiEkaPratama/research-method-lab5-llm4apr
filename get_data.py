"""Download every input file the analysis needs (GitHub only, ~725 MB total).

Usage:  python get_data.py
Creates ./data next to where you run it. Safe to re-run: finished downloads are skipped.
"""
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data")

# Pinned commits so the numbers are reproducible.
EXP_PREDS = "05ad61feb9c9f334dc340baea7c4f31cf7854274"   # last commit that still had all_preds.jsonl in git
EXP_HEAD = "40f164d5b8f1d249bf95a6df8b74b577fd8e519d"    # results/*.json
MOATLESS = "011ead57a5c81664e9c45e07e1f50b17e695cc63"    # gold patches for SWE-bench Lite
RAW_EXP = "https://raw.githubusercontent.com/SWE-bench/experiments"
GOLD_URL = f"https://raw.githubusercontent.com/aorwall/moatless-tools/{MOATLESS}/moatless/evaluation/swebench_lite_all_evaluations.json"
AGENTLESS_URL = "https://github.com/OpenAutoCoder/Agentless/releases/download/v1.5.0/agentless_swebench_lite.zip"

RUNS = [
    "20240402_sweagent_claude3opus",
    "20240402_sweagent_gpt4",
    "20240728_sweagent_gpt4o",
    "20240620_sweagent_claude3.5sonnet",
    "20240530_autocoderover-v20240408",
    "20240617_moatless_gpt4o",
    "20240630_agentless_gpt4o",
    "20240621_autocoderover-v20240620",
    "20241028_agentless-1.5_gpt4o",
    "20241025_OpenHands-CodeAct-2.1-sonnet-20241022",
]
OPTIONAL_RESULTS = ["end_condition.json", "end_condition_resolved.json", "file_f1.json"]

AGENTLESS_MEMBERS = [
    "all_preds.jsonl",
    "file_level/loc_outputs.jsonl",
    "file_level_irrelevant/loc_outputs.jsonl",
    "file_level_combined/combined_locs.jsonl",
    "related_elements/loc_outputs.jsonl",
    "edit_location_samples/loc_outputs.jsonl",
    "reproduction_test_samples/output.jsonl",
] + [f"repair_sample_{k}/{name}" for k in range(1, 5) for name in ("output.jsonl", "used_locs.jsonl")]


def download(url, dest, optional=False, show_progress=False):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip (already have) {dest}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if show_progress and total:
                    print(f"\r  {done / 1e6:7.1f} / {total / 1e6:.1f} MB", end="", flush=True)
        if show_progress:
            print()
    except urllib.error.HTTPError as e:
        tmp.unlink(missing_ok=True)
        if optional and e.code == 404:
            return False
        raise SystemExit(f"Download failed ({e.code}): {url}")
    except urllib.error.URLError as e:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"Cannot reach {url}: {e.reason}. Check your internet/VPN and run again.")
    tmp.replace(dest)
    print(f"  ok {dest}")
    return True


def main():
    print("[1/4] Gold patches (SWE-bench Lite, 300 issues)")
    download(GOLD_URL, DATA / "lite_all_eval.json")

    print("[2/4] Leaderboard predictions and results (10 systems)")
    for run in RUNS:
        d = DATA / "preds" / run
        download(f"{RAW_EXP}/{EXP_PREDS}/evaluation/lite/{run}/all_preds.jsonl", d / "all_preds.jsonl")
        download(f"{RAW_EXP}/{EXP_HEAD}/evaluation/lite/{run}/results/results.json", d / "results.json")
        for name in OPTIONAL_RESULTS:
            download(f"{RAW_EXP}/{EXP_HEAD}/evaluation/lite/{run}/results/{name}", d / name, optional=True)

    print("[3/4] Agentless 1.5 archive (~725 MB, takes a while)")
    zpath = DATA / "_downloads" / "agentless_swebench_lite.zip"
    download(AGENTLESS_URL, zpath, show_progress=True)

    print("[4/4] Extracting only the files the analysis needs")
    out = DATA / "agentless"
    with zipfile.ZipFile(zpath) as z:
        for m in AGENTLESS_MEMBERS:
            name = f"agentless_swebench_lite/{m}"
            target = out / name
            if target.exists() and target.stat().st_size > 0:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            print(f"  ok {target}")

    print("\nDone. You can delete data/_downloads/agentless_swebench_lite.zip to free ~725 MB.")
    print("Next: python run_all.py")


if __name__ == "__main__":
    main()
