"""
Benchmark Lima & Mello 2015 FIBEN MongoDB materialization.

This runner executes Q1--Q9 as real MongoDB aggregate/find workloads and records
latency in milliseconds. Q10 is not included here because it is an insert/update
workload and needs an isolated reset/rollback strategy.

Outputs:
- lmm_fiben_benchmark_raw_results.csv
- lmm_fiben_benchmark_aggregate_results.csv
- lmm_fiben_benchmark_manifest.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from pymongo import MongoClient


THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from run_lmm_fiben_query_plan import build_params, build_queries, json_default  # noqa: E402


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def percentile(values: List[float], p: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def run_pipeline(db, collection: str, pipeline: List[Dict[str, Any]], max_time_ms: int) -> Dict[str, Any]:
    start = time.perf_counter()
    cursor = db[collection].aggregate(
        pipeline,
        allowDiskUse=True,
        maxTimeMS=max_time_ms,
    )

    n_docs = 0
    for _doc in cursor:
        n_docs += 1

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return {
        "elapsed_ms": elapsed_ms,
        "n_returned": n_docs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default="mongodb://mongo:mongo@127.0.0.1:27018/admin")
    parser.add_argument("--db-name", default="lmm_fiben_sf1_source_full")
    parser.add_argument("--scale", default="sf1")
    parser.add_argument("--output-dir", default="de_lima_mello_2015_implementation/results/fiben/benchmark")
    parser.add_argument("--queries", default="Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8,Q9")
    parser.add_argument("--warmup-runs", type=int, default=3)
    parser.add_argument("--cold-runs", type=int, default=5)
    parser.add_argument("--hot-runs", type=int, default=20)
    parser.add_argument("--result-limit", type=int, default=1000)
    parser.add_argument("--max-time-ms", type=int, default=180000)
    args = parser.parse_args()

    selected_queries = {q.strip().upper() for q in args.queries.split(",") if q.strip()}

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    params = build_params(db)
    query_specs = build_queries(params, result_limit=args.result_limit)
    query_specs = [q for q in query_specs if q["query_id"].upper() in selected_queries]

    output_dir = Path(args.output_dir) / args.scale / args.db_name
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_rows: List[Dict[str, Any]] = []

    print(f"[{now()}] Running Lima & Mello FIBEN benchmark on {args.db_name}")
    print(f"[{now()}] Queries: {','.join(q['query_id'] for q in query_specs)}")
    print(f"[{now()}] Params: {json.dumps(params, default=json_default)}")

    for spec in query_specs:
        qid = spec["query_id"]
        qname = spec["query_name"]
        collection = spec["root_collection"]
        pipeline = spec["pipeline"]

        print(f"[{now()}] Warmup {qid}: {qname}", flush=True)

        for i in range(args.warmup_runs):
            try:
                run_pipeline(db, collection, pipeline, args.max_time_ms)
            except Exception as exc:
                print(f"[{now()}] Warmup failed for {qid}: {exc}", flush=True)

        for phase, n_runs in [("cold", args.cold_runs), ("hot", args.hot_runs)]:
            for repetition in range(1, n_runs + 1):
                print(f"[{now()}] {phase} {qid} repetition {repetition}/{n_runs}", flush=True)

                started = time.time()

                try:
                    result = run_pipeline(db, collection, pipeline, args.max_time_ms)
                    status = "completed"
                    elapsed_ms = result["elapsed_ms"]
                    n_returned = result["n_returned"]
                    error_message = None
                except Exception as exc:
                    status = "failed"
                    elapsed_ms = None
                    n_returned = None
                    error_message = str(exc)

                raw_rows.append({
                    "method": "lima_mello_2015",
                    "dataset": "FIBEN",
                    "scale": args.scale,
                    "database": args.db_name,
                    "query_id": qid,
                    "query_name": qname,
                    "root_collection": collection,
                    "run_phase": phase,
                    "repetition": repetition,
                    "status": status,
                    "elapsed_ms": elapsed_ms,
                    "n_returned": n_returned,
                    "started_epoch": started,
                    "result_limit": args.result_limit,
                    "max_time_ms": args.max_time_ms,
                    "error_message": error_message,
                    "pipeline_json": json.dumps(pipeline, default=json_default),
                })

    raw_df = pd.DataFrame(raw_rows)

    agg_rows = []

    for (query_id, query_name, phase), group in raw_df.groupby(["query_id", "query_name", "run_phase"], dropna=False):
        completed = group[group["status"] == "completed"].copy()
        values = completed["elapsed_ms"].dropna().astype(float).tolist()

        agg_rows.append({
            "method": "lima_mello_2015",
            "dataset": "FIBEN",
            "scale": args.scale,
            "database": args.db_name,
            "query_id": query_id,
            "query_name": query_name,
            "run_phase": phase,
            "n_runs": int(len(group)),
            "n_completed": int(len(completed)),
            "n_failed": int((group["status"] != "completed").sum()),
            "min_ms": min(values) if values else None,
            "mean_ms": statistics.mean(values) if values else None,
            "median_ms": statistics.median(values) if values else None,
            "p95_ms": percentile(values, 95) if values else None,
            "max_ms": max(values) if values else None,
            "mean_n_returned": completed["n_returned"].dropna().astype(float).mean() if len(completed) else None,
        })

    agg_df = pd.DataFrame(agg_rows)

    raw_csv = output_dir / "lmm_fiben_benchmark_raw_results.csv"
    agg_csv = output_dir / "lmm_fiben_benchmark_aggregate_results.csv"
    manifest_json = output_dir / "lmm_fiben_benchmark_manifest.json"

    raw_df.to_csv(raw_csv, index=False)
    agg_df.to_csv(agg_csv, index=False)

    manifest = {
        "status": "completed",
        "method": "lima_mello_2015",
        "dataset": "FIBEN",
        "scale": args.scale,
        "database": args.db_name,
        "queries": sorted(selected_queries),
        "warmup_runs": args.warmup_runs,
        "cold_runs": args.cold_runs,
        "hot_runs": args.hot_runs,
        "result_limit": args.result_limit,
        "max_time_ms": args.max_time_ms,
        "raw_csv": str(raw_csv),
        "aggregate_csv": str(agg_csv),
        "important_note": "Q10 is excluded because it is an insert/update workload and requires isolated reset/rollback benchmarking.",
    }

    manifest_json.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=json_default),
        encoding="utf-8",
    )

    print(f"[{now()}] Done.")
    print(json.dumps(manifest, indent=2, sort_keys=True, default=json_default))


if __name__ == "__main__":
    main()
