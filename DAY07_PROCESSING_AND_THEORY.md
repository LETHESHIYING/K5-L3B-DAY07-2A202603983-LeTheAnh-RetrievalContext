# Day 07 — Agentic RAG: Processing and Theory

# Day 07 — Agentic RAG: Quy trình và lý thuyết

This guide combines the lab requirements, project-specific implementation, experimental results, and the theory behind them. Examples with invented numbers are explicitly identified. The authoritative homework instructions are [README.md](README.md), [GUIDE.md](GUIDE.md), [BENCHMARK.md](BENCHMARK.md), [RUBRIC.md](RUBRIC.md), and [SUBMISSION.md](SUBMISSION.md).

Tài liệu này tổng hợp yêu cầu bài lab, cách triển khai của dự án, kết quả thí nghiệm và lý thuyết liên quan. Các ví dụ dùng số liệu giả định được đánh dấu rõ. Yêu cầu chính thức nằm trong các tệp hướng dẫn được liên kết ở trên.

## 1. Project purpose / Mục đích của dự án

**English:** Retrieval-Augmented Generation (RAG) searches a specified knowledge source, selects supporting passages, and provides those passages to a model that answers with citations or reports insufficient evidence. This lab adds an agent that can decide to search and potentially search again. The historical book is the source for answers about what that book says; it is not automatically an authority on modern historical consensus.

**Tiếng Việt:** RAG (sinh câu trả lời tăng cường truy xuất) tìm trong nguồn tài liệu xác định, chọn đoạn bằng chứng và đưa chúng cho mô hình để trả lời có trích dẫn hoặc báo không đủ bằng chứng. Bài lab bổ sung agent có thể quyết định tìm kiếm và tìm tiếp. Cuốn sách lịch sử chỉ là nguồn cho nội dung sách viết; không tự động đại diện cho đồng thuận sử học hiện đại.

```text
DAY 6: PDF → OCR → chunks → embedding model → PostgreSQL + pgvector
DAY 7: question → agent → retrieval → context → answer + citations / abstention
                                      ↓                 ↓
                             retrieval evaluation   answer evaluation
```

**Why separate stages? / Tại sao tách giai đoạn?**

- Retrieval may miss the evidence. / Truy xuất có thể không tìm thấy bằng chứng.
- Evidence may be retrieved but omitted from the final context. / Bằng chứng có thể được tìm thấy nhưng bị bỏ khỏi context cuối.
- The model may receive evidence and still answer or cite incorrectly. / Mô hình có thể nhận bằng chứng nhưng trả lời hoặc trích dẫn sai.
- An unanswerable question requires appropriate abstention. / Câu thiếu bằng chứng cần được từ chối phù hợp.

## 2. Key vocabulary / Thuật ngữ chính

| English | Tiếng Việt | Meaning / Ý nghĩa |
|---|---|---|
| Corpus | Tập tài liệu | The collection searched / Tập nội dung được tìm kiếm. |
| Chunk | Đoạn tài liệu | A smaller source passage / Đoạn nhỏ của tài liệu nguồn. |
| Embedding | Biểu diễn vector | Numeric representation of text / Biểu diễn văn bản bằng vector số. |
| Vector store | Kho vector | Stores and searches vectors / Lưu và tìm vector. |
| Retrieval | Truy xuất | Finds and ranks candidates / Tìm và xếp hạng các đoạn ứng viên. |
| Context | Ngữ cảnh | Evidence sent to the model / Nội dung bằng chứng gửi cho mô hình. |
| Evidence | Bằng chứng | Source content supporting an answer / Nội dung nguồn hỗ trợ câu trả lời. |
| Citation | Trích dẫn | Reference to the source / Dẫn chiếu tới nguồn. |
| Abstention | Từ chối trả lời | State that evidence is insufficient / Nêu rõ không đủ bằng chứng. |
| Benchmark | Bộ đánh giá | Questions, evidence, splits, and scoring rules / Câu hỏi, bằng chứng, cách chia và chấm. |
| Trace | Nhật ký thực thi | Recorded calls, results, context, and errors / Nhật ký lời gọi, kết quả, context và lỗi. |

## 3. Project data and current implementation / Dữ liệu và triển khai hiện tại

**English:** Day 6 uses the 1917 book *American History*. Its documented corpus contains 92 selected content pages. The `history_A` collection has 825 chunks and `history_B` has 913, as checked in the earlier database session. A uses fixed 240-character windows with 24-character overlap; B uses paragraph boundaries where possible with a 240-character maximum. These are chunking configurations, not separate retrieval methods.

**Tiếng Việt:** Day 6 sử dụng sách *American History* xuất bản năm 1917. Corpus được ghi nhận gồm 92 trang nội dung. Trong lần kiểm tra trước, `history_A` có 825 chunks và `history_B` có 913 chunks. A chia cố định 240 ký tự và chồng lấp 24 ký tự; B ưu tiên ranh giới đoạn văn, tối đa 240 ký tự. Đây là các cấu hình chunking, không phải các phương pháp retrieval khác nhau.

| Component / Thành phần | Actual configuration / Cấu hình thực tế |
|---|---|
| Embedding model / Mô hình vector | `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions. |
| Vector store / Kho vector | PostgreSQL 16.16 + pgvector 0.8.7; exact cosine search. |
| Corpus for comparison / Corpus so sánh | `history_B`, exported as `data/history_chunks.json`. |
| Retrieval methods / Phương pháp retrieval | Dense, TF-IDF, and hybrid RRF. BM25 and cross-encoder reranking are not implemented. |
| Agent model / Mô hình agent | `deepseek/deepseek-v4.1-flash-1017` via OpenRouter in the recorded experiments. |

## 4. Benchmark: question types, dev and test / Bộ đánh giá: loại câu, dev và test

**Answerable / Có đáp án:** the selected corpus contains enough evidence. Record the question, expected answer, source, physical page, and sufficient evidence. / Corpus có đủ bằng chứng; ghi câu hỏi, đáp án, nguồn, trang PDF và evidence.

**Insufficient evidence / Thiếu bằng chứng:** the selected corpus cannot support an answer. Record how this was checked; failure to find evidence in top-3 does not prove absence from the corpus. / Corpus không đủ căn cứ trả lời; ghi cách kiểm tra. Không tìm thấy trong top-3 không chứng minh toàn bộ corpus thiếu thông tin.

**Dev / Tập phát triển:** compare methods, inspect mistakes, and choose settings. **Test / Tập kiểm thử:** evaluate after the configuration and selection rule are frozen. If test results are used to tune the system, a new independent test is needed. / Dùng dev để thử và chọn cấu hình; chỉ chạy test sau khi chốt. Nếu dùng test để điều chỉnh thì cần test độc lập mới.

| Split | Answerable / Có đáp án | Insufficient / Thiếu evidence | Minimum / Tối thiểu |
|---|---:|---:|---:|
| Dev | 15 | 2 | 17 |
| Test | 5 | 2 | 7 |

Never pass gold answers, gold evidence, or answerability labels into the agent or retriever. / Không đưa đáp án chuẩn, evidence chuẩn hoặc nhãn answerability vào agent hay retriever.

## 5. Lexical search / Truy xuất từ vựng

**English:** Lexical search matches terms in the query and documents. It can work well for names, dates, and exact terminology, but synonyms, spelling, tokenization, or OCR errors can cause misses. A matching term is not proof that the passage supports the answer.

**Tiếng Việt:** Lexical search chủ yếu so khớp từ trong câu hỏi và tài liệu. Phương pháp này có thể hiệu quả với tên riêng, ngày tháng và thuật ngữ chính xác; tuy nhiên từ đồng nghĩa, lỗi chính tả, cách tách từ và lỗi OCR có thể làm mất kết quả. Có từ trùng không chứng minh đoạn đó hỗ trợ câu trả lời.

```text
corpus → tokenize documents → statistics / index
query  → same preprocessing → matching terms → scoring → ranked chunks
```

### 5.1. Terms and statistics / Từ vựng và thống kê

| Concept / Khái niệm | Definition / Định nghĩa |
|---|---|
| Token / term | Unit produced by preprocessing / Đơn vị sau tiền xử lý. |
| Vocabulary / Từ vựng | All unique terms in the indexed corpus / Tập các term khác nhau trong corpus. |
| TF `f(t,D)` | Occurrences of term `t` in document `D` / Số lần từ `t` xuất hiện trong `D`. |
| DF `df(t)` | Number of documents containing `t`; each document counts once / Số tài liệu chứa `t`, mỗi tài liệu chỉ tính một lần. |
| CF | Total occurrences throughout the corpus / Tổng số lần từ xuất hiện trong toàn corpus. |
| `N` | Number of indexed documents; here each chunk can be a document / Tổng tài liệu được lập chỉ mục; ở đây mỗi chunk có thể là một tài liệu. |
| `|D|`, `avgdl` | Number of tokens in `D` and average document length / Số token của `D` và độ dài trung bình. |

**Example / Ví dụ:** If `company` occurs five times in one chunk and appears in three chunks total, its TF in that chunk is 5, and its DF is 3. / Nếu `company` xuất hiện năm lần trong một chunk và xuất hiện ở tổng cộng ba chunks, TF của chunk đó là 5 và DF là 3.

### 5.2. Preprocessing in this project / Tiền xử lý trong dự án

The real `starter/baseline.py` uses / Hàm thực tế trong `starter/baseline.py`:

```python
def tokenize(text):
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())
```

**English:** It normalizes Unicode to NFC, applies case folding, and extracts runs of word characters. It does not implement stop-word removal, stemming, lemmatization, a Chinese word segmenter, or a Vietnamese-specific word segmenter. Unicode normalization does not repair OCR mistakes.

**Tiếng Việt:** Hàm chuẩn hóa Unicode NFC, chuẩn hóa chữ hoa/thường và lấy các chuỗi ký tự dạng từ. Nó không loại stop words, không stemming, không lemmatization và không dùng bộ tách từ chuyên biệt cho tiếng Trung hoặc tiếng Việt. Chuẩn hóa Unicode không sửa lỗi OCR.

For example, `Company` and `company` generally match after case folding, but `company` and `corporation` do not automatically match. / Ví dụ `Company` và `company` thường khớp sau case folding; `company` và `corporation` không tự động khớp.

### 5.3. Term-document matrix / Ma trận term-document

The following corpus is artificial. / Corpus dưới đây chỉ là ví dụ giả định:

```text
D1 = "virginia company company"
D2 = "ohio company"
D3 = "virginia trade"
q  = "virginia company"
```

| Document | virginia | company | ohio | trade | Length / Độ dài |
|---|---:|---:|---:|---:|---:|
| D1 | 1 | 2 | 0 | 0 | 3 |
| D2 | 0 | 1 | 1 | 0 | 2 |
| D3 | 1 | 0 | 0 | 1 | 2 |
| **DF** | **2** | **2** | **1** | **1** | — |

Here / Ở đây `N=3`, total length / tổng độ dài `=7`, and / và `avgdl=7/3≈2.3333`.

### 5.4. Inverted index / Chỉ mục đảo

An inverted index maps a term to the documents containing it; each term has a postings list. / Chỉ mục đảo ánh xạ term tới các tài liệu chứa term đó; mỗi term có một danh sách postings.

```text
virginia → [(D1, tf=1), (D3, tf=1)]
company  → [(D1, tf=2), (D2, tf=1)]
ohio     → [(D2, tf=1)]
trade    → [(D3, tf=1)]
```

The index is a data structure; TF-IDF and BM25 are scoring approaches. The current `TfidfIndex` stores in-memory sparse dictionaries and loops through the document vectors: **it does not build a postings-list inverted index**. / Chỉ mục là cấu trúc dữ liệu; TF-IDF và BM25 là cách tính điểm. `TfidfIndex` hiện tại lưu từ điển thưa trong bộ nhớ và duyệt các vector; **chưa xây dựng inverted index dạng postings list**. See / Xem [Stanford IR: inverted index](https://nlp.stanford.edu/IR-book/html/htmledition/an-example-information-retrieval-problem-1.html).

## 6. TF-IDF: theory and calculation / TF-IDF: lý thuyết và tính toán

**English:** Inverse document frequency gives lower weight to terms appearing in many documents and higher weight to rarer terms. A rare term can also be an OCR mistake, so a high IDF is not a relevance guarantee.

**Tiếng Việt:** IDF giảm trọng số của từ xuất hiện trong nhiều tài liệu và tăng trọng số tương đối của từ hiếm. Từ hiếm cũng có thể là lỗi OCR; IDF cao không bảo đảm tính liên quan.

### 6.1. Actual project formula / Công thức thực tế của dự án

```text
idf(t)       = ln((1 + N) / (1 + df(t))) + 1
weight(t,D)  = raw_tf(t,D) × idf(t)
norm(v)      = sqrt(sum(v[t]^2))
normalized_v = v / norm(v)
score(q,D)   = dot(normalized_q, normalized_D)
```

The query and document vectors are L2-normalized, so the dot product is cosine similarity. Unknown query terms are ignored; if no positive scores remain, this implementation returns an empty list. This smoothed IDF is the code's formula; other TF-IDF variants differ. / Vector query và tài liệu được chuẩn hóa L2 nên tích vô hướng tương ứng cosine similarity. Từ query không có trong vocabulary bị bỏ qua; nếu không còn điểm dương, hàm trả danh sách rỗng. Công thức IDF có smoothing này là của code hiện tại; các biến thể khác có thể khác. See / Xem [Stanford IDF](https://nlp.stanford.edu/IR-book/html/htmledition/inverse-document-frequency-1.html).

### 6.2. Worked example / Ví dụ tính tay

For the corpus in §5.3 and query `virginia company` / Với corpus ở §5.3 và query `virginia company`:

```text
a = idf(virginia) = idf(company) = ln(4/3) + 1 ≈ 1.2877
b = idf(ohio) = idf(trade)       = ln(2)   + 1 ≈ 1.6931

Vocabulary order / Thứ tự: [virginia, company, ohio, trade]
q  = [a, a, 0, 0]
D1 = [a, 2a, 0, 0]
D2 = [0, a, b, 0]
D3 = [a, 0, 0, b]
```

```text
q · D1  = 3a²
||q||   = a√2
||D1||  = a√5
cos(q,D1) = 3a² / (a√2 × a√5) = 3/√10 ≈ 0.9487

cos(q,D2) = a² / (a√2 × √(a²+b²)) ≈ 0.4280
cos(q,D3) ≈ 0.4280
```

Ranking / Xếp hạng: `D1 > D2 = D3`. The actual implementation breaks tied scores by chunk ID. Non-query terms still affect document-vector length. / Code thực tế dùng chunk ID để phá hòa; các từ không nằm trong query vẫn ảnh hưởng độ dài vector tài liệu.

### 6.3. Code map / Đường đi trong code

| File and function | Function / Chức năng |
|---|---|
| `starter/baseline.py:tokenize()` | Normalize and tokenize / Chuẩn hóa và tách từ. |
| `TfidfIndex.__init__()` | Compute TF, DF, IDF and document vectors / Tính TF, DF, IDF và vector tài liệu. |
| `TfidfIndex._vector()` | Weight and L2-normalize / Gán trọng số và chuẩn hóa L2. |
| `TfidfIndex.search()` | Encode query, compute scores, rank top-k / Mã hóa query, tính điểm và xếp top-k. |
| `src/retrievers.py:RetrievalEngine.search()` | Calls TF-IDF for `method="tfidf"` / Gọi TF-IDF khi `method="tfidf"`. |

## 7. BM25: theory and mathematics / BM25: lý thuyết và toán học

**English:** BM25 is a family of lexical ranking functions incorporating term frequency, term rarity, and document length. Scores rank documents; they are not probabilities that a result is correct. There are implementation variants. The project currently has **no BM25 implementation or BM25 benchmark results**.

**Tiếng Việt:** BM25 là một họ hàm xếp hạng từ vựng, kết hợp tần suất từ, độ hiếm và độ dài tài liệu. Điểm dùng để xếp hạng, không phải xác suất câu trả lời đúng. Có nhiều biến thể triển khai. Dự án hiện **chưa triển khai BM25 và chưa có điểm benchmark BM25**.

### 7.1. Probabilistic intuition / Trực giác xác suất

In a simplified binary independence view, the usefulness of a term can be expressed by how its odds differ between relevant and nonrelevant documents. For a term `t`, one conceptual weight is: / Theo góc nhìn binary independence đơn giản, mức hữu ích của từ có thể được biểu diễn bằng chênh lệch odds giữa tài liệu liên quan và không liên quan:

```text
weight(t) = ln( [p(t | relevant) / (1 - p(t | relevant))]
                / [p(t | nonrelevant) / (1 - p(t | nonrelevant))] )
```

In practice the true relevance probabilities are usually unavailable. BM25 uses practical approximations plus term-frequency saturation and length normalization. Its final score is not a calibrated probability. / Thực tế thường không có đầy đủ xác suất liên quan; BM25 dùng các phép xấp xỉ cùng TF saturation và chuẩn hóa độ dài. Điểm cuối không phải xác suất đã hiệu chỉnh.

### 7.2. A common formula / Một dạng công thức phổ biến

For this tutorial, use the following nonnegative Lucene-style IDF and sum over **unique query terms**. Other libraries may treat query term frequency, IDF, or normalization differently. / Trong bài này, dùng IDF không âm kiểu Lucene sau đây và cộng trên **các term query không trùng**. Thư viện khác có thể xử lý IDF, từ query lặp và chuẩn hóa khác.

```text
BM25(q,D) = Σ[t in unique(q)] IDF(t)
            × f(t,D) × (k1 + 1)
              ───────────────────────────────────────────
              f(t,D) + k1 × (1 - b + b × |D|/avgdl)

IDF(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
```

| Symbol | English | Tiếng Việt |
|---|---|---|
| `N`, `df(t)` | Corpus count and documents containing term | Số tài liệu và số tài liệu chứa term. |
| `f(t,D)` | Count of term in document | Số lần term xuất hiện trong tài liệu. |
| `|D|`, `avgdl` | Document length and average length | Độ dài tài liệu và độ dài trung bình. |
| `k1` | Controls TF saturation; nonnegative | Điều khiển độ bão hòa TF; không âm. |
| `b` | Controls length normalization, commonly 0–1 | Điều khiển chuẩn hóa độ dài, thường từ 0 đến 1. |

### 7.3. Term-frequency saturation / Bão hòa tần suất từ

If `|D|=avgdl` and `k1=1.2`, the TF component is / Khi `|D|=avgdl` và `k1=1.2`, phần TF là `f × (k1+1)/(f+k1)`:

| `f` | TF component / Thành phần TF |
|---:|---:|
| 1 | 1.0000 |
| 2 | 1.3750 |
| 5 | 1.7742 |
| 10 | 1.9643 |

More occurrences increase the contribution, but with diminishing returns. For this expression and `k1>0`, it approaches `k1+1`; the final score also depends on IDF and other terms. / Từ xuất hiện nhiều hơn có thể tăng điểm nhưng lợi ích tăng thêm giảm dần. Với công thức này và `k1>0`, thành phần tiến gần `k1+1`; điểm cuối còn phụ thuộc IDF và các term khác.

### 7.4. Length normalization / Chuẩn hóa độ dài

The factor `1-b+b|D|/avgdl` adjusts for document length. With all else equal, longer documents may be penalized more because they have more opportunities for accidental word matches. `b=0` removes this adjustment; `b=1` applies the full ratio. / Hệ số `1-b+b|D|/avgdl` điều chỉnh độ dài. Khi các yếu tố khác như nhau, tài liệu dài có thể chịu điều chỉnh lớn hơn vì có nhiều cơ hội chứa từ ngẫu nhiên. `b=0` bỏ điều chỉnh; `b=1` áp dụng toàn bộ tỷ lệ.

At `k1=0`, an occurring term has TF contribution 1 in this formula. An absent term contributes 0; do not evaluate `0/0`. Elasticsearch documents defaults `k1=1.2`, `b=0.75`, but these are implementation defaults, not a universal optimum. / Khi `k1=0`, term có xuất hiện đóng góp phần TF bằng 1 trong công thức này; term không xuất hiện đóng góp 0, không tính `0/0`. Elasticsearch dùng mặc định `k1=1.2`, `b=0.75`; đó không phải giá trị tối ưu cho mọi bài toán. [Official BM25 settings / Tài liệu BM25 chính thức](https://www.elastic.co/docs/reference/elasticsearch/index-settings/similarity).

### 7.5. Full numerical example / Ví dụ tính toán đầy đủ

Use the artificial corpus from §5.3, `q="virginia company"`, and assume `k1=1.2`, `b=0.75`. / Dùng corpus giả định ở §5.3, `q="virginia company"`, giả sử `k1=1.2`, `b=0.75`.

```text
N=3, avgdl=7/3, df(virginia)=df(company)=2
IDF(virginia)=IDF(company)=ln(1+(3-2+0.5)/(2+0.5))
                            =ln(1.6) ≈ 0.4700

K(D)=k1 × (1-b+b|D|/avgdl)
term_score(t,D)=IDF(t) × f(t,D)(k1+1)/(f(t,D)+K(D))
```

For D1 / Với D1: `|D1|=3`, `f(virginia,D1)=1`, `f(company,D1)=2`.

```text
K(D1)=1.2 × (0.25 + 0.75 × 3/(7/3)) ≈ 1.4571
virginia: 0.4700 × 2.2 / (1+1.4571) ≈ 0.4208
company:  0.4700 × 4.4 / (2+1.4571) ≈ 0.5982
BM25(q,D1) ≈ 0.4208 + 0.5982 = 1.0190
```

For D2 / Với D2: `|D2|=2`, only `company` matches once / chỉ `company` xuất hiện một lần.

```text
K(D2)=1.2 × (0.25 + 0.75 × 2/(7/3)) ≈ 1.0714
company: 0.4700 × 2.2 / (1+1.0714) ≈ 0.4992
virginia: 0
BM25(q,D2) ≈ 0.4992
BM25(q,D3) ≈ 0.4992  # symmetric in this toy example / đối xứng trong ví dụ
```

| Document | TF-IDF cosine | BM25 example | Ranking / Xếp hạng |
|---|---:|---:|---|
| D1 | 0.9487 | 1.0190 | 1 |
| D2 | 0.4280 | 0.4992 | Tie / Hòa |
| D3 | 0.4280 | 0.4992 | Tie / Hòa |

The ranking happens to match in this example. The raw scores are on different scales; `1.0190 > 0.9487` does **not** prove BM25 is better. / Xếp hạng tình cờ giống nhau. Điểm ở các thang đo khác nhau; `1.0190 > 0.9487` **không** chứng minh BM25 tốt hơn.

### 7.6. When might BM25 help or fail? / Khi nào BM25 có thể hữu ích hoặc thất bại?

**English:** BM25 may help when exact terms such as names or dates are reliable. It can fail on synonyms, OCR errors, ambiguous entities, chunk boundaries, and overly common or repeated terms. A rare term can still be irrelevant. No ranking score proves a citation supports an answer.

**Tiếng Việt:** BM25 có thể hữu ích khi tên riêng hoặc ngày tháng chính xác là tín hiệu tốt. Nó có thể thất bại với từ đồng nghĩa, lỗi OCR, thực thể mơ hồ, ranh giới chunk và từ quá phổ biến hoặc lặp lại. Từ hiếm vẫn có thể không liên quan. Điểm xếp hạng không chứng minh citation hỗ trợ câu trả lời.

In our actual practice question, a passage about the **Ohio Company** ranked highly when asking about the Virginia Company. Those are TF-IDF/dense/hybrid results, **not BM25 results**. / Trong câu thực hành, đoạn về **Ohio Company** có thứ hạng cao khi hỏi về Virginia Company. Đó là kết quả TF-IDF/dense/hybrid, **không phải kết quả BM25**. See / Xem [practice comparison](docs/practice_retrieval_comparison.md).

### 7.7. How to test BM25 later / Cách thử BM25 sau này

1. Use the same permitted chunks and question sets; record tokenizer, library version, IDF variant, `k1`, `b`, and document-length definition. / Dùng cùng chunks và bộ câu hỏi được phép; ghi tokenizer, phiên bản thư viện, biến thể IDF, `k1`, `b` và định nghĩa độ dài.
2. Compare BM25, TF-IDF, dense, and hybrid on dev using the same gold and original queries. / So sánh các phương pháp trên dev với cùng gold và query gốc.
3. Report Hit@1, Evidence Hit@3, context evidence, answers, citations, abstention, time, and cost; inspect failures. / Báo cáo metric, câu trả lời, citation, từ chối, thời gian, chi phí và phân tích lỗi.
4. Choose on dev, freeze, then evaluate on an independent test; if test informs changes, use a fresh test. / Chọn trên dev, chốt rồi đánh giá trên test độc lập; nếu dùng test để điều chỉnh thì tạo test mới.

## 8. Dense search and MiniLM / Dense search và MiniLM

**English:** `all-MiniLM-L6-v2` is an English sentence-embedding model. The project loads a pretrained 6-layer, 384-dimensional model on CPU. Text passes through a tokenizer, Transformer encoder, masked mean pooling, and normalization. The project did not train or fine-tune this model.

**Tiếng Việt:** `all-MiniLM-L6-v2` là mô hình embedding câu tiếng Anh. Dự án tải mô hình pretrained 6 lớp, 384 chiều trên CPU. Văn bản đi qua tokenizer, Transformer encoder, masked mean pooling và chuẩn hóa. Dự án không tự train hoặc fine-tune mô hình này.

```text
text → token IDs + attention mask → 6 Transformer layers
     → masked mean pooling → L2-normalized vector of length 384
```

The author's model card describes contrastive fine-tuning on a large text-pair data pool: paired texts are encouraged to score higher than other candidates in a batch. It reports 100,000 steps, batch size 1,024 and training sequence length 128. The data pool exceeding one billion pairs does not establish that every pair was processed. / Model card mô tả contrastive fine-tuning trên tập lớn các cặp văn bản: cặp đúng được khuyến khích có điểm cao hơn các ứng viên khác trong batch. Tác giả ghi 100.000 bước, batch 1.024, độ dài chuỗi train 128; quy mô dữ liệu hơn một tỷ cặp không có nghĩa mọi cặp đều đã được xử lý. [Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

Generic contrastive objective / Hàm mục tiêu đối chiếu tổng quát:

```text
P(p_i | q_i) = exp(sim(q_i,p_i)/τ) / Σ_j exp(sim(q_i,p_j)/τ)
loss_i = -log P(p_i | q_i)
```

`τ` is a temperature parameter in this conceptual form; no particular value is asserted for this checkpoint. / `τ` là nhiệt độ trong công thức minh họa; không khẳng định giá trị cụ thể của checkpoint.

The checkpoint's Sentence Transformers pipeline has a 256-token maximum. Its default behavior may truncate, but this project's `MyEmbedder._check_lengths()` raises an error before encoding an over-limit input. `batch_size=16` in document encoding is an inference setting, not the model authors' training batch. / Pipeline có giới hạn 256 token. Mặc định có thể cắt, nhưng `MyEmbedder._check_lengths()` của dự án báo lỗi trước khi mã hóa đầu vào quá dài. `batch_size=16` là cấu hình inference, không phải batch khi tác giả train.

### 8.1. Cosine similarity / Độ tương đồng cosine

```text
cos(q,d) = (q · d) / (||q|| ||d||)
q=[1,2], d=[2,1] → dot=4, ||q||=||d||=√5 → cosine=0.8
```

This is a toy two-dimensional calculation; the real model outputs 384 dimensions. A score of 0.8 is not an 80% probability of a correct answer. / Đây là ví dụ hai chiều; mô hình thật tạo 384 chiều. Điểm 0,8 không phải xác suất trả lời đúng 80%.

### 8.2. Training versus inference / Huấn luyện và suy luận

**Training / Huấn luyện:** learn or update model weights using data, a loss, an optimizer, and validation. **Inference / Suy luận:** keep weights fixed and encode new text. / Training cập nhật trọng số bằng dữ liệu, loss và optimizer; inference giữ trọng số và mã hóa văn bản mới.

If fine-tuning later, prepare permitted train pairs, keep dev/test independent, record checkpoint and settings, then re-embed all document chunks before comparing queries using the new model. Matching dimensions alone does not guarantee compatible vector spaces. / Nếu fine-tune sau này, chuẩn bị cặp train được phép, giữ dev/test độc lập, ghi checkpoint và cấu hình, rồi tạo lại embedding cho toàn bộ chunks. Cùng số chiều không bảo đảm hai không gian vector tương thích.

## 9. PostgreSQL and pgvector / PostgreSQL và pgvector

PostgreSQL is the database; pgvector is an extension providing vector types and distance operators. It does not create embeddings or generate answers. / PostgreSQL là hệ quản trị cơ sở dữ liệu; pgvector là extension bổ sung kiểu vector và phép tính khoảng cách. Nó không tự tạo embedding hoặc sinh câu trả lời.

The Day 6 `day6_chunks` table stores `strategy`, `chunk_id`, `document_id`, `source`, physical `page`, `content`, JSONB `metadata`, and `embedding vector(384)`. Its primary key is `(strategy, chunk_id)`. / Bảng `day6_chunks` lưu strategy, ID, nguồn, trang PDF, văn bản, metadata JSONB và vector 384 chiều. Khóa chính là `(strategy, chunk_id)`.

Conceptual SQL / SQL minh họa (`:query_vector` is a placeholder / là placeholder):

```sql
SELECT chunk_id, source, page, content,
       1 - (embedding <=> :query_vector) AS score
FROM day6_chunks
WHERE strategy = 'history_B'
ORDER BY embedding <=> :query_vector, chunk_id
LIMIT 3;
```

`<=>` is cosine distance; the project computes `1-distance` for cosine similarity. The recorded project uses exact cosine search and no HNSW or IVFFlat approximate vector index. Exact vector ranking does not guarantee semantic relevance or factual correctness. / `<=>` là cosine distance; dự án tính `1-distance` để lấy cosine similarity. Dự án dùng exact search, không có HNSW/IVFFlat vector index trong thí nghiệm được ghi nhận. Xếp hạng vector chính xác không bảo đảm nội dung đúng. [pgvector documentation](https://github.com/pgvector/pgvector/blob/v0.8.7/README.md).

## 10. Docker environment / Môi trường Docker

| Term | English | Tiếng Việt |
|---|---|---|
| Image | Template for a container | Mẫu để tạo container. |
| Container | Running instance | Phiên bản đang chạy. |
| Volume | Persistent data storage | Nơi lưu dữ liệu tồn tại ngoài vòng đời container. |
| Compose | YAML-based service configuration | Công cụ mô tả dịch vụ bằng YAML. |

Day 6 uses image `pgvector/pgvector:0.8.7-pg16`, named volume `pg_data`, and port mapping `127.0.0.1:55433:5432`: Windows Python connects to host port 55433, mapped to PostgreSQL port 5432 inside the container. `init.sql` enables the vector extension during initialization. `pg_isready` checks service readiness; a healthy container alone does not prove that chunks or the embedding model are correct.

Day 6 dùng image `pgvector/pgvector:0.8.7-pg16`, volume `pg_data` và ánh xạ cổng `127.0.0.1:55433:5432`: Python trên Windows kết nối cổng host 55433, được ánh xạ vào cổng PostgreSQL 5432 trong container. `init.sql` bật extension khi khởi tạo. `pg_isready` kiểm tra mức sẵn sàng của dịch vụ; trạng thái healthy không tự chứng minh chunks hay embedding model đúng.

In Day 6 `starter`, read-only checks and service startup are / Trong thư mục Day 6 `starter`, kiểm tra và khởi động dịch vụ:

```powershell
docker version
docker compose -p day6_student_starter ps -a
docker compose -p day6_student_starter up -d --wait
.\.venv\Scripts\python.exe scripts\check_setup.py
docker compose -p day6_student_starter exec -T postgres psql -U day6 -d day6_lab -c "SELECT strategy, COUNT(*) AS chunks FROM day6_chunks GROUP BY strategy ORDER BY strategy;"
```

Do not publish `.env` or API keys. A volume is not a backup; `docker compose down -v` removes declared volumes and can delete database data. Ingestion also replaces a database snapshot and writes statistics. / Không công khai `.env` hoặc API key. Volume không phải bản sao lưu; `docker compose down -v` xóa volume khai báo và có thể xóa dữ liệu. Ingestion cũng thay snapshot database và ghi thống kê. [Docker Compose volumes](https://docs.docker.com/compose/gettingstarted/).

## 11. Hybrid and reranking / Hybrid và xếp hạng lại

### 11.1. Hybrid RRF / Kết hợp bằng RRF

Hybrid combines retrieval signals. This project runs dense and TF-IDF, then applies reciprocal rank fusion / Hybrid kết hợp các tín hiệu retrieval. Dự án chạy dense và TF-IDF rồi áp dụng RRF:

```text
RRF(chunk) = Σ over rankings [1 / (k + rank(chunk))]
```

Ranks start at 1; a missing chunk contributes zero for that list. With `k=60`, ranks 3 and 2 contribute `1/63 + 1/62 ≈ 0.032002`. Combining rankings avoids directly adding incompatible raw scores, but agreement between retrievers can boost the same wrong passage. / Rank bắt đầu từ 1; chunk vắng mặt đóng góp 0. Với `k=60`, rank 3 và 2 cho `1/63+1/62≈0.032002`. Kết hợp rank tránh cộng trực tiếp các thang điểm khác nhau, nhưng hai retriever có thể cùng đẩy một đoạn sai lên cao. [RRF documentation](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion).

### 11.2. Reranking / Xếp hạng lại

A cross-encoder reranker can score each `(query, candidate chunk)` pair after first-stage retrieval, then reorder candidates. It can model query–document interactions but adds computation and cannot recover evidence absent from the candidate set. The project has **not implemented or tested** a cross-encoder reranker. / Cross-encoder reranker có thể chấm từng cặp `(query, chunk)` sau retrieval rồi sắp xếp lại. Nó có thể mô hình hóa tương tác query–document nhưng tốn thêm tính toán và không thể lấy lại bằng chứng không nằm trong tập candidate. Dự án **chưa triển khai hay kiểm thử** cross-encoder reranker. [Sentence Transformers Retrieve & Re-Rank](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html).

## 12. Evaluation metrics / Các chỉ số đánh giá

For answerable questions / Đối với câu có đáp án:

```text
Hit@1 = answerable questions with valid evidence at rank 1 / answerable questions
Evidence Hit@3 = answerable questions with valid evidence in top 3 / answerable questions
Context Evidence Rate = answerable questions with enough evidence in final context / answerable questions
```

Report `n/N`, not only a percentage; specify how much evidence counts as enough. Insufficient-evidence cases do not enter retrieval-metric denominators. / Báo `n/N`, không chỉ phần trăm; định nghĩa evidence thế nào là đủ. Câu thiếu evidence không nằm trong mẫu số retrieval metrics.

Agent evaluation includes grounded answer grades 0/1/2, citation support, answer citation coverage, tool-use distribution, correct abstention, false abstention, time, cost, and errors. A valid chunk ID is not proof the chunk supports the claim. / Đánh giá agent gồm điểm grounded answer 0/1/2, citation support, tỷ lệ câu có citation, phân bố tool use, từ chối đúng/sai, thời gian, chi phí và lỗi. ID hợp lệ không chứng minh chunk hỗ trợ phát biểu.

## 13. Actual experiments and outcomes / Thí nghiệm và kết quả thực tế

The v2 benchmark has 20 answerable + 2 insufficient-evidence dev cases and a new test of 5 answerable + 2 insufficient-evidence cases. The previous Day 6 test questions were moved into Day 7 dev because they had already been inspected. / Benchmark v2 có 20 câu có đáp án + 2 câu thiếu evidence cho dev và test mới gồm 5 + 2 câu. Các câu test Day 6 cũ được chuyển sang dev vì đã xem kết quả trước đó.

| Dev configuration / Cấu hình dev | Fully grounded answers / 20 | Errors / Lỗi |
|---|---:|---:|
| Dense top-3, 800 characters | 12/20 | 0 |
| TF-IDF top-3, 800 characters | 13/20 | 0 |
| Hybrid top-3, 800 characters | 13/20 | 0 |
| Hybrid top-6, 800 characters | 12/20 | 0 |
| Hybrid top-6, 1,600 characters | 13/20 | 0 |

TF-IDF was selected before test using the recorded criteria: grounded answers, errors, then prior retrieval-only timing as a tie-break. This was a single timing run and does not establish general superiority. See [selection_v2.json](results/selection_v2.json). / TF-IDF được chọn trước test theo số câu đủ evidence, số lỗi, rồi thời gian retrieval trước đó để phá hòa. Thời gian chỉ đo một lần, không chứng minh ưu thế tổng quát.

| Test outcome / Kết quả test | Dense baseline | Selected TF-IDF |
|---|---:|---:|
| Fully supported answer / 5 answerable | 2/5 | 4/5 |
| Errors / 7 cases | 1 timeout | 0 |
| Final system abstentions / 2 insufficient-evidence | 2/2 | 2/2 |
| Supported citations / all citations | 2/3 | 4/6 |

Both configurations' insufficient-evidence cases ended at the search limit, so final system abstention does not prove that the model explicitly chose to abstain. Dense's timed-out case was retried separately; the retry did not replace the primary result. / Cả hai cấu hình kết thúc các câu thiếu evidence vì search limit; đầu ra hệ thống từ chối không chứng minh model tự chọn từ chối. Case dense timeout được chạy lại riêng nhưng không thay kết quả chính.

## 14. Problems encountered and relevant theory / Vấn đề đã gặp và lý thuyết liên quan

### 14.1. JSON output and trace preservation / JSON và lưu trace

The earlier model output sometimes could not be parsed as JSON. The exact raw output was not retained, so the specific cause is unknown. The controller now requests `json_object` and still validates the response; timeout or invalid output remains possible. / Trước đây một số output không parse được JSON. Do không lưu raw output cũ nên chưa xác định được nguyên nhân chính xác. Controller hiện yêu cầu `json_object` và vẫn kiểm tra kết quả; timeout hoặc output không hợp lệ vẫn có thể xảy ra.

Previously, an exception caused the runner to record empty events, even if searches had occurred. The revised loop attaches completed events and error details to the exception. If a timeout occurs before the first search, there is no context to recover. / Trước đây exception làm mất events dù có thể đã search. Vòng lặp sửa lại giữ events đã hoàn thành và chi tiết lỗi. Nếu timeout trước search đầu tiên thì không có context để khôi phục. See [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/).

### 14.2. Chunk boundaries and incomplete gold / Ranh giới chunk và gold thiếu điều kiện

V2T05's evidence spans two adjacent chunks on physical PDF page 158: one contains the name and 1696, the next contains the central-administration role. Its initial automatic gold only captured the first part. The automatic retrieval score and the manual complete-evidence review are therefore reported separately in [benchmark_v2_evidence_audit.json](data/benchmark_v2_evidence_audit.json). / Evidence V2T05 nằm trên hai chunks liền nhau ở trang PDF 158: một chunk có tên và năm 1696, chunk sau có vai trò hành chính trung ương. Gold tự động ban đầu chỉ ghi phần đầu; vì vậy điểm tự động và đánh giá evidence đầy đủ bằng tay được báo riêng.

The finding was recorded after test; it was not used to alter the frozen configuration and rerun the same test as an independent result. / Phát hiện được ghi sau test; không dùng để sửa cấu hình và chạy lại cùng test rồi tuyên bố độc lập.

### 14.3. Search limits and abstention / Giới hạn tìm kiếm và từ chối

The two-search limit prevents indefinite calls but can stop a run even when evidence is already in context. A system-generated refusal after `search_limit` differs from an explicit model statement that evidence is missing. Both must remain visible in the trace. / Giới hạn hai lần search tránh gọi vô hạn nhưng có thể dừng khi evidence đã có trong context. Từ chối do hệ thống tạo sau `search_limit` khác với model chủ động nói thiếu evidence; trace phải phân biệt hai trường hợp.

### 14.4. OCR and encoding / OCR và mã hóa

OCR errors arise when scanned text is misread; verify the original scan. Garbled `?` characters in old review JSON arose during text encoding, not necessarily OCR. Legible notes were rebuilt from preserved labels and traces; original corrupted files remain in `results/archive_corrupt_reviews/`. / Lỗi OCR xảy ra khi nhận dạng sai từ scan; cần đối chiếu bản gốc. Dấu `?` trong JSON review cũ là lỗi mã hóa, không nhất thiết là lỗi OCR. Ghi chú đọc được đã được viết lại từ nhãn và trace; bản lỗi được giữ trong `results/archive_corrupt_reviews/`.

### 14.5. Limitations, metrics and costs / Giới hạn, mẫu số và chi phí

The agent metrics script excludes failed cases from its grounded-answer mean and reports errors separately. Thus Dense's successful-case mean is not a score over all five answerable questions; the table above also counts the timeout as unsuccessful. The test is small, the same project participants prepared and reviewed cases, and insufficient-evidence questions are mostly temporal. / Script loại các case lỗi khỏi trung bình grounded answer và báo lỗi riêng. Do đó trung bình của Dense không phải điểm trên cả năm câu; bảng trên cũng tính timeout là không thành công. Test nhỏ, người tạo và review thuộc cùng dự án, câu thiếu evidence chủ yếu dựa trên thời gian.

Provider-returned v2 dev/test usage was 167,043 tokens and approximately USD 0.030204934; the separate retry was 1,257 tokens and approximately USD 0.000244902. Including earlier recorded calls, the recorded total was 268,278 tokens and approximately USD 0.054688696. A timed-out call without returned usage may not be fully represented. / Usage provider trả về cho dev/test v2 là 167.043 tokens, khoảng 0,030204934 USD; retry riêng 1.257 tokens, khoảng 0,000244902 USD. Bao gồm các lần cũ đã ghi: 268.278 tokens, khoảng 0,054688696 USD. Timeout không trả usage có thể chưa được tính đủ.

## 15. Full processing route / Quy trình hoàn chỉnh

1. **Verify Day 6 / Kiểm tra Day 6:** start Docker service, check PostgreSQL/pgvector, model revision, collection and real retrieval. Preserve old ingestion artifacts before rebuilding. / Khởi động dịch vụ, kiểm tra DB, model, collection và retrieval thật; giữ artifacts cũ trước khi rebuild.
2. **Export B chunks / Xuất B chunks:** run `src/export_day6_chunks.py`; verify IDs and content against the database. / Chạy script export và đối chiếu ID, nội dung với database.
3. **Prepare benchmark / Chuẩn bị benchmark:** record answerable and insufficient cases, evidence, source, splits and scoring rules. Keep gold out of the agent. / Ghi câu hỏi, evidence, nguồn, split và cách chấm; không đưa gold vào agent.
4. **Build and test retrieval / Xây dựng và kiểm tra retrieval:** use dense, TF-IDF and hybrid on the same corpus. / Dùng ba phương pháp trên cùng corpus.
5. **Run the agent / Chạy agent:** connect a real model, record actions, context, answer, citation, timings, costs and errors. / Kết nối model thật, lưu action, context, câu trả lời, citation, thời gian, chi phí và lỗi.
6. **Evaluate dev / Đánh giá dev:** compare methods and at least two improvements; inspect at least two errors; freeze the selection. / So sánh phương pháp, ít nhất hai cải tiến, phân tích ít nhất hai lỗi và chốt cấu hình.
7. **Evaluate fresh test / Đánh giá test mới:** run baseline and selected configuration, manually inspect evidence and citation, disclose errors. / Chạy baseline và cấu hình chọn; kiểm tra bằng tay evidence, citation và báo lỗi.
8. **Report and submit / Báo cáo và nộp:** complete the individual report, provide reproducibility and permitted data, check secrets, then submit the personal repository link per instructor. / Hoàn thiện báo cáo, hướng dẫn tái lập và dữ liệu được phép, kiểm tra secret, rồi nộp link repo theo giảng viên.

## 16. Optional advanced challenge / Thử thách nâng cao tùy chọn

The bonus requires one real document of at least 100 pages with useful text, tables, images and charts; process useful content across the document, record page/region evidence, create a separate benchmark, and score at least 90% on all test cases without rounding up. The current 92-page text corpus does not demonstrate these requirements. / Bonus yêu cầu một tài liệu thực tế tối thiểu 100 trang có text, bảng, ảnh và biểu đồ hữu ích; xử lý nội dung, giữ evidence theo trang/vùng, tạo benchmark riêng và đạt ít nhất 90% trên toàn bộ test, không làm tròn. Corpus text hiện tại 92 trang chưa chứng minh các yêu cầu này. See / Xem [ADVANCED.md](ADVANCED.md).

## 17. Submission and Git status / Tình trạng nộp bài và Git

The individual report is [2A202603983_LeTheAnh.md](report/individual/2A202603983_LeTheAnh.md). Original and v2 traces, reviews, frozen configurations and metrics are under `results/`. Check the report's limitations and ensure the grader can access or recreate the Day 6 database. / Báo cáo cá nhân nằm tại link trên. Trace, review, cấu hình và metric cũ/v2 nằm trong `results/`. Kiểm tra giới hạn trong báo cáo và bảo đảm người chấm có thể truy cập hoặc tái tạo database Day 6.

The user previously staged an older snapshot. Later changes need to be staged again and reviewed. No commit, push, grader-access verification, or LMS submission has been established here. Do not commit `.env`, API keys or private data. / Người dùng đã stage một snapshot cũ; các thay đổi sau đó cần stage lại và kiểm tra. Chưa xác nhận commit, push, quyền truy cập của người chấm hoặc nộp LMS. Không commit `.env`, API key hoặc dữ liệu riêng tư.

## 18. Study questions / Câu hỏi tự kiểm tra

1. **EN:** A term appears five times in one chunk and appears in three chunks total. What are TF and DF?<br>
   **VI:** Một term xuất hiện năm lần trong một chunk và có mặt trong tổng cộng ba chunks. TF và DF là bao nhiêu?
2. **EN:** Why does the current TF-IDF search return no results if all query terms are absent from its vocabulary?<br>
   **VI:** Tại sao TF-IDF hiện tại trả rỗng nếu mọi term query đều không có trong vocabulary?
3. **EN:** With `b>0`, why can BM25 adjust a long document differently from a short one with the same term frequency?<br>
   **VI:** Khi `b>0`, tại sao BM25 có thể điều chỉnh tài liệu dài khác tài liệu ngắn dù TF giống nhau?
4. **EN:** Why can a top-ranked passage still fail citation support?<br>
   **VI:** Tại sao đoạn đứng đầu vẫn có thể không hỗ trợ citation?
5. **EN:** If the embedding model changes, why is it unsafe to use the old document vectors only because the dimensions match?<br>
   **VI:** Nếu đổi embedding model, tại sao không an toàn khi giữ vector tài liệu cũ chỉ vì số chiều giống nhau?

Attempt the questions before checking the corresponding sections. Do not treat a topic as mastered until answers are reviewed. / Hãy tự trả lời trước khi xem lại các mục tương ứng. Chưa đánh dấu nắm vững cho đến khi câu trả lời được kiểm tra.

## Advanced experiment status / Tình trạng phần nâng cao

**EN:** A separate NASA 127-page report was indexed. A dev/test benchmark was prepared, a configuration selected on dev, and all 30 test questions were run. AI inspection of the original pages recorded 27/30 (90%), counting errors. This is not independent human review: one gold arithmetic error was found after the run and recorded separately, all negative cases concern future years, and index completeness remains unverified. The instructor's acceptance and bonus are not confirmed. See [advanced experiment v1](docs/ADVANCED_EXPERIMENT_V1.md).

**VI:** Một báo cáo NASA riêng gồm 127 trang đã được lập chỉ mục. Benchmark dev/test được chuẩn bị, cấu hình được chọn trên dev và toàn bộ 30 câu test đã chạy. AI đối chiếu trang gốc và ghi nhận 27/30 (90%), tính cả lỗi. Đây không phải đánh giá độc lập của con người: một lỗi số học trong gold được phát hiện sau test và ghi đính chính riêng; các câu thiếu bằng chứng đều hỏi về năm tương lai; tính đầy đủ của index chưa được xác nhận. Giảng viên chưa xác nhận kết quả hay điểm thưởng. Xem [thí nghiệm nâng cao v1](docs/ADVANCED_EXPERIMENT_V1.md).
