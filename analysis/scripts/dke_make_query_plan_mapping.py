from pathlib import Path
import pandas as pd
import re

OUT = Path("analysis/generated")
TABLE_PATH = OUT / "dke_extended_table15_compact.csv"

if not TABLE_PATH.exists():
    raise FileNotFoundError(f"Missing file: {TABLE_PATH}")

compact = pd.read_csv(TABLE_PATH)

query_plan_roots = [
    Path("analysis/generated/query_plan"),
    Path("analysis/generated/ldbc_snb_physical_query_plan"),
]

files = []
for root in query_plan_roots:
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file():
                files.append(str(p))

inventory = pd.DataFrame({"path": files})
inventory.to_csv(OUT / "dke_query_plan_inventory.csv", index=False)

manual_signals = {
    # IMDb
    "QG1_WatchItemById": "indexed lookup over WatchItem or specialized candidate root",
    "QG2_WatchItemByTitle": "title-based indexed lookup over WatchItem-oriented candidates",
    "QG3_RecommendationByGenreAndSubtype": "genre/subtype predicates and candidate root specialization",
    "QG4_AllPersonsOfTypeForWatchItem": "bridge/role traversal and indexed person access",
    "QG5_AllPersonsForEpisodesOfSeries": "episode traversal combined with role/person access",
    "QG6_EpisodesOfSeries": "COUNT_SCAN over external episodes versus embedded series document size",
    "QG7_UpdateWatchItemMetadata": "update maintenance over WatchItem-oriented physical layouts",
    "QG8_AddPersonRoleToWatchItem": "insert/update maintenance path for associative Role structures",
    "QG9_TopRatedSeriesByGenre": "generic watchitems root versus specialized series root",
    "QG10_AdvancedSearchWatchItems": "multi-predicate filtered search over WatchItem-oriented candidates",

    # FIBEN
    "Q1_CompanyProfileIBM": "selective company-root lookup; control can be competitive at small absolute latency",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "indexed corporation lookup plus descriptor/security dereferencing",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "holding/security/account traversal",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": "person-account-holding-security-company traversal",
    "Q5_ReportsAndMetricDataOfCompany": "analytical report hierarchy traversal",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": "filtered listed-security and market-value access",
    "Q7_PersonsWhoBoughtMoreIBMThanSold": "transaction aggregation over buy/sell activity",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "transaction filtering against aggregate selling-price threshold",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "transaction overlap between buy and sell paths",
    "Q10_CreateAccountHoldingAndBuyTransaction": "insert/update case; read-style executionStats may be skipped or reported separately",

    # LDBC
    "IC7_RecentLikers": "person-rooted access plus likes associative edge",
    "Official IC/IS/INS aggregate": "official workload query-plan evidence across IC, IS, and INS operations",
}

manual_expected_experiments = {
    # IMDb
    "QG6_EpisodesOfSeries": "IMDb group B / QG6 containment query-plan",
    "QG9_TopRatedSeriesByGenre": "IMDb QG9 validation",
    "QG4_AllPersonsOfTypeForWatchItem": "IMDb group C roles query-plan",
    "QG5_AllPersonsForEpisodesOfSeries": "IMDb group C QG5 with episodes query-plan",
    "QG8_AddPersonRoleToWatchItem": "IMDb group D update/insert query-plan",
    "QG3_RecommendationByGenreAndSubtype": "IMDb group A query-plan",
    "QG10_AdvancedSearchWatchItems": "IMDb group A or filtered-search query-plan",

    # FIBEN
    "Q1_CompanyProfileIBM": "FIBEN read-query explain-plan validation",
    "Q2_CompanyWithIndustryCountryAndListedSecurities": "FIBEN Q2 detailed query-plan validation",
    "Q3_SecuritiesHeldInEachFinancialServiceAccount": "FIBEN read-query explain-plan validation",
    "Q4_CompaniesReachedFromPersonThroughAccountHoldingListedSecurity": "FIBEN read-query explain-plan validation",
    "Q5_ReportsAndMetricDataOfCompany": "FIBEN read-query explain-plan validation",
    "Q6_TechUSListedSecuritiesWithHighLastTradedValue": "FIBEN read-query explain-plan validation",
    "Q7_PersonsWhoBoughtMoreIBMThanSold": "FIBEN read-query explain-plan validation",
    "Q8_IBMTransactionsBelowAverageSellingPrice": "FIBEN read-query explain-plan validation",
    "Q9_PersonsWhoBoughtAndSoldSameStock": "FIBEN read-query explain-plan validation",
    "Q10_CreateAccountHoldingAndBuyTransaction": "FIBEN Q10 skipped for read-style query-plan or handled as write workload",

    # LDBC
    "IC7_RecentLikers": "LDBC SNB physical query-plan IC7 representative case",
    "Official IC/IS/INS aggregate": "LDBC SNB physical query-plan aggregate",
}

def normalize(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()

def query_tokens(query_name):
    q = normalize(query_name)
    toks = []

    # IDs
    id_match = re.match(r"(qg10|qg[1-9]|q10|q[1-9]|ic7|official)", q)
    if id_match:
        toks.append(id_match.group(1))

    # Relevant words
    for part in q.split():
        if len(part) >= 5:
            toks.append(part)

    # Extra synonyms
    extra = {
        "QG6_EpisodesOfSeries": ["qg6", "episodes", "series", "containment"],
        "QG9_TopRatedSeriesByGenre": ["qg9", "top", "rated", "series", "genre"],
        "QG4_AllPersonsOfTypeForWatchItem": ["qg4", "persons", "roles", "watchitem"],
        "QG5_AllPersonsForEpisodesOfSeries": ["qg5", "persons", "episodes", "series", "roles"],
        "QG8_AddPersonRoleToWatchItem": ["qg8", "add", "person", "role", "update"],
        "Q2_CompanyWithIndustryCountryAndListedSecurities": ["q2", "company", "industry", "country", "listed"],
        "Q3_SecuritiesHeldInEachFinancialServiceAccount": ["q3", "securities", "holding", "account"],
        "Q5_ReportsAndMetricDataOfCompany": ["q5", "reports", "metric", "company"],
        "IC7_RecentLikers": ["ic7", "recent", "likers"],
        "Official IC/IS/INS aggregate": ["ldbc", "physical", "query", "plan"],
    }
    toks.extend(extra.get(query_name, []))

    # unique, stable
    seen = set()
    out = []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def file_score(path, dataset, query_name):
    p = normalize(path)
    toks = query_tokens(query_name)

    score = 0

    # dataset signal
    if dataset == "ldbc_snb":
        if "ldbc" in p:
            score += 3
    elif dataset in p:
        score += 3

    # query tokens
    for tok in toks:
        if tok in p:
            score += 2

    # useful query-plan files
    useful_words = [
        "query plan", "explain", "summary", "component", "validation",
        "physical", "raw", "results", "behavior"
    ]
    for w in useful_words:
        if w in p:
            score += 1

    return score

rows = []

for _, r in compact.iterrows():
    dataset = r["dataset"]
    query_name = r["query_name"]

    scored = []
    for f in files:
        score = file_score(f, dataset, query_name)
        if score >= 5:
            scored.append((score, f))

    scored = sorted(scored, key=lambda x: (-x[0], x[1]))
    examples = [f for _, f in scored[:12]]

    if query_name == "Q10_CreateAccountHoldingAndBuyTransaction":
        status = "skipped_or_write_case"
    elif examples:
        status = "candidate_files_found"
    else:
        status = "manual_check_needed"

    rows.append({
        "dataset": dataset,
        "query_name": query_name,
        "semantic_family": r.get("semantic_family", ""),
        "expected_experiment": manual_expected_experiments.get(query_name, ""),
        "query_plan_files_found": len(scored),
        "example_query_plan_files": " | ".join(examples),
        "main_physical_signal": manual_signals.get(query_name, ""),
        "status": status,
    })

mapping = pd.DataFrame(rows)
mapping.to_csv(OUT / "dke_query_plan_mapping.csv", index=False)

# Add mapping signal to compact table
status_map = mapping.set_index(["dataset", "query_name"])["status"].to_dict()
signal_map = mapping.set_index(["dataset", "query_name"])["main_physical_signal"].to_dict()
experiment_map = mapping.set_index(["dataset", "query_name"])["expected_experiment"].to_dict()

compact["query_plan_evidence"] = compact.apply(
    lambda x: status_map.get((x["dataset"], x["query_name"]), ""),
    axis=1,
)

compact["query_plan_experiment"] = compact.apply(
    lambda x: experiment_map.get((x["dataset"], x["query_name"]), ""),
    axis=1,
)

compact["query_plan_signal"] = compact.apply(
    lambda x: signal_map.get((x["dataset"], x["query_name"]), ""),
    axis=1,
)

compact.to_csv(OUT / "dke_extended_table15_compact_with_queryplan.csv", index=False)

print("Generated:")
print(" - analysis/generated/dke_query_plan_inventory.csv")
print(" - analysis/generated/dke_query_plan_mapping.csv")
print(" - analysis/generated/dke_extended_table15_compact_with_queryplan.csv")
print()
print(mapping[[
    "dataset",
    "query_name",
    "query_plan_files_found",
    "status",
]].to_string(index=False))
