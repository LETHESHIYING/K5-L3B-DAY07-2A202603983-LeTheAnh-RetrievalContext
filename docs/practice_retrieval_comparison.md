# Thực hành so sánh dense và TF-IDF

**Phạm vi:** một câu hỏi thực hành, không phải benchmark dev/test. Không kết luận phương pháp nào tốt hơn từ một câu. Trang PDF vật lý 62–63 (trang sách in 38–39) đã được đối chiếu bằng hình scan; câu hỏi vẫn còn mơ hồ và chưa được duyệt làm gold benchmark.

- Query gốc: `What was the purpose of the Virginia Company?`
- Corpus: file `data/history_chunks.json` xuất từ `history_B`; đã đối chiếu toàn bộ 913 bản ghi (ID, document ID, source, page, text, metadata) với database và khớp tại thời điểm chạy.
- Cấu hình TF-IDF: `starter/baseline.py`, `TfidfIndex.search`, top-k = 3, không filter; truy xuất thử đã chạy trong phiên làm việc.
- Cấu hình dense: `MyEmbedder` + `PgVectorStore.search`, `history_B`, top-k = 3, không filter. Model `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 chiều. Trace đầy đủ: [practice_dense_trace.json](practice_dense_trace.json).
- Chưa sử dụng agent, context cuối, citation hoặc nhãn evidence. Dense embedding query + search mất khoảng 0,162 giây trong một lần chạy, không gồm tải model; đây không phải phép đo hiệu năng đại diện. Thời gian TF-IDF và chi phí chưa đo đầy đủ.

| Rank | TF-IDF: PDF page | TF-IDF score | Chunk ID | Dense |
|---|---:|---:|---|---|
| 1 | 80 | 0.3407 | `4d208eefa8a5c34749cec469c19ed2543d6f004396851c273d366bf5d5e43c51` | Trang 69, 0.7036: “Prosperity in Virginia” |
| 2 | 144 | 0.2731 | `b0d1cef49390fb53d54d8c85d8c47ae07377a98e8d00624cc0ce8c964062e40d` | Trang 62, 0.6540: charter 1606 và mục đích lập thuộc địa tại Virginia |
| 3 | 80 | 0.2691 | `c9f86d65bb552d40fe3c45b321b78f4e25641b54c4c63784b71da18049fbb908` | Trang 144, 0.6509: Ohio Company |

Điểm trên đã làm tròn bốn chữ số. Dense rank 1 chỉ là tiêu đề ngắn, không đủ trả lời. Dense rank 2 tương ứng đoạn đã đối chiếu trên scan trang PDF 62: sách nói hai công ty theo charter 1606 được lập để đưa người đến lập thuộc địa ở Virginia và các vùng khác. Chunk bị cắt sau chữ “and”; phần tiếp theo nằm ngoài chunk. Trang 63 xác định hai nhóm là London Company và Plymouth Company, rồi bàn thêm nhiều động cơ chính trị và kinh tế. Vì câu hỏi không nêu rõ đang hỏi công ty nào hoặc mục đích theo charter hay động cơ rộng hơn, chunk rank 2 có evidence liên quan nhưng chưa đủ để chấm một đáp án toàn diện cho câu hỏi hiện tại. Cùng chunk về Ohio Company xuất hiện ở dense rank 3 và TF-IDF rank 2, nhưng không xác lập mục đích Virginia Company. Không so sánh trực tiếp trị số điểm cosine và TF-IDF như cùng thang đo.

## Đối chiếu scan và bài học

- Nguồn: `data/raw/american_history_1917.pdf` của dự án Day 6, trang PDF vật lý 62–63; số trang in lần lượt 38–39. Đã xem ảnh render hai trang, không chỉ dựa vào OCR.
- Trên trang 62, scan thể hiện đoạn charter nêu việc đưa người đến lập thuộc địa. Trang 63 xác định London và Plymouth là hai nhóm, đồng thời bàn về nhiều động cơ rộng hơn. Nhận định này mô tả nội dung sách, không tự khẳng định tính đầy đủ của lịch sử hiện đại.
- OCR của chunk rank 2 bị nhiễu bởi nhãn lề `The Lon- ...` và từ bị chia dòng `Planta- tion`; câu trích trong chunk kết thúc trước phần còn lại. Cả lỗi OCR lẫn ranh giới chunk đều ảnh hưởng việc đọc evidence.
- Đề xuất cho một câu hỏi mới rõ hơn: hỏi theo nội dung trang 62 về mục đích được nêu trong charter 1606 đối với hai công ty. Nếu dùng trong benchmark, vẫn cần viết đáp án/evidence, xác định split và kiểm tra độc lập theo quy tắc; không tự động tính câu thực hành này vào benchmark.
- Đề xuất thử trên dev: đưa chunk lân cận cùng trang vào context theo offset, rồi đo lại tác động đến context evidence, thời gian và budget. Đây là giả thuyết, chưa triển khai hoặc đo.

## Thực hành hybrid — RRF

Đã chạy kết hợp dense và TF-IDF trên cùng 913 chunk và cùng query. Mỗi phương pháp cung cấp top 3 candidate; RRF dùng `k=60`, trả top 3, không filter. Trace đầy đủ gồm cả hai ranking và điểm gốc: [practice_hybrid_trace.json](practice_hybrid_trace.json). Đây là một cấu hình thực hành, không phải cấu hình đã chọn trên dev.

| Hybrid rank | PDF page | RRF score | Rank dense | Rank TF-IDF | Nhận xét |
|---|---:|---:|---:|---:|---|
| 1 | 144 | 0.032002 | 3 | 2 | Chunk Ohio Company, không xác lập mục đích Virginia Company. |
| 2 | 80 | 0.016393 | — | 1 | Đề cập mục đích trong charter; chưa xác minh là evidence cho câu hỏi này. |
| 3 | 69 | 0.016393 | 1 | — | Tiêu đề “Prosperity in Virginia”, không đủ trả lời. |

Rank 1 có điểm `1/(60+3) + 1/(60+2) = 0.032002` vì xuất hiện trong cả hai ranking. Điều này cho thấy hai phương pháp có thể cùng ưu tiên một kết quả không phù hợp; RRF kết hợp thứ hạng, không tự kiểm chứng sự thật. Chunk trang 62 ở dense rank 2 có điểm `1/62` và không nằm trong hybrid top 3: hai chunk xuất hiện ở rank 1 của từng phương pháp có điểm `1/61`, cao hơn. Không suy ra hybrid luôn tệ hơn từ một query.

Code: [`src/hybrid_retrieval.py`](../src/hybrid_retrieval.py), hàm `reciprocal_rank_fusion`; runner: [`src/run_practice_hybrid.py`](../src/run_practice_hybrid.py). Hai test fusion và các test có sẵn đã chạy thành công; đây không phải đánh giá agent thực hay benchmark.

## Cần bổ sung

1. Trace thực hành cho cả ba ranking đã lưu; benchmark cần trace riêng cho từng query và cấu hình, gồm lỗi, context và agent.
2. Kiểm tra thêm các trang liên quan nếu quyết định dùng một câu hỏi rõ hơn trong benchmark.
3. Xác định gold evidence và quy tắc chấm cho câu benchmark riêng; không tự tạo nhãn từ ranking.
4. Chuẩn bị benchmark dev/test riêng, chạy ba phương pháp và báo cáo theo `BENCHMARK.md`.
