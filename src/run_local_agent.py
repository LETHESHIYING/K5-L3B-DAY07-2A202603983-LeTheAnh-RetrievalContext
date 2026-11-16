"""Run the Day 7 starter agent against an available local model server."""
import argparse
import json
import sys
import time
import urllib.error
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'starter'))
from agentic import run_agent
from local_agent import AgentRetriever, LocalController
from retrievers import RetrievalEngine


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--day6-starter', required=True, type=Path)
    p.add_argument('--chunks', required=True, type=Path)
    p.add_argument('--cases', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--base-url', required=True, help='Local or OpenRouter OpenAI-compatible URL ending in /v1')
    p.add_argument('--provider-env', type=Path, help='Private OpenRouter environment file')
    p.add_argument('--model', required=True)
    p.add_argument('--method', choices=('dense', 'tfidf', 'hybrid'), required=True)
    p.add_argument('--split', choices=('dev', 'test'), required=True)
    p.add_argument('--top-k', type=int, default=3)
    p.add_argument('--candidate-depth', type=int, default=10)
    p.add_argument('--budget', type=int, default=800)
    p.add_argument('--max-searches', type=int, default=4)
    args = p.parse_args()
    host = urlparse(args.base_url).hostname
    if host not in ('localhost', '127.0.0.1', '::1', 'openrouter.ai'):
        raise SystemExit('Only local and OpenRouter model endpoints are supported.')
    if host == 'openrouter.ai' and (urlparse(args.base_url).scheme != 'https' or not args.provider_env):
        raise SystemExit('OpenRouter requires HTTPS and --provider-env.')
    if args.output.exists():
        raise SystemExit('Output exists; choose a new path.')
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
    cases = [c for c in json.loads(args.cases.read_text(encoding='utf-8')) if c['split'] == args.split]
    if not cases:
        raise SystemExit('No cases for selected split')
    model = MyEmbedder()
    engine = RetrievalEngine(chunks, model, PgVectorStore(url, model.dimensions))
    api_key = dotenv_values(args.provider_env).get('OPENROUTER_API_KEY') if args.provider_env else None
    if host == 'openrouter.ai' and not api_key:
        raise SystemExit('OpenRouter key missing from provider environment file.')
    controller = LocalController(args.base_url, args.model, api_key=api_key)
    retriever = AgentRetriever(engine, args.method, args.candidate_depth)
    traces = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f:
        f.write('[]\n')
    for case in cases:
        start = time.perf_counter()
        usage_start = len(controller.usage)
        try:
            result = run_agent(case['question'], controller, retriever, top_k=args.top_k,
                               budget=args.budget, max_searches=args.max_searches)
        except Exception as exc:
            result = {'status': 'error', 'error_type': type(exc).__name__,
                      'events': getattr(exc, 'agent_events', []), 'answer': '', 'citations': []}
            if isinstance(exc, urllib.error.HTTPError):
                result['http_status'] = exc.code
            if isinstance(exc, ValueError):
                result['error_detail'] = str(exc)
        result.update(query_id=case['id'], question=case['question'], elapsed_seconds=time.perf_counter()-start,
                      model=args.model, method=args.method, split=args.split, top_k=args.top_k,
                      budget_chars=args.budget, max_searches=args.max_searches,
                      model_usage=controller.usage[usage_start:])
        traces.append(result)
        args.output.write_text(json.dumps(traces, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(case['id'], result['status'], flush=True)


if __name__ == '__main__':
    main()
