# Code

Solution đã nối agent với model thật và vector store Day 6 qua các adapter bên dưới; [starter](../starter/README.md) vẫn là tài liệu khung ban đầu. Xem [hướng dẫn bàn giao phần cơ bản](../docs/MAIN_TASK_DELIVERY.md) để tái lập v2 và hiểu giới hạn kết quả.

## Export Day 6 chunks

`export_day6_chunks.py` reads an existing Day 6 PostgreSQL collection and writes the Day 7 chunk JSON contract. It validates required fields and unique IDs, orders by ID for reproducibility, and refuses to overwrite an output. It does not export vectors, modify the database, or run ingestion. Keep `.env` private.

From the Day 7 root in Windows Command Prompt, with the Day 6 database running and its dependencies installed:

```cmd
"C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter\.venv\Scripts\python.exe" src\export_day6_chunks.py --day6-env "C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter\.env" --output data\history_chunks.json
```

Adjust paths for your machine. `--strategy` defaults to `history_B`; specify `--strategy history_A` to export A instead. Verify the count and compare IDs and text with the database before benchmarking. The export provides lexical-search input; dense search still queries the original vectors. Only share permitted source data. See [data format](../data/README.md).

## Practice hybrid retrieval

`hybrid_retrieval.py` implements reciprocal rank fusion over ranked Day 7 chunk records, preserving component ranks and scores. `run_practice_hybrid.py` runs real dense and TF-IDF searches, checks the export against the database, and writes a practice trace; it is not an agent or benchmark runner. From the Day 7 root in Command Prompt:

```cmd
set HF_HUB_OFFLINE=1
"C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter\.venv\Scripts\python.exe" src\run_practice_hybrid.py --day6-starter "C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter" --chunks data\history_chunks.json --output docs\practice_hybrid_new.json --query "What was the purpose of the Virginia Company?"
```

The offline setting requires a cached model. Default candidate depth and final top-k are 3, and RRF k is 60; use `--help` to inspect options. Output must not already exist. Rerunning measures a new experiment and does not replace the recorded trace.

## Retrieval-only development evaluation

`run_retrieval_dev.py` compares three methods and two configuration variations using the 20 prior Day 6 questions. All are development data, including questions formerly labeled Day 6 test; a new independent test is required. It checks the corpus against PostgreSQL and measures conservative single-chunk evidence matches. It does not evaluate an agent, unanswerable questions, or multi-chunk evidence.

```cmd
set HF_HUB_OFFLINE=1
"C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter\.venv\Scripts\python.exe" src\run_retrieval_dev.py --day6-starter "C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter" --chunks data\history_chunks.json --questions data\day6_questions_dev_source.json --output results\retrieval_dev_new
```

`run_local_agent.py` runs the real DeepSeek agent via an OpenAI-compatible endpoint. The MiniLM model generates embeddings; DeepSeek generates agent decisions and answers. The following commands require the Day 6 environment/database and an existing private OpenRouter `.env` with `OPENROUTER_API_KEY`. Never commit or print that file. Adapt the paths and choose a new output name on each run.

```cmd
set HF_HUB_OFFLINE=1
"C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter\.venv\Scripts\python.exe" src\run_local_agent.py --day6-starter "C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter" --chunks data\history_chunks.json --cases data\benchmark_day7.json --output results\agent_dev_dense_new.json --base-url https://openrouter.ai/api/v1 --provider-env "C:\path\to\private\.env" --model deepseek/deepseek-v4.1-flash-1017 --method dense --split dev --max-searches 2
```

Repeat with `--method tfidf` and `--method hybrid`, using different output paths. Each query trace records model usage, including returned token and cost information where available. Remote calls transmit questions and retrieved source passages. Model errors are recorded, not silently replaced. This script depends on the Day 6 project and its model cache; see the Day 6 history guide to recreate its database. The output is checkpointed after every case.

The original retrieval-only test run can be reproduced with a new output directory after reviewing the frozen selection; doing so makes a new run, so preserve the recorded test as the independent result:

```cmd
"C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter\.venv\Scripts\python.exe" src\run_retrieval_test.py --day6-starter "C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter" --chunks data\history_chunks.json --cases data\benchmark_day7.json --selection results\selection.json --output results\retrieval_test_new
```

For v2, use the frozen settings in `results/selection_v2.json` and `data/benchmark_day7_v2.json`; use `--split test` and `--method dense` and `--method tfidf` separately with new output files. The historical `results/selection.json` is for the original run. Preserve original results, including model errors. Re-running an API model may produce different outputs and charges. `create_review_queue.py` prepares records for human review; `starter/agent_metrics.py` summarizes completed review labels and does not judge answers itself. `data/benchmark_v2_evidence_audit.json` documents the post-test discovery that V2T05 needs two adjacent chunks to verify the full question; original automatic metrics are retained and the report separately gives manual context ratings.

`data/benchmark_day7.json` and `results/agent_test_*.json` document the earlier test; its dense error traces lost intermediate context. After the trace and JSON-mode changes, `data/benchmark_day7_v2.json` contains new test questions; their source pages were visually inspected. The dev-based v2 configuration was saved in `results/selection_v2.json` before the new test. Do not treat old test scores as evaluating the changed code. Temporal abstention cases rely on the 1917 publication date and OCR searches and have a topical-diversity limitation.

The Day 6 source project is [the student's Day 6 repository](https://github.com/LETHESHIYING/K5-L3B-DAY06-LeTheAnh-2A202603983-DataIngestion); access by the grader has not been verified. Its `starter/HISTORY_GUIDE.md` documents the public-domain book source, OCR, database setup and ingestion. The source PDF is also available from the Library of Congress link in the individual report. Setup requires Docker, Python dependencies, the pinned embedding model, and an authorized model API key; never submit the key. Verify rights and access in the grader's environment.
