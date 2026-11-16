# Advanced benchmark draft audit / Rà soát bản nháp benchmark nâng cao

**Status: rejected drafts, not a frozen benchmark. / Trạng thái: bản nháp bị từ chối, chưa phải benchmark cố định.**

The model-generated drafts are `data/advanced_benchmark_draft_dev.json`, `data/advanced_benchmark_draft_test_v1.json`, and `data/advanced_benchmark_draft_test_v2.json`. They are retained for transparency and must not be used to claim benchmark results. Every item remains marked `original_checked: false`; model output is not ground truth.

- Test v1 question T-01 and dev-004 both ask for FY 2024 total liabilities, the same answer. C-02 and M-01 repeat that value as well. Some test questions include a PDF page number in the question, revealing the gold location to the retriever.
- Test v2 I03 and X03 have the same answer (Mission Support Council), reducing question independence. The original page 38 diagram and text support the individual answer, but the duplication still requires correction.
- Test v2 M02 asks for the difference between assets in two years: both numbers are on the page 29 chart, so it can be answered from one page. M04 likewise asks for the sum of two figures both visible on the page 30 chart. These are not valid evidence of multi-hop retrieval requiring two sources. M01 is also answerable from page 22 alone, whose text gives both the 50 goals and 12 unrated.
- Test v2 unanswerable questions have not been established as absent from the complete report. U06, about cups of coffee, is a poor near-topic negative and should be replaced. Search and visual inspection need to be documented for each negative.
- A source check of page 69 confirmed that draft test v2 T04's total lease receivable principal is $697 million; page 70 confirms T05's $12,214 million undelivered orders. Those spot checks do **not** establish the other labels or sources.
- The prior smoke-test question asks for total FY 2024 assets; it must not be reused as a benchmark question. The visual descriptions contain a documented error on the page 22 chart, making original-page checking necessary.

`src/advanced_draft_benchmark.py` uses the authorized OpenRouter model and sends original page images; costs and source usage conditions apply. Draft v1 dev, v1 test and v2 test reported provider costs of $0.00805668, $0.00638288 and $0.01005455 respectively. These figures do not include any failed requests whose billing is not reported.

`src/advanced_run_batch.py` accepts a benchmark only after structural validation, isolates question text from gold, records per-question traces, and requires a matching frozen configuration and benchmark hash for test. Structural validation does not detect paraphrases, absence of evidence, source accuracy, or single-page shortcuts. The runner has not yet been exercised against a valid benchmark; no dev selection or test score exists.

Next: revise the drafts; inspect every evidence region and validate absence claims against the report; document original-source checks; fix dev/test overlap and single-page shortcuts; freeze the split; run and evaluate dev; freeze the chosen pipeline; run every test question and independently review every answer, citation, failure and cost. Do not claim 90% without the complete test and original-source assessment.
