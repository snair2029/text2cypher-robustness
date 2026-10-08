# Text-to-Cypher Research Explorer

**Honours project:** Robustness Testing for LLM-Based Text-to-Cypher Systems  
**Student:** Shreya Nair  
**Supervisor:** Ying He  
**University:** University of Technology Sydney

## About this project

This project studies how well a language model turns an everyday question
into a Cypher query.

Cypher is the language used to search a graph database. A graph stores
things such as people, movies and organisations, together with the
relationships between them.

The project checks the generated queries, compares them with dataset
reference queries, and presents the evidence in an interactive interface.

## Research questions

The project investigates two main questions:

1. **What kinds of problems occur in generated queries?**  
   Checks cover syntax, use of the supplied schema, query meaning and
   performance.

2. **Do text similarity scores reflect these problems?**  
   BLEU and Exact Match scores are compared with recorded evaluation
   outcomes and reviewed assessments.

## Data and query generation

The study uses 200 questions sampled from the Neo4j Text2Cypher 2024v1
dataset, obtained through Hugging Face.

| Question-length group | Questions |
|---|---:|
| Short (`simple`) | 50 |
| Medium-length (`medium`) | 100 |
| Long (`complex`) | 50 |
| **Total** | **200** |

These groups describe question length. They do not establish how difficult
a database query is.

Each question was supplied to the model with its graph schema. A schema
describes the available node labels, relationship types and properties.

The research journal records that all 200 final queries were generated
using **Gemini 3.1 Flash Lite** with zero-shot prompting. Zero-shot means
that the prompt did not include worked examples.

The original proposal specified GPT-4o. The model change is documented
as a scope adjustment.

Model information was not saved separately for every generated query.
The generation script and research journal provide the available record.

## What was implemented?

| Component | What it does |
|---|---|
| Query generation | Produces a Cypher query from a question and schema |
| Text metrics | Calculates BLEU and Exact Match |
| Syntax validation | Checks whether Neo4j accepts the query |
| Schema checks | Checks detected names and selected relationship endpoints |
| Logical comparison | Compares generated and reference answers where a source graph is available |
| Review records | Stores assessments, explanations and uncertain cases |
| Performance evaluation | Inspects query plans and measures selected query pairs |
| Analysis | Produces summary tables, descriptive correlations and figures |
| Research Explorer | Displays saved examples, findings and supporting evidence |

Original generated and reference queries are preserved.

## Understanding the checks

### Syntax

Syntax means the rules for writing a query.

A query can pass this check but still ask for the wrong information.

### Schema

Schema checks look at whether a query uses the names and selected
relationship patterns described in the supplied graph schema.

These checks are bounded. They do not check every possible Cypher
expression or fully establish property ownership and variable scope.

### Query meaning

Generated and reference queries are compared on the same source graph
where access is available.

Different answers require interpretation. The generated query may contain
an error, the reference may have a defect, or both may interpret an unclear
question differently.

Matching answers provide evidence of agreement on the tested graph.
They do not prove correctness on every possible graph.

### Performance

EXPLAIN shows the planned database operations.

PROFILE records operations performed during execution. The performance
study measures 52 previously matching query pairs.

Client timing includes network transfer and profiling overhead.

## Review process

Two review activities are saved separately:

- **48 flagged comparison cases:** cases where automatic comparisons
  found different values or output formats.
- **40 validation cases:** 10 short, 20 medium-length and 10 long questions.

Student researcher reviewed and accepted the assessments for the 40 validation cases. Agreement measures describe this reviewed sample;
they are not independent classifier accuracy estimates.

Some assessments used prior evaluation evidence. Uncertain cases remain separate from identified errors and cases with no error identified.

## Recorded results

| Finding | Recorded result |
|---|---:|
| Generated queries | 200 |
| Generated queries accepted by syntax validation | 198 |
| Generated syntax errors | 2 |
| Observed result matches | 52 |
| Flagged comparison cases reviewed | 48 |
| Identified generated errors within that review | 10 |
| Acceptable output alternatives within that review | 8 |
| Cases without a final binary label within that review | 30 |
| Separate validation cases reviewed | 40 |
| Performance query pairs measured | 52 |
| Mean sentence BLEU | 60.2673 / 100 |
| Historical Exact Match | 14 / 200 |
| Case-sensitive trimmed Exact Match | 13 / 200 |

The 48 flagged cases were selected because comparisons differed.
Their review counts are **not an overall logical-error rate** for all
200 queries.

Each measured query had one warm-up and three measured repetitions.
Warm-ups are excluded from measurement summaries.

## Understanding the text scores

**BLEU** measures overlap between generated and reference query text.

**Historical Exact Match** compares query text after trimming surrounding
spaces and converting it to lowercase.

**Case-sensitive trimmed Exact Match** trims surrounding spaces but
preserves capitalisation.

Text similarity is not the same as answer correctness. Different query
text can produce an acceptable answer, and similar text can contain a
meaningful error.

Spearman correlation describes how scores and recorded assessments vary
together within the stated sample. It does not establish causation or
general reliability. A constant variable has no defined correlation.

## Folder guide

| File or folder | Contents |
|---|---|
| `app.py` | Interactive Research Explorer |
| `data/` | Dataset sample and original generated queries |
| `scripts/` | Data preparation and query-generation scripts |
| `pipeline/` | Evaluation and evidence-assembly code |
| `analysis/` | Validation, tables, correlations and figures |
| `outputs/` | Saved evidence, assessments and summaries |
| `outputs/final_figures/` | Final PNG/PDF figures and captions |
| `requirements.txt` | Recorded package versions |
| `research_journal.ipynb` | Research progress and historical notes |

## Run on IHPC

Open the project folder and activate the existing environment:

```bash
cd "$HOME/text2cypher_research"
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate text2cypher
```

The evaluation work used Python 3.12.

To install recorded dependencies in a separate environment:

```bash
python -m pip install -r requirements.txt
```

Installing packages does not recreate credentials, source graphs or
the original generation session.

## Rebuild the saved analysis

Run these commands in order from the project folder.
Stop if a command reports an error.

```bash
python pipeline/run_pipeline.py
python analysis/validate_classifier.py
python analysis/cross_tabulation.py
python analysis/spearman_correlation.py
python pipeline/performance_classifier.py --summarise
python analysis/visualisations.py
```

These commands rebuild tables, performance summaries and figures from
saved evidence. They do not generate new queries or rerun database
evaluations.

The performance-summary command:

- Checks that measurements match the current query text.
- Checks that every pair has the expected repetitions.
- Excludes warm-up runs.
- Calculates median, minimum and maximum measurements.

The verified measurement file contains 416 runs: 104 warm-ups and
312 measured runs across 52 query pairs. Each query has three measured
repetitions. All 52 pairs returned matching, non-empty results in every
measured repetition.

Timing includes network transfer and PROFILE overhead. These findings
describe the tested graphs and execution session.

Keep these saved input files available:

- `data/generated_queries.csv`
- `outputs/neo4j_syntax_validation.csv`
- `outputs/schema_inventory.csv`
- `outputs/logical_validation.csv`
- `outputs/performance_validation.csv`
- `outputs/manual_review.csv`
- `outputs/human_validation.csv`
- `outputs/performance_profile.csv`

The commands produce the combined evidence, validation tables,
correlations, performance summary and final figures.
## Open the Research Explorer

### 1. Start the interface on IHPC

```bash
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Leave this terminal running.

### 2. Connect from your Mac

Open a separate Mac terminal:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:8503:127.0.0.1:8501 snair@mars16.ihpc.uts.edu.au
```

Replace `mars16` with the node running Streamlit.

Enter your IHPC password. A blank terminal afterward is normal.
Leave it open.

### 3. Open the browser

Visit:

http://localhost:8503

The interface runs on IHPC; your Mac displays it through SSH.

## Using the interface

1. Choose **Start here** for a short explanation of the workflow.
2. Choose **Explore an example** to search the 200 questions.
3. Compare the generated and reference queries.
4. Read the evaluation outcome and any saved review explanation.
5. Expand the answer samples and technical evidence when needed.
6. Choose **Research results** for the overall findings and figures.
7. Download records, measurements or figures for closer inspection.

The interface displays saved research evidence. Opening an example
does not generate or execute a new query.

## Common questions

### Why does an example say “No preview recorded”?

The case may not have an accessible source graph, or evaluation may
have stopped before an answer was saved.

A missing preview is not the same as an empty answer.

### Why are some cases uncertain?

The question may be ambiguous, the reference may contain a defect,
or the available evidence may not support a clear decision.

### Why does the page stop loading?

Check that Streamlit is running and the Mac SSH connection is open.
Both must point to the same IHPC node.

### Do I need a live database connection to view saved results?

No. The interface reads saved files.

A database connection is required when rerunning live evaluations.

## Live database access

The database tunnel is separate from the interface tunnel.

For the existing IHPC evaluation setup, set:

```bash
export NEO4J_DEMO_TUNNEL_PORT=17687
```

From a separate Mac terminal:

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 127.0.0.1:17687:demo.neo4jlabs.com:7687 snair@mars16.ihpc.uts.edu.au
```

Use the same IHPC node as the evaluation process. Relevant database
credentials must also be configured.

Keep the Mac awake and the tunnel open during live evaluations.
Preserve diagnostic and review files before rerunning evaluators,
because reruns may replace outputs and live graph contents may change.

## Important limitations

- Source graphs were not available for every question.
- Syntax acceptance does not establish correct query meaning.
- Schema checks do not cover every expression or ownership rule.
- Reference queries can contain defects.
- Unavailable and inconclusive cases are not counted as correct.
- Review findings depend on the recorded interpretation rules.
- The measured performance subset does not represent all 200 queries.
- Live graph changes can affect future results.
- File hashes identify assembled files; they do not prove which inputs
  produced earlier evaluations.

## Historical records

Earlier notebook findings and legacy classifier labels are retained
as historical evidence.

Use the revised evaluation tables and final figures for current findings.
Earlier empty-database comparisons and preliminary classifications
are not validated final error counts.

## Sharing the project

Include the code, run instructions and saved evidence needed for analysis.

Exclude:

- Credentials and `.env` files
- Python and Conda environments
- Database storage and logs
- Container images
- Caches
- Existing ZIP archives

Check scripts and notebooks for embedded credentials before sharing.
## Gemini–Gemma benchmark extension

The added **Model comparison** page compares saved Gemini and Gemma answers on the same 200 question IDs, questions, supplied schemas and reference queries. The original Gemini results and reviews remain separate.

Gemini is recorded as Gemini 3.1 Flash Lite in the generation script/journal; original per-query model metadata was not retained. The Gemma benchmark records `gemma-4-26b-a4b-it`. This comparison evaluates the recorded runs using provider defaults; it is not a controlled experiment isolating model architecture or openness.

| Metric | Gemini | Gemma |
|---|---:|---:|
| Mean saved sentence BLEU, including zeros | 60.2673 | 58.9396 |
| Lowercase trimmed Exact Match | 14/200 (7.0%) | 14/200 (7.0%) |
| Case-sensitive trimmed Exact Match | 13/200 (6.5%) | 12/200 (6.0%) |
| Neo4j syntax accepted | 198/200 (99.0%) | 183/200 (91.5%) |
| Observed reference-result matches | 52 | 38 |

BLEU is averaged from the saved per-query scores, rather than regenerated. Exact Match is recomputed from saved queries. Syntax acceptance tests parsing/planning, not logical correctness. Both models have 89 unavailable-graph outcomes but only 88 share the same IDs; syntax checks can occur before graph checks. Public graph snapshots were not immutable. Neither observed-match counts nor flagged-case reviews establish overall semantic accuracy.

On the paired records, both models have observed matches on 34 questions; only Gemini matches on 18 and only Gemma on four. The other 144 pairs include unavailable, review and inconclusive cases. The Gemma review register contains 47 AI-assisted query/schema/preview inspections without independent adjudication or database rerun. Raw automatic outcomes are preserved. The existing Gemini performance evidence is not a Gemma performance benchmark, and no cross-model runtime conclusion is made.

### Rebuild comparison outputs

From the project root, with the existing `text2cypher` environment active:

```bash
python scripts/build_model_metrics.py
python scripts/build_benchmark_comparison.py
streamlit run app.py
```

These two build scripts read saved files and write `outputs/benchmark_comparison`; they make no model API or database requests. Opening **Model comparison** also uses saved files only. The sidebar's **Update combined results** button updates the original Gemini evaluation assembly; rebuild the comparison using the commands above.

Generated outputs include three figure sets (PNG and PDF), model metrics, outcome counts, a paired crosstab, all 200 paired evidence records and input provenance hashes. `outputs/gemma_26b_schema_flag_review.csv` records the three discussed schema/reference concerns separately from the preliminary automatic inventory.

### Journal and demonstration evidence

Capture `06_Gemini_Gemma_Benchmark_Comparison.png` showing the comparison metrics and `07_Gemini_Gemma_Paired_Example.png` showing one question with both generated queries and saved outcomes. Use the generated figures directly in the report. Demonstrate navigating from the original results to Model comparison and inspecting one paired question. Keep uncertain cases visible.

The report should describe this as an extension of the existing robustness evaluation on the same sample. It can support the existing research questions; an additional research question is not required simply because a second model was added. Report the missing generation metadata, uncontrolled provider defaults, unavailable graphs, reference defects and lack of independent review as limitations.

### Same 40-case review and Gemma performance completion

After recording student verification in `outputs/gemma_40_review/gemma_40_human_validation.csv`, run `python scripts/build_review_comparison.py` to rebuild the paired review counts and figure. Verification labels `verified` and `student_verified` are accepted; pending reviews are rejected. The comparison page shows the resulting table and figure. The separate flagged logical register retains its own verification status.

Run Gemma plan inspection with `python pipeline/performance_classifier_gemma_26b.py`. Run bounded measurements with `python pipeline/performance_classifier_gemma_26b.py --profile --max-cases 200`, then `python pipeline/performance_classifier_gemma_26b.py --summarise`. The profiler selects only saved observed-result-match pairs (currently 38), not all 200. Its measurement logic is the original Gemini implementation with different input/output paths. It uses one warm-up and three measurements per generated/reference pair, alternating order, a 15-second transaction timeout and 5,000-row cap, with read-only EXPLAIN guards. It executes PROFILE queries on mapped source graphs. Do not run concurrently with other evaluation workloads.

Connection uses the existing demo graph driver and optional `NEO4J_DEMO_TUNNEL_PORT`. Gemma outputs are separately prefixed `gemma_26b_performance_`; original Gemini measurements are preserved. Inconclusive measurements cause the summary check to fail rather than silently treating them as valid. Resolve connection failures before rebuilding summaries.

After a successful summary, run `python scripts/build_performance_comparison.py`. It selects common IDs/database pairs with three repetitions and nonempty reference agreement in both saved summaries. Report this subset and its coverage, not whole-model efficiency. Client timing includes network transfer, PROFILE overhead and different evaluation dates/cache/load conditions; DB-hit differences are recorded query-plan work, not model generation speed. For a controlled latency comparison, rerun both models' saved queries together under a common schedule and environment.

### Recorded performance comparison results

Gemma completed 304 PROFILE records for 38 generated/reference pairs: 76 warm-up records and 228 measured records. Query hashes and repetition schedules passed validation; all 38 pairs matched with nonempty results in each measured repetition. The saved Gemini and Gemma summaries share 34 eligible questions. On these 34, the median per-query database-hit medians are 1,298 for Gemini and 1,312.5 for Gemma; median per-query client PROFILE time medians are 264.2265 ms and 291.8490 ms respectively. These aggregate medians describe recorded query runs; they do not establish statistical significance or controlled model-speed differences.

Rebuild the performance report figure with `python scripts/plot_performance_comparison.py`. The Model comparison page displays the summary, PNG figure and expandable paired records. Timing includes network transfer and PROFILE overhead, with runs made at different times. The final 47-case Gemma register retains its recorded student-verification status; the verified 40-case sample is a separate activity.
