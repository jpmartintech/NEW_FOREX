"""Apply the frozen P05.1 policy exploratorily to an existing P05 report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from new_forex.provenance import PROJECT_ROOT, file_sha256
from new_forex.stress.acceptance import classify


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy_path = PROJECT_ROOT / "configs" / "stress_acceptance.yaml"
    policy = yaml.safe_load(policy_path.read_text())
    report = json.loads(args.report.read_text())
    rows = []
    for row in report["rows"]:
        rows.append({**row, "exploratory_acceptance": classify(row["metrics"], policy, row["scenario"])})
    result = {"policy_version": policy["version"], "policy_sha256": file_sha256(policy_path),
              "established_after_first_p05_run": policy["established_after_first_p05_run"],
              "cohort_certification": "PROHIBITED", "source_report": str(args.report),
              "rows": rows}
    result["summary"] = {scenario: _summary(rows, scenario) for scenario in sorted({r["scenario"] for r in rows})}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"policy": policy["version"], "rows": len(rows), "summary": result["summary"]}, indent=2))
    return 0


def _summary(rows: list[dict], scenario: str) -> dict[str, int]:
    decisions = [row["exploratory_acceptance"]["decision"] for row in rows if row["scenario"] == scenario]
    return {decision: decisions.count(decision) for decision in sorted(set(decisions))}


if __name__ == "__main__":
    raise SystemExit(main())
