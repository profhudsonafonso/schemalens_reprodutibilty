# DBSR Implementation Anonymization Checklist

Before each commit, check:

- [ ] No personal names in README, scripts, comments, or paths.
- [ ] No local paths such as `/home/<user>/...`.
- [ ] No credentials, MongoDB passwords, tokens, or private URLs.
- [ ] No raw FIBEN data.
- [ ] No MongoDB dumps.
- [ ] No generated raw explain JSON if it contains environment-specific metadata.
- [ ] No copied third-party source code without license review.
- [ ] Only aggregate CSVs, summaries, scripts, and documentation are committed.
- [ ] File names are generic and review-safe.
