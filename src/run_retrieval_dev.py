"""Run a retrieval-only development comparison on the documented Day 6 cases."""
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


def normalized(text):
    return ' '.join(text.split())


def supports(chunk, case):
    return (chunk['source_id'] == case['gold_source_id'] and chunk['page'] == case['gold_page']
            and normalized(case['evidence_quote']) in normalized(chunk['text']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--day6-starter', required=True, type=Path)
    p.add_argument('--questions', required=True, type=Path)
    p.add_argument('--chunks', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit('Output exists; select a new directory')
    sys.path.insert(0, str(args.day6_starter.resolve()))
    from dotenv import dotenv_values
    from src.embeddings import MyEmbedder
    from src.store import PgVectorStore
    import psycopg
    url = dotenv_values(args.day6_starter / '.env').get('DATABASE_URL')
    if not url:
        raise SystemExit('Missing Day 6 DATABASE_URL')
    chunks = json.loads(args.chunks.read_text(encoding='utf-8'))
    with psycopg.connect(url) as conn:
        rows = conn.execute('SELECT chunk_id, document_id, source, page, content, metadata '
                            'FROM day6_chunks WHERE strategy=%s ORDER BY chunk_id', ('history_B',)).fetchall()
    keys = ('id', 'source_id', 'source', 'page', 'text', 'metadata')
    if [dict(zip(keys, row)) for row in rows] != sorted(chunks, key=lambda c: c['id']):
        raise SystemExit('Export differs from database')
    cases = json.loads(args.questions.read_text(encoding='utf-8'))
    model = MyEmbedder()
    engine = RetrievalEngine(chunks, model, PgVectorStore(url, model.dimensions))
    # Old Day 6 test is development only: it has already been inspected.
    configs = [dict(name='dense', method='dense', top_k=3, candidate_depth=10, budget=800),
               dict(name='tfidf', method='tfidf', top_k=3, candidate_depth=10, budget=800),
               dict(name='hybrid', method='hybrid', top_k=3, candidate_depth=10, budget=800),
               dict(name='hybrid_top6', method='hybrid', top_k=6, candidate_depth=10, budget=800),
               dict(name='hybrid_budget1600', method='hybrid', top_k=6, candidate_depth=10, budget=1600)]
    traces, summaries = [], []
    for cfg in configs:
        group = []
        for case in cases:
            start = time.perf_counter()
            results = engine.search(case['question'], method=cfg['method'], top_k=cfg['top_k'],
                                    candidate_depth=cfg['candidate_depth'])
            context, ids = pack_context(results, budget=cfg['budget'])
            trace = {'query_id': case['id'], 'question': case['question'], 'source_split': case['split'],
                     'split': 'dev', 'config': cfg['name'], 'filter': {}, 'results': results,
                     'context': context, 'context_ids': ids, 'elapsed_ms': (time.perf_counter()-start)*1000,
                     'hit1': bool(results and supports(results[0], case)),
                     'hit3': any(supports(c, case) for c in results[:3]),
                     'context_evidence': any(c['id'] in ids and supports(c, case) for c in results)}
            traces.append(trace)
            group.append(trace)
        summaries.append({'config': cfg, 'n': len(group), 'hit1': sum(x['hit1'] for x in group),
                          'hit3': sum(x['hit3'] for x in group),
                          'context_evidence': sum(x['context_evidence'] for x in group),
                          'total_query_seconds': sum(x['elapsed_ms'] for x in group)/1000})
    args.output.mkdir(parents=True)
    (args.output / 'traces.json').write_text(json.dumps(traces, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.output / 'summary.json').write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
