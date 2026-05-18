\# SchemaLens Revision Plan — 2026-05-18



\## Goal



The main goal of the current revision is to strengthen the experimental maturity of the SchemaLens paper. The advisor's main concern is that the current evaluation is still too descriptive. The revised version must turn the evaluation into an analytical validation.



\## Main priorities



1\. Add simple reduction baselines.

2\. Add an ablation study.

3\. Explain why configurations win.

4\. Analyze failure and near-failure cases.

5\. Discuss scale behavior.

6\. Improve repository reproducibility.



\---



\## C1 — Evaluation is too descriptive



\*\*Meaning:\*\*  

The paper explains the SchemaLens workflow, but it does not yet analyze the benchmark results deeply enough.



\*\*Action:\*\*  

Rewrite the evaluation sections to explain performance differences using cardinality, fan-out, document size, query plans, index usage, cache/materialization effects, and scale behavior.



\*\*Status:\*\* Pending.



\---



\## C2 — Explain why configurations win



\*\*Meaning:\*\*  

The paper should not only say that one configuration is faster. It should explain why it is faster.



\*\*Action:\*\*  

Add a "Why configurations win" analysis for representative cases:

\- IMDb QG6: G7 vs G8/G9.

\- IMDb association or associative case.

\- FIBEN representative case.

\- LDBC SNB failure/near-failure case.



\*\*Needs new benchmark?\*\*  

No full benchmark. Only small query-plan/explain checks may be needed.



\*\*Status:\*\* Pending.



\---



\## C3 — Add simple reduction baselines



\*\*Meaning:\*\*  

SchemaLens is currently compared mainly with the full benchmarked configuration space. The paper also needs comparison with simpler reduction strategies.



\*\*Baselines to add:\*\*

\- random-k;

\- always-reference;

\- always-embed;

\- depth-only activation;

\- relationship-type-only activation.



\*\*Action:\*\*  

Use existing aggregate benchmark CSV files to simulate these baselines.



\*\*Status:\*\* Pending.



\---



\## C4 — Add ablation study



\*\*Meaning:\*\*  

The paper must show which parts of the analytical matrix actually matter.



\*\*Ablations to add:\*\*

\- without root choice;

\- without relationship semantics;

\- without embedding depth;

\- without residual traversal;

\- without sharedness;

\- without update volatility.



\*\*Action:\*\*  

Rerun only the activation/reduction logic using the existing aggregate outputs. Do not rerun full benchmarks unless absolutely necessary.



\*\*Status:\*\* Pending.



\---



\## C5 — Failure and near-failure analysis



\*\*Meaning:\*\*  

Cases where SchemaLens does not preserve the global best should not be hidden.



\*\*Known case:\*\*  

LDBC SNB sf1 / IS4\_ContentOfMessage:

\- control winner: G0;

\- p95 = 2.288074 ms;

\- primary G1 p95 = 3.472862 ms;

\- absolute difference ≈ 1.185 ms;

\- regret = 0.51781.



\*\*Action:\*\*  

Add a subsection explaining this as a limit case and not as a hidden failure.



\*\*Status:\*\* Pending.



\---



\## C6 — Repository aggregate outputs missing



\*\*Meaning:\*\*  

The repository previously included aggregate benchmark results clearly only for IMDb. FIBEN and LDBC SNB aggregate outputs were missing.



\*\*Action completed on 2026-05-18:\*\*  

Added aggregate benchmark result CSV files for:

\- IMDb sf0.25, sf0.5, sf1;

\- FIBEN sf1, sf10, sf30;

\- LDBC SNB sf0.1, sf1, sf3.



\*\*Status:\*\* Partially resolved.



\*\*Remaining action:\*\*  

Update README and analysis notebooks to point to these files.



\---



\## C7 — Repository notebooks are hard to reproduce



\*\*Meaning:\*\*  

Some notebooks have missing markdown, development notes, local paths, Portuguese comments, or unclear outputs.



\*\*Action:\*\*  

Clean notebooks progressively:

\- remove personal paths;

\- add short markdown explanations;

\- keep useful outputs;

\- remove development comments;

\- use relative paths.



\*\*Status:\*\* Pending.



\---



\## C8 — Dependencies and reproduction commands



\*\*Meaning:\*\*  

The repository needs clearer dependency and execution instructions.



\*\*Action:\*\*  

Add or improve:

\- requirements.txt with pinned dependencies;

\- Docker/Python stack notes;

\- simple reproduction commands;

\- expected-output checks;

\- runtime/resource estimates.



\*\*Status:\*\* Pending.



\---



\## C9 — MongoDB port confusion



\*\*Meaning:\*\*  

There is confusion between MongoDB port 27017 and 27018.



\*\*Action:\*\*  

Clarify that 27017 is the MongoDB container port and 27018 may be the host-exposed port, or standardize scripts and README to one convention.



\*\*Status:\*\* Pending.



\---



\## Aggregate benchmark files now available



\### IMDb



\- analysis/imdb/benchmark\_aggregate\_results\_imdb\_all\_sfs.csv

\- analysis/imdb/benchmark\_aggregate\_results\_sf025.csv

\- analysis/imdb/benchmark\_aggregate\_results\_sf050.csv

\- analysis/imdb/benchmark\_aggregate\_results\_sf1.csv



\### FIBEN



\- analysis/fiben/benchmark\_aggregate\_results\_fiben\_sf1.csv

\- analysis/fiben/benchmark\_aggregate\_results\_fiben\_sf10.csv

\- analysis/fiben/benchmark\_aggregate\_results\_fiben\_sf30.csv



\### LDBC SNB



\- analysis/ldbc\_snb/benchmark\_aggregate\_results\_ldbc\_snb\_sf0\_1.csv

\- analysis/ldbc\_snb/benchmark\_aggregate\_results\_ldbc\_snb\_sf1.csv

\- analysis/ldbc\_snb/benchmark\_aggregate\_results\_ldbc\_snb\_sf3.csv



\---



\## Next technical step



Create a normalization script that reads all aggregate CSV files and generates:



\- analysis/generated/aggregate\_results\_all\_datasets.csv



This file will standardize the columns across IMDb, FIBEN, and LDBC SNB and will be the input for:



\- baseline\_summary.csv;

\- ablation\_summary.csv;

\- failure\_cases.csv;

\- near\_best\_summary.csv;

\- paper-ready LaTeX tables.

