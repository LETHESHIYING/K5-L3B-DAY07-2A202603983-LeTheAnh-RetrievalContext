"""Extract every page of the advanced PDF and build a separate pgvector collection."""
import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path

import psycopg
from dotenv import dotenv_values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--day6-starter', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--pymupdf-site', type=Path, help='Optional existing site-packages path containing PyMuPDF')
    p.add_argument('--strategy', default='advanced_nasa_fy2024_text_v1')
    args = p.parse_args()
    if args.pymupdf_site:
        sys.path.append(str(args.pymupdf_site.resolve()))
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit('Install PyMuPDF in the environment or provide --pymupdf-site') from exc
    if args.pymupdf_site:
        sys.path.remove(str(args.pymupdf_site.resolve()))
    if args.output.exists():
        raise SystemExit('Output exists: use a new directory to preserve the original run.')
    sys.path.insert(0, str(args.day6_starter.resolve()))
    from src.embeddings import MyEmbedder
    from src.models import Chunk
    from src.store import PgVectorStore
    database_url = dotenv_values(args.day6_starter / '.env').get('DATABASE_URL')
    if not database_url:
        raise SystemExit('Day 6 DATABASE_URL is missing')
    with psycopg.connect(database_url) as connection:
        existing = connection.execute('SELECT count(*) FROM day6_chunks WHERE strategy=%s', (args.strategy,)).fetchone()[0]
    if existing:
        raise SystemExit('Collection already exists; choose a new strategy to avoid replacing it.')
    pdf_sha = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    model = MyEmbedder()
    pdf = fitz.open(args.pdf)
    if len(pdf) < 120:
        raise SystemExit('The source must have at least 120 pages for this project.')
    source = 'https://www.nasa.gov/wp-content/uploads/2023/11/nasa-fy-2024-afr-1.pdf'
    chunks, pages = [], []
    for i, page in enumerate(pdf):
        text = page.get_text('text', sort=True)
        page_record = {'pdf_page': i+1, 'width_points': page.rect.width, 'height_points': page.rect.height,
                       'text_chars': len(text), 'images': len(page.get_images()), 'text': text}
        pages.append(page_record)
        start = 0
        while start < len(text):
            end = min(start + 600, len(text))
            if end < len(text):
                space = text.rfind(' ', start + 300, end)
                if space > start: end = space
            piece = text[start:end]
            while piece.strip() and len(model.model.tokenizer(piece, add_special_tokens=True, truncation=False)['input_ids']) > model.model.max_seq_length:
                end = start + max(1, (end-start)//2)
                piece = text[start:end]
            if piece.strip():
                identity = f'{pdf_sha}:{i+1}:{start}:{end}:{piece}'
                cid = hashlib.sha256(identity.encode('utf8')).hexdigest()
                chunks.append(Chunk(cid, 'nasa_fy2024_afr', source, i+1, piece,
                                    {'char_start': start, 'char_end': end, 'source_sha256': pdf_sha,
                                     'kind': 'native_pdf_text', 'pdf_page': i+1}))
            start = end
    empty = [p['pdf_page'] for p in pages if not p['text'].strip()]
    if empty:
        raise SystemExit(f'Pages without extracted text require OCR: {empty}')
    store = PgVectorStore(database_url, model.dimensions)
    started = time.perf_counter()
    vectors = model.embed_documents([c.text for c in chunks])
    store.upsert(args.strategy, chunks, vectors)
    with psycopg.connect(database_url) as connection:
        stored = connection.execute('SELECT count(*) FROM day6_chunks WHERE strategy=%s', (args.strategy,)).fetchone()[0]
    if stored != len(chunks):
        raise SystemExit('Database count does not match extracted chunks')
    args.output.mkdir(parents=True)
    (args.output / 'pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf8')
    (args.output / 'chunks.json').write_text(json.dumps([
        {'id': c.chunk_id, 'source_id': c.document_id, 'source': c.source, 'page': c.page,
         'text': c.text, 'metadata': c.metadata} for c in chunks], ensure_ascii=False, indent=2), encoding='utf8')
    manifest = {'document': 'NASA FY 2024 Agency Financial Report', 'source_url': source, 'sha256': pdf_sha,
                'physical_pages': len(pdf), 'pages_extracted': len(pages), 'blank_text_pages': empty,
                'chunk_count': len(chunks), 'strategy': args.strategy, 'model': model.model_name,
                'model_revision': model.revision, 'embedding_dimensions': model.dimensions,
                'extraction': 'PyMuPDF native text sorted by page, max 600 chars and model token limit',
                'visual_handling': 'NOT YET VERIFIED: native PDF text extraction alone is not a visual index',
                'elapsed_embedding_and_store_seconds': time.perf_counter()-started,
                'pymupdf_version': importlib.metadata.version('PyMuPDF')}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
