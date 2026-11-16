"""Save manual dev-v2 reviews; these judgments are not independent audits."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cases = {x['id']: x for x in json.loads((ROOT / 'data/benchmark_day7_v2.json').read_text(encoding='utf8'))}

for method in (sys.argv[1:] or ('dense', 'tfidf', 'hybrid')):
    traces = json.loads((ROOT / f'results/agent_dev_v2_{method}.json').read_text(encoding='utf8'))
    reviews = []
    for trace in traces:
        if trace['status'] == 'error':
            continue
        qid, case = trace['query_id'], cases[trace['query_id']]
        citations = [qid not in ('H16', 'H20')] * len(trace['citations'])
        last = trace['events'][-1] if trace['events'] else {}
        if not case['answerable']:
            reason = ('Hệ thống không đưa ra khẳng định; model nói thiếu evidence.'
                      if last.get('model_answer') == 'Insufficient evidence.'
                      else 'Hệ thống từ chối do search limit; không khẳng định model chủ động từ chối.')
            review = {'query_id': qid, 'citation_support': citations,
                      'abstention_correct': trace['status'] == 'abstain', 'reason': reason}
        else:
            bad = qid in ('H08', 'H16', 'H20')
            grade = 0 if trace['status'] == 'abstain' or bad else 2
            if trace['status'] == 'abstain': reason = 'Câu có đáp án nhưng hệ thống từ chối.'
            elif qid == 'H08': reason = 'Câu nói Plymouth, Anh; gold là Holland. Câu hỏi mơ hồ về thời điểm; giữ nhãn bảo thủ.'
            elif qid == 'H16': reason = 'Đoạn trích nói “he” nhưng không có tên John Smith, không đủ hỗ trợ chủ thể.'
            elif qid == 'H20': reason = 'Chunk bị cắt ngay sau hai tên, thiếu đoạn xác nhận vai trò.'
            else: reason = f"Đối chiếu gold ({case['expected_answer']}) và đoạn citation trong trace."
            review = {'query_id': qid, 'citation_support': citations, 'answer_grade': grade, 'reason': reason}
        reviews.append(review)
    path = ROOT / f'results/reviews_dev_v2_{method}.json'
    with path.open('x', encoding='utf8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(path.name, len(reviews))
