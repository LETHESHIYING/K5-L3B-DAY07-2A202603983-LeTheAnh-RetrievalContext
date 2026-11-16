"""Evaluate frozen baseline and selected retrieval configurations on test."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'starter'))
from baseline import pack_context
from retrievers import RetrievalEngine


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--day6-starter', required=True, type=Path)
    p.add_argument('--chunks', required=True, type=Path)
    p.add_argument('--cases', required=True, type=Path)
    p.add_argument('--selection', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit('Output already exists')
    selection = json.loads(args.selection.read_text(encoding='utf8'))
    if selection.get('phase') != 'frozen_before_test':
        raise SystemExit('Configuration must be frozen before test')
    sys.path.insert(0, str(args.day6_starter.resolve()))
    from dotenv import dotenv_values
    from src.embeddings import MyEmbedder
    from src.store import PgVectorStore
    import psycopg
    url = dotenv_values(args.day6_starter / '.env').get('DATABASE_URL')
    if not url:
        raise SystemExit('Missing database configuration')
    chunks = json.loads(args.chunks.read_text(encoding='utf8'))
    with psycopg.connect(url) as conn:
        rows = conn.execute('SELECT chunk_id, document_id, source, page, content, metadata '
                            'FROM day6_chunks WHERE strategy=%s ORDER BY chunk_id', ('history_B',)).fetchall()
    keys = ('id', 'source_id', 'source', 'page', 'text', 'metadata')
    if [dict(zip(keys, row)) for row in rows] != sorted(chunks, key=lambda c: c['id']):
        raise SystemExit('Export differs from database')
    cases = [c for c in json.loads(args.cases.read_text(encoding='utf8'))
             if c['split'] == 'test' and c['answerable']]
    model = MyEmbedder()
    engine = RetrievalEngine(chunks, model, PgVectorStore(url, model.dimensions))
    traces, summary = [], []
    for label in ('baseline', 'selected'):
        cfg = selection[label]
        group = []
        for case in cases:
            start = time.perf_counter()
            ranked = engine.search(case['question'], method=cfg['method'], top_k=max(3, cfg['top_k']),
                                   candidate_depth=cfg['candidate_depth'])
            context, ids = pack_context(ranked[:cfg['top_k']], cfg['context_budget_characters'])
            def hit(c):
                return any(c['source_id'] == g['source_id'] and c['page'] == g['page'] and
                           ' '.join(g['evidence'].split()) in ' '.join(c['text'].split()) for g in case['gold'])
            trace = {'query_id': case['id'], 'config': label, 'question': case['question'],
                     'results': ranked, 'context': context, 'context_ids': ids,
                     'hit1': bool(ranked and hit(ranked[0])), 'hit3': any(hit(c) for c in ranked[:3]),
                     'context_evidence': any(c['id'] in ids and hit(c) for c in ranked),
                     'elapsed_ms': (time.perf_counter()-start)*1000}
            traces.append(trace)
            group.append(trace)
        summary.append({'config': label, 'N': len(group), 'hit1': sum(x['hit1'] for x in group),
                        'hit3': sum(x['hit3'] for x in group),
                        'context_evidence': sum(x['context_evidence'] for x in group),
                        'total_seconds': sum(x['elapsed_ms'] for x in group)/1000})
    args.output.mkdir(parents=True)
    (args.output / 'traces.json').write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding='utf8')
    (args.output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
