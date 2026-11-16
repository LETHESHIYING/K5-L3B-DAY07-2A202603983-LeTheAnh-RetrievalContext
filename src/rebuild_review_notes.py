"""Rebuild legible notes from preserved labels and traces, without changing labels."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = {c['id']: c for c in json.loads((ROOT / 'data/benchmark_day7.json').read_text(encoding='utf8'))}
    dest = ROOT / 'results/repaired_reviews'
    dest.mkdir(parents=True, exist_ok=True)
    for split, methods in (('dev', ('dense', 'tfidf', 'hybrid')), ('test', ('dense', 'tfidf'))):
        for method in methods:
            traces = {t['query_id']: t for t in json.loads((ROOT / f'results/agent_{split}_{method}.json').read_text(encoding='utf8'))}
            labels = json.loads((ROOT / f'results/reviews_{split}_{method}.json').read_text(encoding='utf8'))
            for label in labels:
                qid = label['query_id']
                trace, case = traces[qid], cases[qid]
                if not case['answerable']:
                    ending = trace.get('events', [])[-1].get('event', 'unknown') if trace.get('events') else 'unknown'
                    label['reason'] = (f"Câu hỏi về sự kiện sau năm xuất bản 1917; đầu ra hệ thống là "
                                       f"{trace['status']}. Sự kiện kết thúc: {ending}; không suy ra model đã chủ động từ chối.")
                elif trace['status'] == 'abstain':
                    ending = trace.get('events', [])[-1].get('event', 'unknown') if trace.get('events') else 'unknown'
                    label['reason'] = f"Từ chối câu có đáp án ({case['expected_answer']}); sự kiện kết thúc: {ending}."
                elif qid == 'H08':
                    label['reason'] = 'Câu trả lời Plymouth ở Anh khác gold Holland; câu hỏi có thể mơ hồ về thời điểm, cần người học xem lại.'
                elif qid == 'H16':
                    label['reason'] = 'Citation nói người đó lấy và trồng ngô nhưng chunk không xác định tên John Smith; không đủ hỗ trợ chủ thể.'
                elif qid == 'H20':
                    label['reason'] = 'Chunk citation bị cắt sau tên và chưa thể hiện đầy đủ vai trò của hai người.'
                else:
                    label['reason'] = f"Giữ nhãn đã chấm: đáp án so với gold ({case['expected_answer']}); citation: {', '.join(trace['citations'])}."
                label['review_provenance'] = 'Diễn đạt lại từ nhãn cũ và trace còn lưu; không phải đánh giá độc lập mới.'
            output = dest / f'reviews_{split}_{method}.json'
            if output.exists():
                raise FileExistsError(output)
            output.write_text(json.dumps(labels, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
            print(output.relative_to(ROOT), len(labels))
    for name in ('context_reviews_test', 'agent_context_reviews_test'):
        data = json.loads((ROOT / f'results/{name}.json').read_text(encoding='utf8'))
        for row in data:
            if row['context_grade'] is None:
                row['reason'] = 'Lượt chạy lỗi; context trung gian không được lưu nên không thể chấm.'
            elif row['context_grade'] == 0:
                row['reason'] = 'Context không chứa đoạn evidence cần thiết theo gold.'
            else:
                row['reason'] = 'Context chứa đoạn evidence đã xác định cho câu hỏi; xem trace và trang nguồn.'
            row['review_provenance'] = 'Giữ nguyên điểm đã chấm, diễn đạt lại ghi chú.'
        output = dest / f'{name}.json'
        if output.exists(): raise FileExistsError(output)
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__':
    main()
