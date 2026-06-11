#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

import duckdb


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def first_existing(data_dir: Path, names):
    for name in names:
        p = data_dir / name
        if p.exists():
            return p
    raise FileNotFoundError(f"None of these files exist in {data_dir}: {names}")


def create_views(con, data_dir: Path):
    files = {
        "corporation": first_existing(data_dir, ["CORPORATION.csv", "corporation.csv"]),
        "security": first_existing(data_dir, ["SECURITY.csv", "security.csv"]),
        "listed_security": first_existing(data_dir, ["LISTEDSECURITY.csv", "listed_security.csv"]),
        "person": first_existing(data_dir, ["PERSON.csv", "person.csv"]),
        "financial_service_account": first_existing(data_dir, ["FINANCIALSERVICEACCOUNT.csv", "financial_service_account.csv"]),
        "holding": first_existing(data_dir, ["HOLDING.csv", "holding.csv"]),
        "transaction": first_existing(data_dir, ["SECURITIESTRANSACTION.csv", "securities_transaction.csv", "transaction.csv"]),
    }

    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_corporations AS
        SELECT * FROM read_csv_auto('{files["corporation"]}', header=True, all_varchar=True)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_securities AS
        SELECT * FROM read_csv_auto('{files["security"]}', header=True, all_varchar=True)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_listed_securities AS
        SELECT * FROM read_csv_auto('{files["listed_security"]}', header=True, all_varchar=True)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_persons AS
        SELECT * FROM read_csv_auto('{files["person"]}', header=True, all_varchar=True)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_financial_service_accounts AS
        SELECT * FROM read_csv_auto('{files["financial_service_account"]}', header=True, all_varchar=True)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_holdings AS
        SELECT * FROM read_csv_auto('{files["holding"]}', header=True, all_varchar=True)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW fiben_transactions AS
        SELECT * FROM read_csv_auto('{files["transaction"]}', header=True, all_varchar=True)
    """)


def build_original_pool(con, sample_size: int):
    pool = {}

    ibm_df = con.execute("""
        SELECT CORPORATIONID, HASTICKERSYMBOL, HASLEGALNAME
        FROM fiben_corporations
        WHERE upper(COALESCE(HASTICKERSYMBOL, '')) = 'IBM'
           OR upper(COALESCE(HASLEGALNAME, '')) LIKE '%IBM%'
        LIMIT 1
    """).df()

    if ibm_df.empty:
        ibm_df = con.execute("""
            SELECT c.CORPORATIONID, c.HASTICKERSYMBOL, c.HASLEGALNAME
            FROM fiben_corporations c
            LEFT JOIN fiben_securities s ON c.CORPORATIONID = s.ISPROVIDEDBY
            GROUP BY c.CORPORATIONID, c.HASTICKERSYMBOL, c.HASLEGALNAME
            ORDER BY COUNT(s.SECURITYID) DESC, c.CORPORATIONID
            LIMIT 1
        """).df()

    ibm_corporation_id = None if ibm_df.empty else str(ibm_df.iloc[0]["CORPORATIONID"])

    pool["Q1_CompanyProfileIBM"] = [ibm_corporation_id]
    pool["Q2_CompanyWithIndustryCountryAndListedSecurities"] = [ibm_corporation_id]
    pool["Q5_ReportsAndMetricDataOfCompany"] = [ibm_corporation_id]

    pool["Q3_SecuritiesHeldInEachFinancialServiceAccount"] = (
        con.execute(f"""
            SELECT FINANCIALSERVICEACCOUNTID
            FROM fiben_financial_service_accounts
            WHERE FINANCIALSERVICEACCOUNTID IS NOT NULL
            ORDER BY FINANCIALSERVICEACCOUNTID
            LIMIT {sample_size}
        """).df()["FINANCIALSERVICEACCOUNTID"].astype(str).tolist()
    )

    q4_df = con.execute(f"""
        SELECT
            p.PERSONID,
            COUNT(DISTINCT c.CORPORATIONID) AS n_reachable_corporations,
            COUNT(DISTINCT h.HOLDINGID) AS n_holdings
        FROM fiben_persons p
        JOIN fiben_financial_service_accounts a
          ON p.PERSONID = a.ISOWNEDBY
        JOIN fiben_holdings h
          ON a.FINANCIALSERVICEACCOUNTID = h.ISHELDBY
        JOIN fiben_securities s
          ON regexp_extract(CAST(h.REFERSTO AS VARCHAR), '([0-9]+)$') = regexp_extract(CAST(s.SECURITYID AS VARCHAR), '([0-9]+)$')
        JOIN fiben_corporations c
          ON s.ISPROVIDEDBY = c.CORPORATIONID
        GROUP BY p.PERSONID
        ORDER BY n_reachable_corporations DESC, n_holdings DESC, p.PERSONID
        LIMIT {sample_size}
    """).df()

    pool["Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity"] = (
        q4_df["PERSONID"].astype(str).tolist() if not q4_df.empty else []
    )

    pool["Q6_TechUSListedSecuritiesWithHighLastTradedValue"] = [{
        "industry_keyword": "tech",
        "country_name": "United States",
        "min_last_traded_value": 100,
    }]

    pool["Q7_PersonsWhoBoughtMoreIBMThanSold"] = [ibm_corporation_id]
    pool["Q8_IBMTransactionsBelowAverageSellingPrice"] = [ibm_corporation_id]

    pool["Q9_PersonsWhoBoughtAndSoldSameStock"] = (
        con.execute(f"""
            SELECT REFERSTO AS listed_security_id
            FROM fiben_transactions
            WHERE REFERSTO IS NOT NULL
            GROUP BY REFERSTO
            ORDER BY COUNT(*) DESC, REFERSTO
            LIMIT {sample_size}
        """).df()["listed_security_id"].astype(str).tolist()
    )

    diagnostics = {
        "ibm_corporation_id": ibm_corporation_id,
        "Q3_pool": pool["Q3_SecuritiesHeldInEachFinancialServiceAccount"],
        "Q4_pool": q4_df.to_dict(orient="records") if not q4_df.empty else [],
        "Q9_pool": pool["Q9_PersonsWhoBoughtAndSoldSameStock"],
    }

    return pool, diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--base-probe", required=True)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--scale-label", default="sf10")
    parser.add_argument("--out-probe", required=True)
    parser.add_argument("--out-diagnostics", required=True)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    con = duckdb.connect(database=":memory:")
    create_views(con, data_dir)

    original_pool, diagnostics = build_original_pool(con, args.sample_size)
    probe = read_json(Path(args.base_probe))

    for q, values in original_pool.items():
        if q not in probe["parameters"]:
            probe["parameters"][q] = {}

        if q == "Q3_SecuritiesHeldInEachFinancialServiceAccount":
            probe["parameters"][q]["financial_service_account_id_pool"] = values
        elif q == "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity":
            probe["parameters"][q]["person_id_pool"] = values
        elif q == "Q9_PersonsWhoBoughtAndSoldSameStock":
            probe["parameters"][q]["listed_security_id_pool"] = values
        elif q in {
            "Q1_CompanyProfileIBM",
            "Q2_CompanyWithIndustryCountryAndListedSecurities",
            "Q5_ReportsAndMetricDataOfCompany",
            "Q7_PersonsWhoBoughtMoreIBMThanSold",
            "Q8_IBMTransactionsBelowAverageSellingPrice",
        }:
            probe["parameters"][q]["corporation_id_pool"] = values
            probe["parameters"][q]["corporation_id"] = values[0] if values else None
        elif q == "Q6_TechUSListedSecuritiesWithHighLastTradedValue":
            probe["parameters"][q].update(values[0])

    diagnostics["baseline"] = "DBSR"
    diagnostics["dataset"] = "FIBEN"
    diagnostics["scale_label"] = args.scale_label
    diagnostics["data_dir"] = str(data_dir)
    diagnostics["sample_size"] = args.sample_size
    diagnostics["method"] = "original_schema_lens_parameter_pool_reconstruction"

    write_json(Path(args.out_probe), probe)
    write_json(Path(args.out_diagnostics), diagnostics)

    print("Wrote", args.out_probe)
    print("Wrote", args.out_diagnostics)
    print("IBM corporation:", diagnostics["ibm_corporation_id"])
    print("Q3 first 10:", diagnostics["Q3_pool"][:10])
    print("Q4 first 10:", diagnostics["Q4_pool"][:10])
    print("Q9 first 10:", diagnostics["Q9_pool"][:10])


if __name__ == "__main__":
    main()
