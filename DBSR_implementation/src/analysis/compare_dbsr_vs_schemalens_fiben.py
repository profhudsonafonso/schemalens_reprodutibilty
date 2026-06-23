#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


QUERY_NAME_MAP = {
    "Q1_CompanyProfileIBM": "Q1",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "Q2",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "Q3",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": "Q4",
    "Q5_ReportsAndMetricDataOfCompany": "Q5",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": "Q6",
    "Q7_PersonsWhoBoughtMoreIBMThanSold": "Q7",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "Q8",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "Q9",
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "query_id",
        "dbsr_query_name",
        "schemalens_best_config",
        "schemalens_best_group",
        "schemalens_p95_ms",
        "dbsr_p95_ms",
        "best_observed_method",
        "best_observed_p95_ms",
        "dbsr_regret_vs_schemalens",
        "dbsr_regret_vs_best_observed",
        "dbsr_within_5_percent_of_schemalens",
        "schema_lens_returned_count",
        "dbsr_returned_count",
        "returned_count_ratio_dbsr_over_schemalens",
        "semantic_parity_warning",
    ]

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def first_existing(row: Dict[str, str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in row and row[c] not in ("", None):
            return row[c]
    return None


def as_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def normalize_query_id(value: str) -> str:
    value = str(value).strip()

    if value in QUERY_NAME_MAP:
        return QUERY_NAME_MAP[value]

    # Common FIBEN names: Q1, Q2, ...
    if value.upper().startswith("Q"):
        # Keep only Q + number prefix if the field contains more text.
        out = []
        for ch in value.upper():
            if ch == "Q" or ch.isdigit():
                out.append(ch)
            else:
                break
        if out:
            return "".join(out)

    return value


def load_dbsr_hot(path: Path) -> Dict[str, Dict[str, Any]]:
    rows = read_csv(path)
    out: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        phase = row.get("phase", "")
        if phase != "hot":
            continue

        query_name = row["query_name"]
        query_id = normalize_query_id(query_name)

        out[query_id] = {
            "query_id": query_id,
            "dbsr_query_name": query_name,
            "dbsr_p95_ms": as_float(row.get("p95_ms")),
            "dbsr_avg_ms": as_float(row.get("avg_ms")),
            "dbsr_p50_ms": as_float(row.get("p50_ms")),
            "dbsr_returned_count": as_float(row.get("avg_returned_count")),
        }

    return out


def detect_schemalens_rows(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    detected = []

    for row in rows:
        query_value = first_existing(row, [
            "query_name",
            "query",
            "query_id",
            "workload_query",
            "query_label",
            "operation",
        ])

        p95_value = first_existing(row, [
            "p95_latency_ms",
            "p95_ms",
            "p95_hot_ms",
            "hot_p95_ms",
            "best_p95",
            "best_p95_ms",
            "p95",
        ])

        phase_value = first_existing(row, [
            "run_phase",
            "phase",
            "benchmark_phase",
        ])

        if query_value is None or p95_value is None:
            continue

        # If phase exists, keep only hot rows.
        if phase_value is not None and str(phase_value).lower() != "hot":
            continue

        query_id = normalize_query_id(query_value)
        p95 = as_float(p95_value)

        if p95 is None:
            continue

        detected.append({
            "query_id": query_id,
            "raw_query_value": query_value,
            "p95_ms": p95,
            "avg_documents_returned": as_float(first_existing(row, [
                "avg_documents_returned",
                "avg_returned_count",
                "documents_returned",
            ])),
            "n_runs": as_float(first_existing(row, [
                "n_runs",
                "executions",
            ])),
            "n_success_runs": as_float(first_existing(row, [
                "n_success_runs",
                "successful_executions",
            ])),
            "config": first_existing(row, [
                "candidate_id",
                "design_pattern",
                "config",
                "candidate",
                "candidate_name",
                "configuration",
                "config_name",
                "group",
            ]),
            "group": first_existing(row, [
                "final_benchmark_group",
                "g_class",
                "group_type",
                "best_group",
                "candidate_group",
                "activation_group",
                "role",
            ]),
            "raw_row": row,
        })

    return detected


def best_schemalens_by_query(path: Path) -> Dict[str, Dict[str, Any]]:
    rows = read_csv(path)
    detected = detect_schemalens_rows(rows)

    best: Dict[str, Dict[str, Any]] = {}

    for row in detected:
        q = row["query_id"]
        if q not in best or row["p95_ms"] < best[q]["p95_ms"]:
            best[q] = row

    return best


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbsr-aggregate", required=True)
    parser.add_argument("--schemalens-aggregate", required=True)
    parser.add_argument("--scale-label", default="sf1")
    parser.add_argument("--out-dir", default="DBSR_implementation/results/fiben")
    args = parser.parse_args()

    dbsr = load_dbsr_hot(Path(args.dbsr_aggregate))
    schemalens = best_schemalens_by_query(Path(args.schemalens_aggregate))

    comparison = []
    missing = []

    for query_id in sorted(dbsr.keys(), key=lambda x: int(x.replace("Q", "")) if x.replace("Q", "").isdigit() else x):
        d = dbsr[query_id]
        s = schemalens.get(query_id)

        if s is None:
            missing.append(query_id)
            continue

        dbsr_p95 = d["dbsr_p95_ms"]
        sl_p95 = s["p95_ms"]

        best_observed = min(dbsr_p95, sl_p95)
        best_method = "DBSR" if dbsr_p95 <= sl_p95 else "SchemaLens"

        dbsr_regret_vs_schemalens = (dbsr_p95 - sl_p95) / sl_p95 if sl_p95 > 0 else 0.0
        dbsr_regret_vs_best = (dbsr_p95 - best_observed) / best_observed if best_observed > 0 else 0.0

        sl_returned = s.get("avg_documents_returned")
        dbsr_returned = d["dbsr_returned_count"]

        if sl_returned in (None, 0):
            returned_ratio = None
            warning = "schema_lens_return_count_missing_or_zero"
        else:
            returned_ratio = dbsr_returned / sl_returned
            warning = ""
            if returned_ratio < 0.5 or returned_ratio > 2.0:
                warning = "returned_count_differs_substantially"

        comparison.append({
            "query_id": query_id,
            "dbsr_query_name": d["dbsr_query_name"],
            "schemalens_best_config": s.get("config"),
            "schemalens_best_group": s.get("group"),
            "schemalens_p95_ms": round(sl_p95, 6),
            "dbsr_p95_ms": round(dbsr_p95, 6),
            "best_observed_method": best_method,
            "best_observed_p95_ms": round(best_observed, 6),
            "dbsr_regret_vs_schemalens": round(dbsr_regret_vs_schemalens, 6),
            "dbsr_regret_vs_best_observed": round(dbsr_regret_vs_best, 6),
            "dbsr_within_5_percent_of_schemalens": dbsr_p95 <= sl_p95 * 1.05,
            "schema_lens_returned_count": sl_returned,
            "dbsr_returned_count": dbsr_returned,
            "returned_count_ratio_dbsr_over_schemalens": round(returned_ratio, 6) if returned_ratio is not None else None,
            "semantic_parity_warning": warning,
        })

    dbsr_wins = sum(1 for r in comparison if r["best_observed_method"] == "DBSR")
    schemalens_wins = sum(1 for r in comparison if r["best_observed_method"] == "SchemaLens")
    near_best = sum(1 for r in comparison if r["dbsr_within_5_percent_of_schemalens"])

    avg_regret_vs_schemalens = (
        sum(r["dbsr_regret_vs_schemalens"] for r in comparison) / len(comparison)
        if comparison else 0.0
    )

    summary = {
        "baseline": "DBSR",
        "comparison_target": "SchemaLens",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "queries_compared": len(comparison),
        "missing_queries": missing,
        "dbsr_wins": dbsr_wins,
        "schemalens_wins": schemalens_wins,
        "dbsr_near_schemalens_5_percent": near_best,
        "avg_dbsr_regret_vs_schemalens": round(avg_regret_vs_schemalens, 6),
        "dbsr_aggregate": args.dbsr_aggregate,
        "schemalens_aggregate": args.schemalens_aggregate,
        "methodological_note": (
            "This comparison uses the best SchemaLens p95 observed per FIBEN query "
            "from the SchemaLens aggregate CSV and the official DBSR hot p95 from "
            "the materialized DBSR collections."
        ),
    }

    out_dir = Path(args.out_dir)
    comparison_path = out_dir / f"dbsr_vs_schemalens_{args.scale_label}_comparison.csv"
    summary_path = out_dir / f"dbsr_vs_schemalens_{args.scale_label}_summary.json"

    write_csv(comparison_path, comparison)
    write_json(summary_path, summary)

    print("DBSR vs SchemaLens comparison completed.")
    print(f"Queries compared: {summary['queries_compared']}")
    print(f"Missing queries: {summary['missing_queries']}")
    print(f"DBSR wins: {summary['dbsr_wins']}")
    print(f"SchemaLens wins: {summary['schemalens_wins']}")
    print(f"DBSR near SchemaLens within 5%: {summary['dbsr_near_schemalens_5_percent']}")
    print(f"Avg DBSR regret vs SchemaLens: {summary['avg_dbsr_regret_vs_schemalens']}")
    print(f"Wrote {comparison_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
