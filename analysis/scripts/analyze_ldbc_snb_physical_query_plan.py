from pathlib import Path
import json
import re
import pandas as pd
import numpy as np

REPO_ROOT = Path("/home/hudson/Documents/schemalens_reprodutibilty")
SOURCE_ROOT = Path("/home/hudson/Documents/framework_test/ldbc_snb_benchmark")

BENCHMARK_DIR = SOURCE_ROOT / "results" / "physical_benchmark"
OUT_DIR = REPO_ROOT / "analysis" / "generated" / "ldbc_snb_physical_query_plan"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCALES = {
    "sf0.1": "ldbc_snb_sf0_1_full_10cold_10hot",
    "sf1": "ldbc_snb_sf1_full_10cold_10hot",
    "sf3": "ldbc_snb_sf3_full_10cold_10hot",
}

STAGE_COLUMNS = [
    "IXSCAN", "COLLSCAN", "FETCH", "SORT", "LIMIT", "PROJECTION",
    "OR", "AND_HASH", "AND_SORTED", "GROUP", "LOOKUP", "UNWIND",
    "MATCH", "ADD_FIELDS", "PROJECT"
]

def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def collect_plan_features(obj):
    stages = []
    index_names = []
    collection_names = []
    used_disk_any = False

    def visit(x):
        nonlocal used_disk_any

        if isinstance(x, dict):
            stage = x.get("stage")
            if isinstance(stage, str):
                stages.append(stage.upper())

            # Aggregation pipeline operators: $lookup, $group, $unwind, etc.
            for k in x.keys():
                if isinstance(k, str) and k.startswith("$"):
                    stages.append(k[1:].upper())

            idx = x.get("indexName")
            if isinstance(idx, str):
                index_names.append(idx)

            coll = x.get("collectionName")
            if isinstance(coll, str):
                collection_names.append(coll)

            ns = x.get("namespace")
            if isinstance(ns, str):
                collection_names.append(ns)

            if x.get("usedDisk") is True:
                used_disk_any = True

            for v in x.values():
                visit(v)

        elif isinstance(x, list):
            for item in x:
                visit(item)

    visit(obj)

    # Normalize Mongo names.
    normalized = []
    for s in stages:
        if s.startswith("PROJECTION"):
            normalized.append("PROJECTION")
        elif s in {"EQ_LOOKUP", "HASH_LOOKUP", "NLJOIN"}:
            normalized.append("LOOKUP")
        elif s in {"GROUP", "HASH_AGGREGATE"}:
            normalized.append("GROUP")
        else:
            normalized.append(s)

    stages = normalized

    return {
        "stage_list": "|".join(sorted(set(stages))),
        "index_names": "|".join(sorted(set(index_names))),
        "collection_names": "|".join(sorted(set(collection_names))),
        "used_disk_any": used_disk_any,
        **{f"has_{s}": s in stages for s in STAGE_COLUMNS},
        **{f"count_{s}": stages.count(s) for s in STAGE_COLUMNS},
    }

def parse_json_path(path: Path, scale_label: str):
    # Example folder: ic4_hot
    phase_folder = path.parent.parent.name
    m_folder = re.match(r"(?P<official>[a-z0-9]+)_(?P<phase>cold|hot)$", phase_folder, re.I)

    if m_folder:
        official_id = m_folder.group("official").upper()
        run_phase = m_folder.group("phase").lower()
    else:
        official_id = ""
        run_phase = ""

    fname = path.name

    # New query-plan filename pattern, e.g.:
    # ic7__ldbc_snb_ic7_g0_39cfc8f6__sample_001__component_002__ic7_g0_comments_by_person.json
    m_new = re.match(
        r"(?P<file_official>[a-z0-9]+)__"
        r"(?P<candidate_id>ldbc_snb_[a-z0-9]+_g\d+_[0-9a-f]+)__"
        r"sample_(?P<sample_id>\d+)__"
        r"component_(?P<component_order>\d+)__"
        r"(?P<component_name>.+)\.json$",
        fname,
        re.I
    )

    # Old query-plan filename pattern, e.g.:
    # ldbc_snb_is1_g0_edd90ee3_0_is1_person_by_id.json
    m_old = re.match(
        r"(?P<candidate_id>ldbc_snb_[a-z0-9]+_g\d+_[0-9a-f]+)_(?P<component_order>\d+)_(?P<component_name>.+)\.json$",
        fname,
        re.I
    )

    if m_new:
        candidate_id = m_new.group("candidate_id")
        component_order = int(m_new.group("component_order"))
        component_name = m_new.group("component_name")
    elif m_old:
        candidate_id = m_old.group("candidate_id")
        component_order = int(m_old.group("component_order"))
        component_name = m_old.group("component_name")
    else:
        candidate_id = ""
        component_order = np.nan
        component_name = path.stem

    g_match = re.search(r"_(g\d+)_", candidate_id, re.I)
    g_class = g_match.group(1).upper() if g_match else ""

    return {
        "scale_label": scale_label,
        "official_id": official_id,
        "run_phase": run_phase,
        "candidate_id": candidate_id,
        "candidate_key": candidate_id.lower(),
        "g_class_from_file": g_class,
        "component_order": component_order,
        "component_name": component_name,
        "json_path": str(path),
    }

def read_aggregate_files():
    rows = []
    for scale_label, folder in SCALES.items():
        cons = BENCHMARK_DIR / folder / "consolidated"
        files = sorted(cons.glob("*benchmark_aggregate_results.csv"))
        if not files:
            print(f"WARNING: no aggregate file for {scale_label} in {cons}")
            continue
        df = pd.read_csv(files[0])
        df["scale_label"] = scale_label
        df["candidate_key"] = df["candidate_id"].astype(str).str.lower()
        df["official_id"] = df["official_id"].astype(str).str.upper()
        df["run_phase"] = df["run_phase"].astype(str).str.lower()
        rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()

component_rows = []

for scale_label, folder in SCALES.items():
    base = BENCHMARK_DIR / folder
    json_files = sorted(base.glob("*/query_plan_raw_json/*.json"))

    print(f"{scale_label}: raw JSON files = {len(json_files)}")

    for path in json_files:
        meta = parse_json_path(path, scale_label)

        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            stats = obj.get("executionStats", {}) if isinstance(obj, dict) else {}
            planner = obj.get("queryPlanner", {}) if isinstance(obj, dict) else {}
            command = obj.get("command", {}) if isinstance(obj, dict) else {}

            features = collect_plan_features(obj)

            row = {
                **meta,
                "execution_success": stats.get("executionSuccess"),
                "n_returned": stats.get("nReturned"),
                "execution_time_millis": stats.get("executionTimeMillis"),
                "total_keys_examined": stats.get("totalKeysExamined"),
                "total_docs_examined": stats.get("totalDocsExamined"),
                "namespace": planner.get("namespace", ""),
                "command_type": next(iter(command.keys())) if isinstance(command, dict) and command else "",
                "ok": obj.get("ok"),
                **features,
            }

        except Exception as e:
            row = {
                **meta,
                "execution_success": False,
                "n_returned": np.nan,
                "execution_time_millis": np.nan,
                "total_keys_examined": np.nan,
                "total_docs_examined": np.nan,
                "namespace": "",
                "command_type": "",
                "ok": np.nan,
                "stage_list": "",
                "index_names": "",
                "collection_names": "",
                "used_disk_any": False,
                "parse_error": str(e),
            }

        component_rows.append(row)

components = pd.DataFrame(component_rows)

for col in ["n_returned", "execution_time_millis", "total_keys_examined", "total_docs_examined"]:
    if col in components.columns:
        components[col] = pd.to_numeric(components[col], errors="coerce")

components.to_csv(OUT_DIR / "ldbc_snb_physical_query_plan_component_results.csv", index=False)

# Candidate-level summary per query/phase/candidate.
group_cols = ["scale_label", "official_id", "run_phase", "candidate_id", "candidate_key"]

bool_cols = [c for c in components.columns if c.startswith("has_")]
count_cols = [c for c in components.columns if c.startswith("count_")]

summary = (
    components
    .groupby(group_cols, dropna=False)
    .agg(
        component_count=("component_name", "count"),
        component_names=("component_name", lambda s: "|".join(sorted(set(map(str, s))))),
        total_n_returned=("n_returned", "sum"),
        total_execution_time_millis=("execution_time_millis", "sum"),
        total_keys_examined=("total_keys_examined", "sum"),
        total_docs_examined=("total_docs_examined", "sum"),
        max_execution_time_millis=("execution_time_millis", "max"),
        max_keys_examined=("total_keys_examined", "max"),
        max_docs_examined=("total_docs_examined", "max"),
        stage_list=("stage_list", lambda s: "|".join(sorted(set("|".join(map(str, s)).split("|")) - {""}))),
        index_names=("index_names", lambda s: "|".join(sorted(set("|".join(map(str, s)).split("|")) - {""}))),
        collection_names=("collection_names", lambda s: "|".join(sorted(set("|".join(map(str, s)).split("|")) - {""}))),
        used_disk_any=("used_disk_any", "max"),
        all_execution_success=("execution_success", "min"),
    )
    .reset_index()
)

for c in bool_cols:
    tmp = components.groupby(group_cols, dropna=False)[c].max().reset_index(name=c)
    summary = summary.merge(tmp, on=group_cols, how="left")

for c in count_cols:
    tmp = components.groupby(group_cols, dropna=False)[c].sum().reset_index(name=c)
    summary = summary.merge(tmp, on=group_cols, how="left")

summary.to_csv(OUT_DIR / "ldbc_snb_physical_query_plan_candidate_summary.csv", index=False)

# Join with benchmark aggregate.
agg = read_aggregate_files()

join_cols = ["scale_label", "official_id", "run_phase", "candidate_key"]
joined = agg.merge(summary, on=join_cols, how="left", suffixes=("_benchmark", "_plan"))

joined.to_csv(OUT_DIR / "ldbc_snb_physical_benchmark_query_plan_joined.csv", index=False)

# Hot winners with plan.
hot = joined[joined["run_phase"] == "hot"].copy()
hot["p95_latency_ms"] = pd.to_numeric(hot["p95_latency_ms"], errors="coerce")
hot_winners = (
    hot.sort_values(["scale_label", "official_id", "p95_latency_ms"])
    .groupby(["scale_label", "official_id"], as_index=False)
    .first()
)

hot_winners_cols = [
    "scale_label", "official_id", "query_name", "candidate_id_benchmark",
    "g_class", "benchmark_group", "p95_latency_ms", "avg_latency_ms",
    "component_count", "total_docs_examined", "total_keys_examined",
    "total_n_returned", "total_execution_time_millis",
    "has_IXSCAN", "has_COLLSCAN", "has_FETCH", "has_SORT",
    "has_LOOKUP", "has_GROUP", "has_UNWIND", "used_disk_any",
    "stage_list", "index_names", "collection_names"
]
hot_winners_cols = [c for c in hot_winners_cols if c in hot_winners.columns]
hot_winners[hot_winners_cols].to_csv(
    OUT_DIR / "ldbc_snb_physical_hot_winners_with_query_plan.csv",
    index=False
)

# Scale-level summary.
scale_summary_rows = []

for scale, gdf in joined.groupby("scale_label"):
    scale_summary_rows.append({
        "scale_label": scale,
        "candidate_phase_rows": len(gdf),
        "component_rows": len(components[components["scale_label"] == scale]),
        "total_docs_examined": gdf["total_docs_examined"].sum(),
        "total_keys_examined": gdf["total_keys_examined"].sum(),
        "rows_with_ixscan": int(gdf.get("has_IXSCAN", pd.Series(False, index=gdf.index)).fillna(False).sum()),
        "rows_with_collscan": int(gdf.get("has_COLLSCAN", pd.Series(False, index=gdf.index)).fillna(False).sum()),
        "rows_with_sort": int(gdf.get("has_SORT", pd.Series(False, index=gdf.index)).fillna(False).sum()),
        "rows_with_lookup": int(gdf.get("has_LOOKUP", pd.Series(False, index=gdf.index)).fillna(False).sum()),
        "rows_with_group": int(gdf.get("has_GROUP", pd.Series(False, index=gdf.index)).fillna(False).sum()),
        "rows_with_unwind": int(gdf.get("has_UNWIND", pd.Series(False, index=gdf.index)).fillna(False).sum()),
    })

scale_summary = pd.DataFrame(scale_summary_rows)
scale_summary.to_csv(OUT_DIR / "ldbc_snb_physical_query_plan_scale_summary.csv", index=False)

# Compact Markdown report.
report = []
report.append("# LDBC SNB Physical Query-Plan Analysis")
report.append("")
report.append("This report consolidates MongoDB explain executionStats JSON files generated during the physical LDBC SNB benchmark.")
report.append("")
report.append("## Scale-level summary")
report.append("")
report.append(scale_summary.to_markdown(index=False))
report.append("")
report.append("## Hot winners with query-plan evidence")
report.append("")
display_cols = [
    "scale_label", "official_id", "g_class", "benchmark_group", "p95_latency_ms",
    "total_docs_examined", "total_keys_examined", "has_IXSCAN", "has_COLLSCAN",
    "has_SORT", "has_LOOKUP", "has_GROUP", "has_UNWIND"
]
display_cols = [c for c in display_cols if c in hot_winners.columns]
report.append(hot_winners[display_cols].to_markdown(index=False))
report.append("")
report.append("## Notes")
report.append("")
report.append("- Component rows correspond to individual explain JSON files.")
report.append("- Candidate summaries aggregate all explain components for the same scale, query, phase, and candidate.")
report.append("- The joined file links benchmark latency with query-plan metrics.")
report.append("- Raw JSON files are not copied to the repository; only consolidated CSV/Markdown artifacts should be committed.")

(OUT_DIR / "ldbc_snb_physical_query_plan_report.md").write_text("\n".join(report), encoding="utf-8")

print("")
print("Wrote outputs to:", OUT_DIR)
print("")
print("Component rows:", len(components))
print("Candidate summary rows:", len(summary))
print("Joined rows:", len(joined))
print("")
print("Scale summary:")
print(scale_summary.to_string(index=False))
print("")
print("Hot winners with query-plan evidence:")
print(hot_winners[display_cols].to_string(index=False))
