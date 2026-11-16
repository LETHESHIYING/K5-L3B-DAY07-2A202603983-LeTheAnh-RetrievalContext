# Day 7 — Hướng dẫn kiểm tra và tái lập phần cơ bản

## Phạm vi và trạng thái

Phần cơ bản dùng *American History* (1917), tập `history_B` của Day 6 và benchmark v2. Báo cáo chính là [2A202603983_LeTheAnh.md](../report/individual/2A202603983_LeTheAnh.md). Các kết quả có tiền tố v2 là kết quả hiện hành; kết quả cũ được giữ để truy vết. Thử thách nâng cao dùng tài liệu NASA riêng, chưa hoàn thành và không được coi là đã đạt bonus; xem [tiến độ](advanced_progress.md).

## Đầu ra cho người chấm

| Nội dung | Tệp / cách kiểm tra |
|---|---|
| Nguồn, phân chia, câu hỏi và gold | [Benchmark v2](../data/benchmark_day7_v2.json): dev 20 có đáp án + 2 thiếu evidence; test mới 5 có đáp án + 2 thiếu evidence |
| Corpus lexical | [913 chunks](../data/history_chunks.json); source ID, trang, text và metadata được xuất từ `history_B` |
| Dense, lexical, hybrid | [retrievers.py](../src/retrievers.py), [hybrid_retrieval.py](../src/hybrid_retrieval.py), [baseline.py](../starter/baseline.py) |
| Agent, model và tool | [agentic.py](../starter/agentic.py), [local_agent.py](../src/local_agent.py), [run_local_agent.py](../src/run_local_agent.py) |
| Lựa chọn trước test | [selection_v2.json](../results/selection_v2.json) và các `results/agent_dev_v2_*.json`, `results/reviews_dev_v2_*.json` |
| Kết quả test và nhãn | `results/agent_test_v2_{dense,tfidf}.json`, `results/reviews_test_v2_{dense,tfidf}.json`, `results/agent_metrics_test_v2_{dense,tfidf}.json` |
| Kiểm tra context test | [retrieval-only](../results/context_reviews_test_v2.json); [context agent](../results/agent_context_reviews_test_v2.json); [lượt dense chẩn đoán riêng](../results/review_retry_v2_dense_V2T01.json) |
| Bằng chứng V2T05 | [Evidence audit](../data/benchmark_v2_evidence_audit.json): gold tự động ban đầu thiếu điều kiện, nên phải xem chấm thủ công |
| Cấu hình, kết quả, thời gian và chi phí | [Báo cáo cá nhân](../report/individual/2A202603983_LeTheAnh.md) và trace từng câu |

Nguồn sách: [Library of Congress](https://www.loc.gov/resource/gdcmassbookdig.americanhistory01jame/). Theo báo cáo Day 6, bản số hóa được xác định là public domain tại Hoa Kỳ; kiểm tra quyền tại nơi sử dụng. Tài liệu Day 6 và cách tái tạo nằm trong [repo Day 6 của học viên](https://github.com/LETHESHIYING/K5-L3B-DAY06-LeTheAnh-2A202603983-DataIngestion), `starter/HISTORY_GUIDE.md`; quyền truy cập của người chấm chưa được xác nhận.

## Môi trường

- Python 3.11+; cài dependencies của project Day 6, PostgreSQL và pgvector theo `starter/HISTORY_GUIDE.md` của Day 6. Chạy database và thiết lập `DATABASE_URL` trong `.env` của Day 6.
- Embedding `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 chiều. Các vector và query phải dùng cùng model và revision. Dense truy vấn `history_B` trên pgvector; TF-IDF dùng file chunks xuất từ cùng collection; hybrid dùng RRF.
- Agent đã chạy qua OpenRouter với `deepseek/deepseek-v4.1-flash-1017`. Lệnh agent cần một `.env` riêng chứa `OPENROUTER_API_KEY`; không đưa key hoặc file `.env` vào bài nộp. Gọi model có chi phí và gửi câu hỏi cùng đoạn corpus được truy xuất tới provider.
- Đường dẫn dưới đây là ví dụ PowerShell; thay theo máy. Model phải có trong cache nếu bật offline mode. Không ghi đè kết quả gốc; các lệnh sử dụng đường dẫn output mới.

## Kiểm tra code

```powershell
$day6 = 'C:\Users\ADMIN\Downloads\K5-L3-Day06-DataIngestionEngineering\starter'
$python = "$day6\.venv\Scripts\python.exe"
& $python -m unittest discover -s tests -v
```

Lần kiểm tra cục bộ gần nhất sau khi sửa đọc UTF-8 trên Windows: 21/21 unit test thành công. Đây là kiểm tra code bằng fixture/mock, không thay cho đánh giá chất lượng model thật.

## Tái lập retrieval test v2

Chỉ thực hiện sau khi có database `history_B` tương ứng. Script kiểm tra nội dung export khớp database và yêu cầu file selection có trạng thái `frozen_before_test`. Chạy lại là một lượt đo mới, không thay kết quả đã nộp.

```powershell
$env:HF_HUB_OFFLINE = '1'
& $python src\run_retrieval_test.py --day6-starter $day6 --chunks data\history_chunks.json --cases data\benchmark_day7_v2.json --selection results\selection_v2.json --output results\retrieval_test_v2_reproduction
```

Script đo exact match một evidence trong một chunk. Với V2T05 điều này chưa đủ để kiểm chứng đầy đủ điều kiện; phải dùng audit và nhãn context thủ công, không diễn giải số tự động 5/5 như context đầy đủ.

## Tái lập agent test v2

Lệnh sau chạy lại có phí. Điền đường dẫn file cấu hình riêng; thay đường dẫn output nếu đã tồn tại. Để chạy baseline, thay `--method tfidf` bằng `--method dense` và dùng output khác. Tham số khớp `results/selection_v2.json`.

```powershell
$providerEnv = 'C:\path\to\private\.env'
& $python src\run_local_agent.py --day6-starter $day6 --chunks data\history_chunks.json --cases data\benchmark_day7_v2.json --output results\agent_test_v2_tfidf_reproduction.json --base-url https://openrouter.ai/api/v1 --provider-env $providerEnv --model deepseek/deepseek-v4.1-flash-1017 --method tfidf --split test --top-k 3 --candidate-depth 10 --budget 800 --max-searches 2
```

Kết quả model/API có thể thay đổi; phải tự đối chiếu từng câu và citation với nguồn. Không dùng lần chạy lại để thay timeout hoặc các điểm số của lần test chính. Các tệp metric tổng hợp nhãn đã chấm, không tự xác minh evidence.

## Giới hạn và kiểm tra cuối

- Dense test chính có một timeout trước search, nên không có context agent để chấm ở câu đó. Lần chạy lại chẩn đoán được lưu riêng. Context retrieval-only có đủ năm câu cho mỗi cấu hình.
- Tập test chỉ có bảy câu; các câu thiếu evidence đều dựa trên thời điểm sau năm xuất bản 1917. Người chuẩn bị/chấm không độc lập. OCR có lỗi. Những giới hạn này ảnh hưởng cách diễn giải, không được che giấu.
- Kiểm tra quyền truy cập nguồn và các tệp được gửi, đảm bảo không có thông tin bí mật. Nếu nộp qua Git, nội dung đã stage có thể khác nội dung working tree; xem cả hai trước khi commit. Không có thao tác push nào được thực hiện bởi hướng dẫn này.
