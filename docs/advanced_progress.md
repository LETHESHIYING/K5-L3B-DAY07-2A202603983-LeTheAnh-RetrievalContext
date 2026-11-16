# Advanced experiment: NASA FY 2024 Agency Financial Report

## Status / Tình trạng

**Experiments and AI source review completed; bonus not confirmed.** A 127-page source has been indexed, a separate dev/test benchmark prepared, two dev configurations compared, and the frozen configuration run on all 30 test cases. AI inspection of the original pages recorded 27/30 (90%), including all errors. This is not an independent human review, and a frozen-gold arithmetic error required a transparent post-test erratum. Index completeness and eligibility for bonus remain unverified. See [experiment v1](ADVANCED_EXPERIMENT_V1.md).

**Đã chạy thí nghiệm và AI đã đối chiếu nguồn; chưa xác nhận điểm thưởng.** Tài liệu 127 trang đã được lập chỉ mục, có benchmark dev/test riêng, so sánh hai cấu hình dev và chạy toàn bộ 30 câu test sau khi chốt. Kết quả đối chiếu nguồn bằng AI là 27/30 (90%), tính cả lỗi. Đây không phải đánh giá độc lập của con người; một đáp án gold có lỗi số học và được đính chính minh bạch sau test. Chưa xác nhận tính đầy đủ của index hoặc điều kiện nhận bonus. Xem [thí nghiệm v1](ADVANCED_EXPERIMENT_V1.md).

## Document and provenance / Nguồn tài liệu

- NASA, *FY 2024 Agency Financial Report*, 127 physical PDF pages. [NASA's original PDF](https://www.nasa.gov/wp-content/uploads/2023/11/nasa-fy-2024-afr-1.pdf); [NASA financial reports listing](https://www.nasa.gov/budgets-plans-and-reports/agency-financial-reports/).
- SHA-256: `65ee29adf5f3a92fcd74701696c25dae8f2d18f1ba2e7f4fba2bcfc059acbefc`.
- NASA imagery and media have usage conditions and may include third-party content: see [NASA's media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/). The PDF and extracted page data are kept locally under ignored `data/advanced/`; the link and hash allow the source to be obtained and checked. This is not a blanket permission to redistribute third-party images or NASA marks.
- This is a **separate advanced corpus**, not an assertion that the old 92-page history corpus grew to 127 pages. Physical PDF page numbers are one greater than the printed report page numbers on examples reviewed (for example, PDF page 29 is printed page 28); check each page rather than assuming that convention throughout.

## Index / Lập chỉ mục

The Day 6 PostgreSQL database stores 812 native-text chunks from all 127 pages under the separate strategy `advanced_nasa_fy2024_text_v1`. The MiniLM model and existing pgvector table are reused. Original `history_A` and `history_B` remain separate. Native PDF text extraction does not establish correct reading order for all columns or tables and does not cover non-text visual content.

The visual-description index was built as `advanced_nasa_fy2024_vision_v1`, with 1,126 chunks covering 127 distinct PDF pages. A database query after indexing confirmed that `history_A` still had 825 chunks and `history_B` 913 chunks. Both counts alone and page coverage measure storage, not extraction accuracy or completeness.

A separate corrected snapshot and pgvector strategy `advanced_nasa_fy2024_vision_v2` were created after the two known page-22 bar-segment mistakes were compared with the original. The source vision records and v1 strategy remain intact. A read-only database query confirmed both versions have 1,126 chunks across 127 pages. `src/advanced_correct_chart_p22.py` records the original values and the narrow correction; it does not certify other page descriptions. `src/advanced_agent.py` and `src/advanced_run_batch.py` accept `--visual-strategy` to select an index version, which must be recorded in the dev-selected frozen configuration before test.

`src/advanced_vision_index.py` renders individual pages and asks the authorized DeepSeek vision model for text descriptions and approximate page regions. All 127 selected records in `data/advanced/vision_completed_v1` report success. Page 62 was retried after an invalid response and page 67 after a stalled request; the prior records are retained separately. Page 22 came from an earlier pilot with a different reasoning setting. The reported cost for the selected 127 successful records was approximately $0.1991; it does not include any charge the provider might have made for failed or timed-out attempts. The generated records are unverified, can omit information, and can misread values; they are aids for finding a page, not ground truth. `src/advanced_build_visual_index.py` can build a separate pgvector strategy only when all 127 pages have successful records. `src/advanced_search.py` searches both strategies. A successful response for each page does **not** by itself prove that all useful visual information was extracted.

## Original-page checks / Đối chiếu bản gốc

- PDF page 14: the original photograph and its caption show astronaut Kate Rubins using a hammer to drive a tube during a nighttime simulated moonwalk; the description identifies the photo and simulated moonwalk correctly. This does not validate every descriptive detail.
- PDF page 15, central framework diagram: the original shows 4 strategic goals, 12 strategic objectives and 50 performance goals; the generated description also contains these figures and the depicted arrows. This is a spot check, not a full-page certification.
- PDF page 29, central balance-sheet chart: original shows FY 2024 assets $27,504 million, liabilities $7,664 million and net position $19,840 million; these three values appear in the generated description. Other elements were not fully audited.
- PDF page 50: the original shows consolidated balance sheets for 2024 and 2023, in millions, and the generated summary identifies the table, dates and units. This does not validate every cell.
- PDF page 22, central performance chart: an error was found. The generated description assigns a red segment to Strategic Goal 3 in FY 2024, but the original shows green 10 and yellow 1 only. It also describes the FY 2023 Goal 4 segments incorrectly: the original shows green 10, yellow 1 and red 1. The visual index must not be treated as verified; benchmark scoring must compare to the original chart.

## Reproduction / Tái lập

Download the original PDF into `data/advanced/source/nasa_fy2024_afr.pdf` and verify the SHA-256 above. Install PyMuPDF, psycopg, python-dotenv and the existing Day 6 dependencies in the Python environment. Start the Day 6 PostgreSQL/pgvector service and configure its local `.env`. Do not publish credentials. The scripts refuse to overwrite an existing strategy or output directory; choose fresh names when repeating an experiment.

```powershell
$day6 = 'C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter'
$python = "$day6\.venv\Scripts\python.exe"
& $python src\advanced_ingest.py --pdf data\advanced\source\nasa_fy2024_afr.pdf --day6-starter $day6 --output data\advanced\native_text_v1 --pymupdf-site 'C:\Users\ADMIN\anaconda3\Lib\site-packages'
```

For a new run, use a fresh `--strategy` and `--output`. The optional `--pymupdf-site` points to this computer's existing PyMuPDF installation; omit it if PyMuPDF is installed in the active environment. The visual script needs an OpenRouter API key in a local environment file and makes paid requests; its `--provider-env` argument is a path, never the key itself. Confirm the source's applicable media restrictions before transmitting or redistributing its contents.

```powershell
$providerEnv = 'C:\path\to\your\private\.env' # OPENROUTER_API_KEY, never commit this file
& $python src\advanced_vision_index.py --pdf data\advanced\source\nasa_fy2024_afr.pdf --provider-env $providerEnv --pymupdf-site 'C:\Users\ADMIN\anaconda3\Lib\site-packages' --output data\advanced\vision_new --workers 3
& $python src\advanced_build_visual_index.py --vision-dir data\advanced\vision_new --day6-starter $day6 --output data\advanced\visual_index_new --strategy advanced_nasa_fy2024_vision_new
& $python src\advanced_search.py --day6-starter $day6 --query 'What are NASA total assets in FY 2024?' --top-k 5
```

The search script defaults to the `advanced_nasa_fy2024_text_v1` and `advanced_nasa_fy2024_vision_v1` strategies; specify `--text-strategy` and `--visual-strategy` when using different names. `src/advanced_agent.py` is an experimental runner that accepts only a question and asks the vision model to inspect retrieved original pages. One smoke test asked for FY 2024 total assets: it retrieved physical PDF pages 30, 13, 29 and 51, and answered $27,504 million with citations to the charts on pages 29 and 30; those values and regions were checked in the original. The local trace is `data/advanced/agent_smoke_assets.json` and includes retrieved context, page reads and provider usage. The model reported 5,865 tokens and $0.0008539 for this call. This single question is **not** a benchmark or evidence of 90% accuracy. `src/advanced_validate_benchmark.py` checks structural minimums only and cannot verify the evidence, paraphrase independence, or a claim that an answer is absent.

## Remaining advanced requirements / Việc còn lại

Three earlier machine-generated benchmark drafts were rejected after finding duplicate answers, gold page hints, and multi-hop shortcuts. See [the draft audit](advanced_benchmark_draft_audit.md). A revised candidate was later frozen and evaluated; see [experiment v1](ADVANCED_EXPERIMENT_V1.md).

Source evidence for 20 of 30 test-v2 draft questions has now been inspected against original page renderings and recorded in `data/advanced_benchmark_test_review_inprogress.json`. This AI-conducted source audit is not independent human review. The count is not a valid score or acceptance of the test set: duplicates, multi-hop shortcuts and negative cases still require correction and verification.

A non-benchmark smoke test using the corrected visual index retrieved PDF page 22. Its first call failed schema validation after a provider response; trace `data/advanced/agent_smoke_chart_v2.json` records the failure and reported cost of $0.000654676. After recording raw model content on later responses, a separate retry returned green 10, yellow 1 and red 1 for the FY 2023 Goal 4 bar, with a page-22 chart citation; this agrees with the original figure. The retry trace is `data/advanced/agent_smoke_chart_v2_retry.json`, with reported cost $0.00089691. The original failure was preserved; a successful retry does not prove robustness or count as a test result. Because the original failure trace did not retain the raw response, the exact shape of that response cannot be determined.

Remaining checks: independently review the benchmark, M03 erratum, every test decision and original source; audit visual-index omissions and accuracy beyond the samples already checked; and determine whether the temporal-negative design and the corrected gold satisfy the instructor's advanced criteria. Preserve the original frozen benchmark and test run.
