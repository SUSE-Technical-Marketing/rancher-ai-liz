#!/usr/bin/env python3
"""
Compare two Liz test runs side-by-side.

Usage:
  python compare.py results/2026-03-09T10-00-00-model-a  results/2026-03-09T11-00-00-model-b
  python compare.py results/run-a results/run-b --csv        # also write comparison.csv
"""

import json
import sys
import argparse
import csv
from pathlib import Path


def load_summary(run_dir: Path) -> dict:
    summary_file = run_dir / "summary.json"
    if not summary_file.exists():
        print(f"No summary.json in {run_dir}")
        sys.exit(1)
    with open(summary_file) as f:
        return json.load(f)


def fmt(val, suffix="s"):
    if val is None:
        return "  N/A  "
    return f"{val:.2f}{suffix}"


def delta_indicator(a, b):
    """Show change direction and percentage."""
    if a is None or b is None:
        return ""
    pct = ((b - a) / a) * 100
    if pct > 5:
        return f"  +{pct:.0f}%  SLOWER"
    elif pct < -5:
        return f"  {pct:.0f}%  faster"
    else:
        return f"  ~same"


def compare(run_a: Path, run_b: Path, write_csv: bool = False):
    sa = load_summary(run_a)
    sb = load_summary(run_b)

    label_a = sa.get("run_label") or run_a.name
    label_b = sb.get("run_label") or run_b.name

    # Index questions by name
    qa = {q["name"]: q for q in sa.get("questions", [])}
    qb = {q["name"]: q for q in sb.get("questions", [])}

    all_names = list(dict.fromkeys(list(qa.keys()) + list(qb.keys())))

    col_w = 34

    print(f"\n{'='*80}")
    print(f"COMPARISON")
    print(f"  A: {label_a}  ({sa.get('timestamp', '')})")
    print(f"  B: {label_b}  ({sb.get('timestamp', '')})")
    print(f"{'='*80}")

    header = f"{'Test':<{col_w}} {'Metric':<7} {'A':>8} {'B':>8} {'Delta':>18}"
    print(header)
    print("-" * 80)

    csv_rows = []

    for name in all_names:
        a = qa.get(name)
        b = qb.get(name)

        for metric, key in [("TTFT", "ttft_stats"), ("Total", "total_time_stats")]:
            a_avg = a[key].get("avg") if a else None
            b_avg = b[key].get("avg") if b else None
            d = delta_indicator(a_avg, b_avg)
            print(f"{name[:col_w-1]:<{col_w}} {metric:<7} {fmt(a_avg):>8} {fmt(b_avg):>8} {d}")

            csv_rows.append({
                "test_name": name,
                "metric": metric,
                f"A_{label_a}_avg": a_avg,
                f"B_{label_b}_avg": b_avg,
            })
        print()

    if write_csv:
        out = Path("comparison.csv")
        with open(out, "w", newline="") as f:
            if csv_rows:
                writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
                writer.writeheader()
                writer.writerows(csv_rows)
        print(f"Comparison saved to: {out}")


def main():
    parser = argparse.ArgumentParser(description="Compare two Liz test run results")
    parser.add_argument("run_a", help="Path to first run directory")
    parser.add_argument("run_b", help="Path to second run directory")
    parser.add_argument("--csv", action="store_true", help="Also write comparison.csv")
    args = parser.parse_args()

    compare(Path(args.run_a), Path(args.run_b), write_csv=args.csv)


if __name__ == "__main__":
    main()
