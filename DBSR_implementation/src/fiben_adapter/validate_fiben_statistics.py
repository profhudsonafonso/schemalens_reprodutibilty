#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


REQUIRED_TOP_LEVEL_FIELDS = [
    "dataset",
    "scale_label",
    "source",
    "status",
    "collections",
]

REQUIRED_COLLECTION_FIELDS = [
    "entity",
    "collection",
    "count",
    "avg_object_size_bytes",
    "size_bytes",
    "storage_size_bytes",
    "total_index_size_bytes",
    "statistics_status",
]


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_statistics(obj: Dict[str, Any], allow_template: bool) -> List[str]:
    errors: List[str] = []

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in obj:
            errors.append(f"Missing top-level field: {field}")

    if obj.get("dataset") != "FIBEN":
        errors.append("dataset must be FIBEN")

    collections = obj.get("collections", [])
    if not isinstance(collections, list) or not collections:
        errors.append("collections must be a non-empty list")
        return errors

    seen_entities = set()
    seen_collections = set()

    for idx, item in enumerate(collections):
        if not isinstance(item, dict):
            errors.append(f"collections[{idx}] must be an object")
            continue

        for field in REQUIRED_COLLECTION_FIELDS:
            if field not in item:
                errors.append(f"collections[{idx}] missing field: {field}")

        entity = item.get("entity")
        collection = item.get("collection")

        if entity in seen_entities:
            errors.append(f"duplicate entity: {entity}")
        if collection in seen_collections:
            errors.append(f"duplicate collection: {collection}")

        seen_entities.add(entity)
        seen_collections.add(collection)

        status = item.get("statistics_status")
        count = item.get("count")
        avg_size = item.get("avg_object_size_bytes")

        if status == "pending_measurement":
            if not allow_template:
                errors.append(
                    f"{entity}: pending_measurement is only allowed with --allow-template"
                )
            continue

        if count is None:
            errors.append(f"{entity}: count is required for measured statistics")
        elif not isinstance(count, int) or count < 0:
            errors.append(f"{entity}: count must be a non-negative integer")

        if avg_size is None:
            errors.append(f"{entity}: avg_object_size_bytes is required for measured statistics")
        elif not isinstance(avg_size, (int, float)) or avg_size < 0:
            errors.append(f"{entity}: avg_object_size_bytes must be a non-negative number")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--statistics",
        required=True,
        help="Path to a FIBEN DBSR statistics JSON file."
    )
    parser.add_argument(
        "--allow-template",
        action="store_true",
        help="Allow pending_measurement values for template files."
    )
    args = parser.parse_args()

    obj = read_json(Path(args.statistics))
    errors = validate_statistics(obj, allow_template=args.allow_template)

    if errors:
        print("Statistics validation failed:")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)

    print("Statistics validation passed.")
    print(f"Dataset: {obj.get('dataset')}")
    print(f"Scale: {obj.get('scale_label')}")
    print(f"Collections: {len(obj.get('collections', []))}")
    print(f"Status: {obj.get('status')}")


if __name__ == "__main__":
    main()
