# FIBEN Scale Factors (SF1, SF10, SF30) — Short Technical README

## Purpose

This artifact provides a reproducible workflow to prepare scale factors for the **FIBEN** dataset, using a **workload-induced conceptual subset** rather than the full benchmark schema.

Two usage modes are supported:

1. **Reproduce locally from the original FIBEN CSV package**
2. **Reuse pre-generated scaled datasets from an anonymous artifact repository**

---

## Option A — Reproduce the scale factors locally

Use this option if you want to rebuild the full pipeline from the original FIBEN files.

### Input
Start from the original FIBEN CSV package extracted from `data.zip`.

### Conceptual strategy
The scaled dataset is **not** the full FIBEN benchmark.  
Instead, it is a **workload-induced conceptual subset** defined from a set of representative generic queries instantiated in the FIBEN domain.

The selected conceptual subset includes these tables:

- `COUNTRY`
- `INDUSTRYSECTORCLASSIFIER`
- `CORPORATION`
- `FINANCIALREPORT`
- `ELEMENTSOFFINANCIALREPORT`
- `ELEMENTOFFINANCIALSTATEMENT`
- `DISCLOSURE`
- `SECURITY`
- `LISTEDSECURITY`
- `PERSON`
- `FINANCIALSERVICEACCOUNT`
- `HOLDING`
- `SECURITIESTRANSACTION`
- `MONETARYAMOUNT`

### Important note about the source CSV files
The original FIBEN CSV files are **headerless**.

Because of this, the pipeline must:

- read all source CSV files with `header=None`
- recover the physical schema by **column position**
- assign column names manually before extraction and scaling

This is a critical requirement. If the files are read as if they had a header row, the first data row will be incorrectly interpreted as column names.

### Main workflow

#### Step 1 — Define the conceptual scope of SF1
Define the workload-induced conceptual subset that will serve as the baseline dataset.

#### Step 2 — Map the conceptual subset to physical FIBEN tables
Associate each conceptual entity with its physical CSV table.

#### Step 3 — Define the extraction policy
Use `CORPORATION` as the main root table and define which tables are:

- fixed dimensions
- root-induced tables
- downstream-induced tables

#### Step 4 — Inspect the physical CSV package
Create manifests of the source files and verify that all selected tables are available.

#### Step 5 — Build the SF1 materialization plan
Define key propagation sets such as:

- `K_CORP`
- `K_REPORT`
- `K_REPORT_ELEMENT`
- `K_SECURITY`
- `K_LISTED_SECURITY`
- `K_ACCOUNT`
- `K_PERSON`
- `K_AMOUNT`

#### Step 6 — Recover the schema by column position
Assign the correct column names manually for each selected headerless CSV file.

#### Step 7 — Materialize SF1
Read the selected source files with the recovered positional schema and build the final SF1 subset as CSV files **with explicit headers**.

#### Step 8 — Audit SF1
Record row counts, sizes, and relationship-cardinality statistics.  
These measurements will later guide scale generation.

#### Step 9 — Define the scaling strategy
Use a **dual-root synthetic expansion strategy**:

- **corporation-rooted generation** for:
  - `CORPORATION`
  - `FINANCIALREPORT`
  - `ELEMENTSOFFINANCIALREPORT`
  - `ELEMENTOFFINANCIALSTATEMENT`
  - `DISCLOSURE`
  - `SECURITY`
  - `LISTEDSECURITY`

- **account-rooted generation** for:
  - `PERSON`
  - `FINANCIALSERVICEACCOUNT`
  - `HOLDING`
  - `SECURITIESTRANSACTION`
  - `MONETARYAMOUNT`

#### Step 10A — Generate the corporation-rooted side
Use **deterministic whole-subtree cloning** to generate:

- `CORPORATION`
- `FINANCIALREPORT`
- `ELEMENTSOFFINANCIALREPORT`
- `ELEMENTOFFINANCIALSTATEMENT`
- `DISCLOSURE`
- `SECURITY`
- `LISTEDSECURITY`

The fixed dimensions below are copied unchanged:

- `COUNTRY`
- `INDUSTRYSECTORCLASSIFIER`

#### Step 10B — Close the account-rooted side
Generate:

- `PERSON`
- `FINANCIALSERVICEACCOUNT`
- `HOLDING`
- `SECURITIESTRANSACTION`
- `MONETARYAMOUNT`

Also rebuild `LISTEDSECURITY` so that synthetic `HASLASTTRADEDVALUE` references point to synthetic `MONETARYAMOUNT` rows.

#### Step 11 — Audit and compare SF1, SF10, and SF30
Compare:

- row counts
- file sizes
- relationship-cardinality statistics

and compute structural-preservation deltas relative to SF1.

---

## Option B — Use a pre-generated anonymous artifact repository

Use this option if you do **not** want to rerun the whole preparation process.

The anonymous artifact repository should contain at least:

- the final `SF1` tables
- the final `SF10` tables
- the final `SF30` tables
- manifests
- validation reports
- the reproducibility documentation

### Recommended repository structure

```text
artifact_root/
├── sf1/
│   └── tables/
├── sf10/
│   └── tables/
├── sf30/
│   └── tables/
├── manifests/
├── validation/
└── docs/
```

### Recommended documentation in the anonymous repository

Include:

- the conceptual scope of the subset
- the selected physical tables
- the positional schema recovery notes
- the final manifests
- the referential validation reports
- the final scale comparison summary

---

## Final dataset sizes

### SF1
- Total tables: `14`
- Total rows: `10,513,440`
- Total size: `309.2206 MB`

### SF10
- Total tables: `14`
- Total rows: `105,128,091`
- Total size: `5714.1234 MB` (`5.580199 GB`)

### SF30
- Total tables: `14`
- Total rows: `315,382,871`
- Total size: `17725.0185 MB` (`17.309588 GB`)

---

## Structural preservation results

The final comparison across scales showed:

- `SF10` row ratio vs `SF1` = `9.999400`
- `SF30` row ratio vs `SF1` = `29.998066`

The main workload-relevant structural relationships were preserved exactly under the adopted cloning strategy:

- `SF10` mean absolute relative delta vs `SF1` = `0.0`
- `SF10` max absolute relative delta vs `SF1` = `0.0`
- `SF30` mean absolute relative delta vs `SF1` = `0.0`
- `SF30` max absolute relative delta vs `SF1` = `0.0`

This means the synthetic expansion preserved the audited structural profile of the workload-induced FIBEN subset.

---

## Referential validation status

The final packages for both `SF10` and `SF30` were validated successfully.

Main audited foreign-key paths included:

- `CORPORATION -> INDUSTRYSECTORCLASSIFIER`
- `CORPORATION -> COUNTRY`
- `FINANCIALREPORT -> CORPORATION`
- `ELEMENTSOFFINANCIALREPORT -> FINANCIALREPORT`
- `ELEMENTOFFINANCIALSTATEMENT -> ELEMENTSOFFINANCIALREPORT`
- `DISCLOSURE -> ELEMENTSOFFINANCIALREPORT`
- `SECURITY -> CORPORATION`
- `LISTEDSECURITY -> SECURITY`
- `LISTEDSECURITY -> MONETARYAMOUNT`
- `FINANCIALSERVICEACCOUNT -> PERSON`
- `HOLDING -> FINANCIALSERVICEACCOUNT`
- `HOLDING -> LISTEDSECURITY`
- `SECURITIESTRANSACTION -> FINANCIALSERVICEACCOUNT`
- `SECURITIESTRANSACTION -> LISTEDSECURITY`
- `SECURITIESTRANSACTION -> MONETARYAMOUNT`

All audited checks finished with:

- `missing_distinct_values = 0`
- `fk_ok = True`

---

## Practical recommendation

Use:

- `SF1` as the validated baseline
- `SF10` as the first main scaled dataset
- `SF30` as the largest main experimental dataset

`SF100` should be treated as **optional**, only if an additional stress-test configuration is needed.

Given that `SF30` already exceeds **315 million rows** and **17 GB**, it is sufficient for the main experimental evaluation in most cases.

---

## Expected artifact folders from the local workflow

```text
fiben_sf_artifacts/
├── specification/
├── manifests/
├── schema/
├── validation/
├── audit/
├── sf1_materialized/
├── scaled_corp_rooted/
│   ├── SF10/
│   └── SF30/
└── docs/
```

---

## Summary

This FIBEN scale-factor workflow does **not** blindly multiply rows.  
Instead, it:

- defines a workload-induced conceptual subset
- materializes a referentially closed `SF1`
- recovers the physical schema of headerless CSV files by position
- generates `SF10` and `SF30` through deterministic synthetic expansion
- validates structural preservation across scales

This makes the generated scale factors suitable for controlled experiments over the selected conceptual subset in MongoDB.
