"""Search the advanced text and visual indexes without access to benchmark gold."""
import argparse
import json
import sys
from pathlib import Path

from dotenv import dotenv_values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--day6-starter', type=Path, required=True)
    p.add_argument('--query', required=True)
    p.add_argument('--top-k', type=int, default=5)
    p.add_argument('--text-strategy', default='advanced_nasa_fy2024_text_v1')
    p.add_argument('--visual-strategy', default='advanced_nasa_fy2024_vision_v1')
    p.add_argument('--output', type=Path, help='Optional new trace file; existing files are not overwritten')
    a = p.parse_args()
    if a.top_k < 1:
        p.error('--top-k must be positive')
    sys.path.insert(0, str(a.day6_starter.resolve()))
    from src.embeddings import MyEmbedder
    from src.store import PgVectorStore
    url = dotenv_values(a.day6_starter / '.env').get('DATABASE_URL')
    if not url:
        raise SystemExit('Day 6 DATABASE_URL is missing')
    embedder = MyEmbedder()
    store = PgVectorStore(url, embedder.dimensions)
    vec = embedder.embed_query(a.query)
    results = {}
    for name, strategy in [('text', a.text_strategy), ('visual', a.visual_strategy)]:
        results[name] = store.search(strategy, vec, top_k=a.top_k)
    result = {'query': a.query, 'results': results,
              'warning': 'Visual descriptions are unverified; inspect the original PDF page before relying on them.'}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        with a.output.open('x', encoding='utf8') as f:
            f.write(text + '\n')
    print(text)


if __name__ == '__main__':
    main()
