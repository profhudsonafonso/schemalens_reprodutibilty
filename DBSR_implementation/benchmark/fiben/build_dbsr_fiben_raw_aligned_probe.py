#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pymongo import MongoClient


TARGET_QUERIES = {
    "Q3": "Q3_SecuritiesHeldInEachFinancialServiceAccount",
    "Q4": "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity",
    "Q9": "Q9_PersonsWhoBoughtAndSoldSameStock",
}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def connect(args):
    client = MongoClient(
        host=args.mongo_host,
        port=args.mongo_port,
        username=args.mongo_username,
        password=args.mongo_password,
        authSource=args.mongo_auth_source,
        serverSelectionTimeoutMS=5000,
    )
    client.admin.command("ping")
    return client


def extract_hot_sequence(raw_path: Path, query_name: str) -> List[int]:
    rows = list(csv.DictReader(raw_path.open()))
    grouped = defaultdict(list)

    for r in rows:
        if r["query_name"] == query_name and r["run_phase"] == "hot":
            grouped[r["candidate_id"]].append(r)

    if not grouped:
        raise RuntimeError(f"No hot rows found for {query_name}")

    sequences = Counter()
    for _, rs in grouped.items():
        seq = tuple(
            int(float(r["documents_returned"]))
            for r in sorted(rs, key=lambda x: int(x["repetition"]))
        )
        sequences[seq] += 1

    return list(sequences.most_common(1)[0][0])


def list_values(doc: Dict[str, Any], path: str) -> List[Any]:
    parts = path.split(".")

    def walk(value: Any, remaining: List[str]) -> List[Any]:
        if not remaining:
            return [value]
        if isinstance(value, list):
            out = []
            for item in value:
                out.extend(walk(item, remaining))
            return out
        if isinstance(value, dict):
            key = remaining[0]
            if key not in value:
                return []
            return walk(value[key], remaining[1:])
        return []

    return [v for v in walk(doc, parts) if v is not None]


def q3_count(doc: Dict[str, Any]) -> int:
    holdings = doc.get("holding", [])
    listed_count = 0

    for h in holdings:
        listed = h.get("listedSecurity", [])
        if isinstance(listed, list):
            listed_count += len(listed)
        elif listed:
            listed_count += 1

    return 1 + len(holdings) + listed_count


def q4_count(db, person_doc: Dict[str, Any]) -> int:
    refs = [str(v) for v in list_values(person_doc, "financialServiceAccount.holding.REFERSTO")]
    if not refs:
        return 0

    security_docs = list(
        db.dbsr_rank12_listedsecurity_security_corporation.find(
            {"LISTEDSECURITYID": {"$in": refs}},
            {"security.corporation.CORPORATIONID": 1},
        )
    )

    path_count = 0

    for doc in security_docs:
        for security in doc.get("security", []):
            corporations = security.get("corporation", [])
            if isinstance(corporations, dict):
                corporations = [corporations]
            for corporation in corporations:
                if corporation.get("CORPORATIONID") is not None:
                    path_count += 1

    return path_count


def q9_counts_by_security(db) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    pipeline = [
        {
            "$match": {
                "ISFACILITATEDBY": {"$ne": None},
                "$or": [
                    {"HASTYPE": {"$in": ["1", 1, "2", 2]}},
                    {"TRANSACTIONKIND": {"$in": ["1", 1, "2", 2]}},
                    {"TRANSACTIONTYPEID": {"$in": ["1", 1, "2", 2]}},
                ],
            }
        },
        {
            "$project": {
                "REFERSTO": 1,
                "ISFACILITATEDBY": 1,
                "kind": {
                    "$toString": {
                        "$ifNull": [
                            "$HASTYPE",
                            {"$ifNull": ["$TRANSACTIONKIND", "$TRANSACTIONTYPEID"]},
                        ]
                    }
                },
            }
        },
        {
            "$group": {
                "_id": {
                    "security": "$REFERSTO",
                    "account": "$ISFACILITATEDBY",
                },
                "kinds": {"$addToSet": "$kind"},
            }
        },
        {
            "$match": {
                "kinds": {"$all": ["1", "2"]}
            }
        },
        {
            "$group": {
                "_id": "$_id.security",
                "count": {"$sum": 1},
            }
        },
    ]

    for row in db.dbsr_rank02_transaction_listedsecurity.aggregate(pipeline, allowDiskUse=True):
        counts[str(row["_id"])] = int(row["count"])

    return counts


def select_sequence_pool(
    candidates: List[Tuple[str, int]],
    target_sequence: List[int],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    # Align the DBSR parameter pool with the SchemaLens returned-count sequence.
    # Reuse is allowed because the SchemaLens raw file gives returned counts per
    # repetition but does not expose the original parameter ids.
    by_count: Dict[int, List[str]] = defaultdict(list)
    for candidate_id, returned in candidates:
        by_count[int(returned)].append(str(candidate_id))

    if not candidates:
        raise RuntimeError("No candidates available for sequence alignment.")

    pool = []
    diagnostic = []
    reuse_counter: Dict[int, int] = defaultdict(int)

    for target in target_sequence:
        exact_options = by_count.get(target, [])

        if exact_options:
            idx = reuse_counter[target] % len(exact_options)
            selected = exact_options[idx]
            selected_count = target
            match_type = "exact" if reuse_counter[target] < len(exact_options) else "exact_reused"
            reuse_counter[target] += 1
        else:
            selected, selected_count = min(
                candidates,
                key=lambda x: (abs(x[1] - target), x[1])
            )
            match_type = "nearest_reused"

        pool.append(str(selected))
        diagnostic.append({
            "target_returned_count": int(target),
            "selected_id": str(selected),
            "selected_returned_count": int(selected_count),
            "match_type": match_type,
        })

    return pool, diagnostic


def build_q3_candidates(db, target_sequence: List[int]) -> List[Tuple[str, int]]:
    needed = set(target_sequence)
    candidates = []
    nearest: Dict[int, Tuple[str, int]] = {}

    cursor = db.dbsr_rank07_financialserviceaccount_holding_listedsecurity.find(
        {},
        {"FINANCIALSERVICEACCOUNTID": 1, "holding": 1},
        no_cursor_timeout=True,
    ).batch_size(5000)

    try:
        for doc in cursor:
            account_id = doc.get("FINANCIALSERVICEACCOUNTID")
            if account_id is None:
                continue

            count = q3_count(doc)

            if count in needed:
                candidates.append((str(account_id), count))

            for target in needed:
                current = nearest.get(target)
                if current is None or abs(count - target) < abs(current[1] - target):
                    nearest[target] = (str(account_id), count)

            have = Counter(v for _, v in candidates)
            target_need = Counter(target_sequence)
            if all(have[t] >= target_need[t] for t in target_need):
                break
    finally:
        cursor.close()

    for item in nearest.values():
        if item not in candidates:
            candidates.append(item)

    return candidates


def build_q4_candidates(db, target_sequence: List[int]) -> List[Tuple[str, int]]:
    # Q4 cannot necessarily reproduce the SchemaLens documents_returned
    # sequence because the SchemaLens raw file exposes returned counts but not
    # the original parameter ids or internal counting semantics. We therefore
    # collect the highest-fanout DBSR persons and select the nearest available
    # traversal-output count.
    candidates = []

    pipeline = [
        {
            "$project": {
                "PERSONID": 1,
                "financialServiceAccount": 1,
                "holding_ref_count": {
                    "$sum": {
                        "$map": {
                            "input": {"$ifNull": ["$financialServiceAccount", []]},
                            "as": "fsa",
                            "in": {"$size": {"$ifNull": ["$$fsa.holding", []]}},
                        }
                    }
                },
            }
        },
        {"$sort": {"holding_ref_count": -1}},
        {"$limit": 5000},
    ]

    for doc in db.dbsr_rank11_person_financialserviceaccount_holding.aggregate(pipeline, allowDiskUse=True):
        person_id = doc.get("PERSONID")
        if person_id is None:
            continue

        count = q4_count(db, doc)
        candidates.append((str(person_id), int(count)))

    if not candidates:
        raise RuntimeError("No Q4 candidates found. Inspect dbsr_rank11_person_financialserviceaccount_holding.")

    return candidates


def build_q9_candidates(db, target_sequence: List[int]) -> List[Tuple[str, int]]:
    positive_counts = q9_counts_by_security(db)
    candidates = []

    for doc in db.dbsr_rank01_listedsecurity.find({}, {"LISTEDSECURITYID": 1}):
        sid = doc.get("LISTEDSECURITYID")
        if sid is None:
            continue
        sid = str(sid)
        candidates.append((sid, positive_counts.get(sid, 0)))

    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema-lens-raw", required=True)
    parser.add_argument("--base-probe", required=True)
    parser.add_argument("--mongo-host", default="127.0.0.1")
    parser.add_argument("--mongo-port", type=int, default=27018)
    parser.add_argument("--mongo-username", default="mongo")
    parser.add_argument("--mongo-password", default="mongo")
    parser.add_argument("--mongo-auth-source", default="admin")
    parser.add_argument("--mongo-db", required=True)
    parser.add_argument("--scale-label", default="sf10")
    parser.add_argument("--out-probe", required=True)
    parser.add_argument("--out-diagnostics", required=True)
    args = parser.parse_args()

    client = connect(args)
    db = client[args.mongo_db]

    raw_path = Path(args.schema_lens_raw)
    probe = read_json(Path(args.base_probe))

    sequences = {
        qid: extract_hot_sequence(raw_path, query_name)
        for qid, query_name in TARGET_QUERIES.items()
    }

    diagnostics: Dict[str, Any] = {
        "baseline": "DBSR",
        "dataset": "FIBEN",
        "scale_label": args.scale_label,
        "mongo_database": args.mongo_db,
        "schema_lens_raw": str(raw_path),
        "schema_lens_sequences": sequences,
        "notes": [
            "This probe aligns DBSR parameter pools with the SchemaLens SF10 raw returned-count sequence.",
            "It does not change DBSR document structures or indexes.",
            "The pool length is 10 so a 20-hot-run benchmark repeats the SchemaLens 10-run sequence twice.",
        ],
    }

    print("Building Q3 candidates...")
    q3_candidates = build_q3_candidates(db, sequences["Q3"])
    q3_pool, q3_diag = select_sequence_pool(q3_candidates, sequences["Q3"])

    print("Building Q4 candidates...")
    q4_candidates = build_q4_candidates(db, sequences["Q4"])
    q4_pool, q4_diag = select_sequence_pool(q4_candidates, sequences["Q4"])

    print("Building Q9 candidates...")
    q9_candidates = build_q9_candidates(db, sequences["Q9"])
    q9_pool, q9_diag = select_sequence_pool(q9_candidates, sequences["Q9"])

    probe["parameters"][TARGET_QUERIES["Q3"]]["financial_service_account_id_pool"] = q3_pool
    probe["parameters"][TARGET_QUERIES["Q4"]]["person_id_pool"] = q4_pool
    probe["parameters"][TARGET_QUERIES["Q9"]]["listed_security_id_pool"] = q9_pool

    diagnostics["Q3_selected"] = q3_diag
    diagnostics["Q4_selected"] = q4_diag
    diagnostics["Q9_selected"] = q9_diag

    write_json(Path(args.out_probe), probe)
    write_json(Path(args.out_diagnostics), diagnostics)

    print("Wrote", args.out_probe)
    print("Wrote", args.out_diagnostics)

    for qid in ["Q3", "Q4", "Q9"]:
        selected = diagnostics[f"{qid}_selected"]
        print(qid, "target:", sequences[qid])
        print(qid, "selected:", [x["selected_returned_count"] for x in selected])
        print(qid, "matches:", Counter(x["match_type"] for x in selected))


if __name__ == "__main__":
    main()
