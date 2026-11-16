"""Prepare evidence and model answers for manual review; never generate labels."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', required=True, type=Path)
    p.add_argument('--traces', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    cases = {c['id']: c for c in json.loads(args.cases.read_text(encoding='utf-8'))}
    traces = json.loads(args.traces.read_text(encoding='utf-8'))
    rows = []
    for trace in traces:
        case = cases[trace['query_id']]
        events = [e for e in trace.get('events', []) if e.get('event') == 'search']
        context = events[-1].get('context', '') if events else ''
        rows.append({'query_id': trace['query_id'], 'question': case['question'],
                     'answerable': case['answerable'], 'expected_answer': case.get('expected_answer'),
                     'gold': case.get('gold'), 'absence_reason': case.get('absence_reason'),
                     'status': trace['status'], 'answer': trace.get('answer'),
                     'citations': trace.get('citations', []), 'context': context,
                     'answer_grade': None, 'citation_support': None,
                     'abstention_correct': None, 'review_reason': None})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'Prepared {len(rows)} cases; labels still require review.')


if __name__ == '__main__':
    main()
