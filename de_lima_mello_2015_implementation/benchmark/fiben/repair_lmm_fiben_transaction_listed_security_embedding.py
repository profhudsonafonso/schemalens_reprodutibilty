from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Dict

from pymongo import MongoClient, UpdateMany


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def clean_listed_security_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    # Avoid copying large fields added later to lmm_listed_security.
    excluded = {"_id", "holding", "security_ref", "corporation_ref"}
    return {k: v for k, v in doc.items() if k not in excluded}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mongo-uri", default="mongodb://mongo:mongo@127.0.0.1:27018/admin")
    parser.add_argument("--db-name", required=True)
    parser.add_argument("--scale", required=True)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    tx = db["lmm_transaction"]
    listed = db["lmm_listed_security"]

    print(f"[{now()}] Ensuring indexes")
    tx.create_index("REFERSTO")
    listed.create_index("LISTEDSECURITYID")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_csv = output_dir / "lmm_materialization_embedding_repair_transaction_listed_security.csv"
    report_json = output_dir / "lmm_materialization_embedding_repair_transaction_listed_security.json"

    print(f"[{now()}] Loading listed securities")
    securities = []
    for doc in listed.find({}, no_cursor_timeout=True):
        sid = doc.get("LISTEDSECURITYID")
        if sid is not None:
            securities.append((sid, clean_listed_security_doc(doc)))

    print(f"[{now()}] Listed securities loaded: {len(securities)}")

    start = time.perf_counter()
    rows = []
    operations = []
    total_matched = 0
    total_modified = 0
    n_batches = 0

    for i, (sid, subdoc) in enumerate(securities, start=1):
        filt = {"REFERSTO": sid}
        if args.only_missing:
            filt["listed_security"] = {"$exists": False}

        operations.append(UpdateMany(filt, {"$set": {"listed_security": subdoc}}))

        if len(operations) >= args.batch_size:
            n_batches += 1
            batch_start = time.perf_counter()
            result = tx.bulk_write(operations, ordered=False)
            elapsed = time.perf_counter() - batch_start

            total_matched += result.matched_count
            total_modified += result.modified_count

            rows.append({
                "batch_no": n_batches,
                "operations": len(operations),
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "elapsed_seconds": elapsed,
                "status": "completed",
            })

            print(
                f"[{now()}] batch={n_batches} securities={i}/{len(securities)} "
                f"matched={result.matched_count} modified={result.modified_count} "
                f"elapsed={elapsed:.2f}s",
                flush=True,
            )

            operations = []

    if operations:
        n_batches += 1
        batch_start = time.perf_counter()
        result = tx.bulk_write(operations, ordered=False)
        elapsed = time.perf_counter() - batch_start

        total_matched += result.matched_count
        total_modified += result.modified_count

        rows.append({
            "batch_no": n_batches,
            "operations": len(operations),
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "elapsed_seconds": elapsed,
            "status": "completed",
        })

    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "batch_no",
                "operations",
                "matched_count",
                "modified_count",
                "elapsed_seconds",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "status": "completed",
        "scale": args.scale,
        "database": args.db_name,
        "relationship_name": "transaction_refers_to_listed_security",
        "parent_collection": "lmm_transaction",
        "lookup_from": "lmm_listed_security",
        "local_field": "REFERSTO",
        "foreign_field": "LISTEDSECURITYID",
        "embedded_field": "listed_security",
        "n_listed_securities": len(securities),
        "n_batches": n_batches,
        "batch_size": args.batch_size,
        "only_missing": args.only_missing,
        "total_matched": total_matched,
        "total_modified": total_modified,
        "elapsed_seconds": time.perf_counter() - start,
        "summary_csv": str(summary_csv),
        "important_note": "Repair avoids copying large later-created fields such as holding into each transaction.",
    }

    report_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(f"[{now()}] Done.")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
