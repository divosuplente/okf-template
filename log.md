# Log

Append-only history of operations on this corpus. One entry per ingest, query-fileed-back, or lint pass. Each entry starts with `## [YYYY-MM-DD] <op> | <summary>` so it is greppable: `grep "^## \[" log.md | tail -5`.

## [TEMPLATE] bootstrap | Template vault created
- Initialized directory structure from OKF template repository.
- No concepts ingested yet. Run `okf index` after adding concepts.
