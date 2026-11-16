# Advanced experiment v1 — evidence and limitations

## Source and split

Source: NASA FY 2024 Agency Financial Report, 127 physical PDF pages; original URL and SHA-256 are in [advanced progress](advanced_progress.md). The text and visual indices cover all pages; the corrected visual v2 only repairs the two recorded page-22 errors and does not certify the remaining model descriptions.

[Benchmark candidate](../data/advanced_benchmark_v1.json): 15 answerable and 3 insufficient-evidence development questions; 24 answerable and 6 insufficient-evidence test questions. Each test answerable question has one primary group: table 6, image/diagram 5, chart 5, multi-hop 4, text 4. The `src/advanced_validate_benchmark.py` structural checker passed; this is not proof that every question or source label is correct.

The question authoring and direct page checks were performed by the AI assistant; this is not an independent human audit. Test multi-hop questions explicitly compare two financial amounts from different report pages; some compare different accounting measures numerically and must not be interpreted as accounting equivalences. All nine insufficient-evidence questions concern actual results for fiscal years after the report's November 2024 date; this is a narrow abstention test and not representative of all missing-evidence questions. The original PDF page 6 and file metadata were checked for chronology. The previous discarded drafts and known issues remain documented in [draft audit](advanced_benchmark_draft_audit.md).

## Development and selection

Two development configurations were run against the same candidate split; no gold answers or gold page regions were passed to the answering agent. Their per-question traces are in `results/advanced_dev_v1/` and `results/advanced_dev_v2/`; AI-conducted original-source reviews are `results/advanced_dev_v1_review.json` and `results/advanced_dev_v2_review.json`. Both dev configs used the corrected visual index; v2 also changed response-format instructions and normalized structured JSON answers and increased retrieved candidate/page limits, so the effect of either change alone is not isolated.

| Config | top-k per index | Max page images | Passed / 18 | Errors | Provider-reported cost |
|---|---:|---:|---:|---:|---:|
| Dev 1 | 5 | 4 | 14/18 | 2 | $0.0195034434 |
| Dev 2 | 8 | 6 | 16/18 | 0 | $0.026385732 |

Dev 2 had one incorrect abstention and one incomplete answer. It was selected before running test; the frozen settings, source hash, benchmark hash and agent script hash are in [advanced_selection_v1.json](../results/advanced_selection_v1.json). The reviewed dev score includes both answerable and insufficient-evidence cases; AI review is not an independent human assessment.

## Test results and source-based review

All 30 test questions were run with the frozen configuration. The AI assistant inspected answers, cited regions and original PDF pages and recorded each decision in [advanced_test_v1_reviews.json](../results/advanced_test_v1_reviews.json). Each individual trace is under `results/advanced_test_v1/`; machine-readable totals are in [advanced_test_v1_metrics.json](../results/advanced_test_v1_metrics.json). The trace files contain retrieval results, pages presented to the vision model, raw response where returned, token/cost usage, elapsed time and error status; the original PDF plus physical page identifies the image used. This review was carried out by AI against original images, not by an independent human reviewer.

| Main group | Pass / total | Pass rate |
|---|---:|---:|
| Table | 6/6 | 100% |
| Image / diagram | 4/5 | 80% |
| Chart | 5/5 | 100% |
| Multi-hop | 2/4 | 50% |
| Text | 4/4 | 100% |
| Insufficient evidence | 6/6 | 100% |
| **All test questions** | **27/30** | **90%** |

The rate uses all 30 questions without rounding. Three cases were marked unsuccessful:

- **I02:** the provider returned an object with no valid `answer` or `citations` keys; the system recorded a schema error. No diagnostic retry replaced this result.
- **M03:** the model computed $12,460 million correctly, but its cited page 64 does not establish the requested *principal* condition; the principal column is on page 69. The answer failed citation support. The frozen benchmark mistakenly stated $10,655 million as gold. The error was discovered after test and is preserved and corrected transparently in [M03 erratum](../data/advanced_benchmark_v1_errata.json) and a [corrected reference copy](../data/advanced_benchmark_v1_corrected_reference.json); it does not change M03's recorded fail or replace the frozen benchmark.
- **M04:** the model abstained although the report contains both required values.

TUC abstained correctly and cited page 52: page 52 was present in retrieved visual-description context, but its original image was not one of the six page images sent to the model. The reviewer checked the actual page 52 separately; this distinction is recorded in the item review.

The provider returned usage for 268,387 tokens and $0.0373156248 for the test, with one agent error. Total test wall time was approximately 366 seconds; the sum of per-case elapsed times was approximately 1,322 seconds because cases ran concurrently. Provider charges for any calls without returned usage may not be reflected.

**Interpretation:** The recorded AI source review reaches the numerical threshold exactly. It is not a confirmed 15-point bonus: benchmark M03 contained a corrected-after-test gold error; review was not independent human review; negative cases are all temporal; and indexing every page does not establish complete, correct treatment of every useful visual element. The instructor should review these limitations and original sources. No unreported rerun or replacement of failed test cases was used.

## Reproduction

See [advanced progress](advanced_progress.md) for obtaining the source PDF and constructing the text/visual indices; the corrected v2 visual snapshot additionally requires `src/advanced_correct_chart_p22.py` and rebuilding under a fresh strategy. The stored frozen configuration names `advanced_nasa_fy2024_text_v1` and `advanced_nasa_fy2024_vision_v2`. Requires a compatible Day 6 database, local MiniLM model, PyMuPDF and a private OpenRouter environment file. API runs have a cost; do not publish the key or source material without checking rights. Run from the project root in PowerShell, using new output paths:

```powershell
$day6 = 'C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter'
$python = "$day6\.venv\Scripts\python.exe"
$providerEnv = 'C:\path\to\private\.env'
& $python src\advanced_validate_benchmark.py data\advanced_benchmark_v1.json
& $python src\advanced_run_batch.py --benchmark data\advanced_benchmark_v1.json --split test --pdf data\advanced\source\nasa_fy2024_afr.pdf --day6-starter $day6 --provider-env $providerEnv --pymupdf-site 'C:\Users\ADMIN\anaconda3\Lib\site-packages' --visual-strategy advanced_nasa_fy2024_vision_v2 --workers 4 --top-k 8 --max-pages 6 --frozen-config results\advanced_selection_v1.json --output results\advanced_test_reproduction
```

The frozen original benchmark deliberately retains the incorrect M03 gold for integrity. Anyone grading a reproduction must consult the separate erratum and must independently read the original source and the model's citations. A new run can produce different results; it must not replace this run.
