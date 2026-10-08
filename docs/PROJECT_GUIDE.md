# Project guide

## Open the app

From the project root, with the `text2cypher` environment active:

```bash
streamlit run app.py --server.port 8501
```

The interface reads saved files. Browsing it requires neither model API access
nor a Neo4j connection. Generation and database evaluation remain separate commands.

## Where files belong

| Location | Purpose |
|---|---|
| `app.py` | Guided introduction and original Gemini evidence |
| `benchmark_view.py` | Six tabs for the Gemini–Gemma comparison |
| `scripts/` | Generation, dataset preparation and comparison builders |
| `pipeline/` | Syntax, schema, logical and performance evaluation |
| `analysis/` | Original Gemini statistical analysis and figures |
| `data/` | Saved sample, questions and original Gemini responses |
| `outputs/benchmark_gemma_26b.csv` | Final Gemma generation run |
| `outputs/benchmark_comparison/` | Paired results, charts and provenance |
| `outputs/gemma_40_review/` | Recorded same-sample review |
| `outputs/final_figures/` | Original research figures |
| `journal_screenshots/` | Research journal evidence |
| `research_journal.ipynb` | Research journal |
| `archive/source_snapshots/` | Preserved earlier code; not active scripts |
| `docs/` | Organisation, checks and installation instructions |

`benchmark_gemma.py` and the dated sequential script document the earlier
31B attempt. The active final Gemma generation entry point is
`scripts/benchmark_gemma_26b.py`; use its matching evaluators. Previous CSV
backups are retained and hidden in VS Code, rather than deleted.

## Comparison page

- Overview: text similarity and syntax acceptance.
- Database outcomes: recorded statuses and paired reference agreement.
- Compare a question: search the same question and inspect both saved responses.
- Review evidence: same 40 IDs plus the separate flagged-case register.
- Query performance: the 34 common eligible cases and measurement limits.
- Downloads: the CSV evidence behind the comparison.

Original Gemini pages are explicitly labelled. The comparison can load even
when the original combined Gemini interface files are missing.

## VS Code

Workspace settings hide archived source, historical CSV backups and caches.
To show them, temporarily disable the corresponding `files.exclude` entry
in `.vscode/settings.json`. All active script paths and evidence paths are preserved.

## Scope

Cleanup changes display and organisation, not queries, evaluations or review
judgements. The 47-case register retains its recorded verification status.
No database evaluations or model requests are required to apply this update.
