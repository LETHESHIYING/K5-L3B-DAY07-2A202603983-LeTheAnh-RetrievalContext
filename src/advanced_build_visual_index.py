"""Build a separate, traceable vector index of unverified page descriptions."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import psycopg
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vision-dir', type=Path, required=True)
    parser.add_argument('--day6-starter', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--strategy', default='advanced_nasa_fy2024_vision_v1')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Output exists; preserve the previous run and select a new output path.')
    records = [json.loads(p.read_text(encoding='utf8')) for p in sorted(args.vision_dir.glob('page_*.json'))]
    pages = {r['pdf_page']: r for r in records}
    missing = sorted(set(range(1, 128)) - pages.keys())
    failed = sorted(n for n, r in pages.items() if r.get('status') != 'ok')
    if len(records) != 127 or missing or failed:
        raise SystemExit(f'Expected 127 successful, unique page records; missing={missing}, failed={failed}')
    hashes = {r['source_sha256'] for r in records}
    if len(hashes) != 1:
        raise SystemExit('Visual records refer to different source files.')
    sys.path.insert(0, str(args.day6_starter.resolve()))
    from src.embeddings import MyEmbedder
    from src.models import Chunk
    from src.store import PgVectorStore
    url = dotenv_values(args.day6_starter / '.env').get('DATABASE_URL')
    if not url:
        raise SystemExit('Day 6 DATABASE_URL is missing')
    with psycopg.connect(url) as conn:
        if conn.execute('SELECT count(*) FROM day6_chunks WHERE strategy=%s', (args.strategy,)).fetchone()[0]:
            raise SystemExit('Strategy already exists; choose a new strategy to preserve it.')
    model = MyEmbedder()
    source = 'https://www.nasa.gov/wp-content/uploads/2023/11/nasa-fy-2024-afr-1.pdf'
    chunks = []
    for r in records:
        page = r['pdf_page']
        d = r['description']
        items = [{'type': 'page summary', 'location': 'whole page', 'description': d['summary']}]
        items.extend(d.get('visual_items', []))
        for item_no, item in enumerate(items):
            text = json.dumps(item, ensure_ascii=False)
            offset = 0
            while offset < len(text):
                end = min(offset + 550, len(text))
                piece = text[offset:end]
                while len(model.model.tokenizer(piece, add_special_tokens=True, truncation=False)['input_ids']) > model.model.max_seq_length:
                    end = offset + max(1, (end - offset) // 2)
                    piece = text[offset:end]
                cid = hashlib.sha256(f"{r['source_sha256']}:{page}:{item_no}:{offset}:{piece}".encode()).hexdigest()
                chunks.append(Chunk(cid, 'nasa_fy2024_afr', source, page, piece,
                                    {'kind': 'unverified_model_visual_description', 'pdf_page': page,
                                     'location': str(item.get('location', 'whole page')),
                                     'source_sha256': r['source_sha256'], 'item': item_no, 'offset': offset}))
                offset = end
    started = time.perf_counter()
    vectors = model.embed_documents([c.text for c in chunks])
    PgVectorStore(url, model.dimensions).upsert(args.strategy, chunks, vectors)
    with psycopg.connect(url) as conn:
        stored = conn.execute('SELECT count(*) FROM day6_chunks WHERE strategy=%s', (args.strategy,)).fetchone()[0]
    if stored != len(chunks):
        raise SystemExit('Database count does not match description chunks.')
    args.output.mkdir(parents=True)
    manifest = {'strategy': args.strategy, 'source_url': source, 'source_sha256': next(iter(hashes)),
                'pages': len(records), 'chunks': len(chunks), 'embedding_model': model.model_name,
                'embedding_revision': model.revision, 'visual_model': sorted({r['model'] for r in records}),
                'warning': 'Machine-generated descriptions may omit content or contain mistakes; verify each against the original.',
                'elapsed_seconds': time.perf_counter() - started}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
