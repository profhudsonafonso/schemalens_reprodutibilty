#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Any


DEFAULT_FILE_MAP = {
    "Corporation": "CORPORATION.csv",
    "Country": "COUNTRY.csv",
    "Industry": "INDUSTRYSECTORCLASSIFIER.csv",
    "Security": "SECURITY.csv",
    "ListedSecurity": "LISTEDSECURITY.csv",
    "Person": "PERSON.csv",
    "FinancialServiceAccount": "FINANCIALSERVICEACCOUNT.csv",
    "Holding": "HOLDING.csv",
    "Transaction": "SECURITIESTRANSACTION.csv",
    "FinancialReport": "FINANCIALREPORT.csv",
    "ReportElement": "ELEMENTSOFFINANCIALREPORT.csv",
    "StatementElement": "ELEMENTOFFINANCIALSTATEMENT.csv",
}


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sniff_csv(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        sample = f.read(8192)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
        except Exception:
            dialect = csv.excel

        reader = csv.reader(f, dialect)
        header = next(reader, [])
        rows = []
        for _, row in zip(range(3), reader):
            rows.append(row)

    return {
        "delimiter": getattr(dialect, "delimiter", ","),
        "header": header,
        "sample_rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-model",
        default="DBSR_implementation/generated/fiben/dbsr_input_model.json",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Official FIBEN CSV directory, e.g. /home/.../fiben/data full",
    )
    args = parser.parse_args()

    input_model = read_json(Path(args.input_model))
    data_dir = Path(args.data_dir)

    print(f"Data dir: {data_dir}")
    print(f"Exists: {data_dir.exists()}")
    print()

    missing = []
    found = []

    for entity in input_model.get("entities", []):
        entity_name = entity["name"]
        primary_key = entity.get("primary_key", "")
        source_view = entity.get("source_view", "")
        file_name = DEFAULT_FILE_MAP.get(entity_name)
        path = data_dir / file_name if file_name else None

        print("=" * 80)
        print(f"Entity: {entity_name}")
        print(f"Source view: {source_view}")
        print(f"Primary key: {primary_key}")
        print(f"Expected file: {file_name}")

        if not path or not path.exists():
            print("Status: MISSING")
            missing.append(entity_name)
            continue

        info = sniff_csv(path)
        header = info["header"]

        print(f"Status: FOUND")
        print(f"Path: {path}")
        print(f"Delimiter: {repr(info['delimiter'])}")
        print(f"Header columns: {len(header)}")
        print(f"Primary key in header: {primary_key in header}")
        print("First columns:", header[:30])

        if primary_key and primary_key not in header:
            similar = [h for h in header if primary_key.lower() == h.lower()]
            print("Case-insensitive primary key match:", similar)

        found.append(entity_name)

    print()
    print("=" * 80)
    print(f"Found entities: {len(found)}")
    print(f"Missing entities: {len(missing)}")
    print("Missing:", missing)


if __name__ == "__main__":
    main()
