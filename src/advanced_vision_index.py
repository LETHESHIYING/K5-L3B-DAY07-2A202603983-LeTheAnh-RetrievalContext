"""Describe PDF page visuals with the authorized multimodal model; descriptions are unverified."""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--provider-env', type=Path, required=True)
    p.add_argument('--pymupdf-site', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--first', type=int, default=1)
    p.add_argument('--last', type=int)
    p.add_argument('--workers', type=int, default=3)
    p.add_argument('--model', default='deepseek/deepseek-v4.1-flash-1017')
    args = p.parse_args()
    if args.pymupdf_site:
        sys.path.append(str(args.pymupdf_site.resolve()))
    import fitz
    if args.pymupdf_site:
        sys.path.remove(str(args.pymupdf_site.resolve()))
    from dotenv import dotenv_values
    key = dotenv_values(args.provider_env).get('OPENROUTER_API_KEY')
    if not key:
        raise SystemExit('Missing OpenRouter key in provider environment file')
    doc = fitz.open(args.pdf)
    last = args.last or len(doc)
    if args.first < 1 or last > len(doc) or last < args.first or not 1 <= args.workers <= 5:
        raise SystemExit('Invalid page range or worker count')
    args.output.mkdir(parents=True, exist_ok=True)
    source_sha = hashlib.sha256(args.pdf.read_bytes()).hexdigest()
    def analyze(number, image):
        path = args.output / f'page_{number:04d}.json'
        if path.exists():
            return number, 'exists'
        prompt = ('Describe the informational visual content of this report page for retrieval. '
                  'Return JSON with keys summary (string), visual_items (array of objects with '
                  'type, location, description, visible_values), and uncertainties (array). '
                  'Include charts, tables, maps, diagrams, informative photos and captions. '
                  'Include visible values and units only when legible. Do not invent data. '
                  'If decorative or unreadable, say so. Page number: ' + str(number))
        data_url = 'data:image/jpeg;base64,' + base64.b64encode(image).decode('ascii')
        body = {'model': args.model, 'temperature': 0, 'response_format': {'type': 'json_object'},
                'reasoning': {'effort': 'low'},
                'provider': {'require_parameters': True},
                'messages': [{'role': 'user', 'content': [{'type': 'text', 'text': prompt},
                              {'type': 'image_url', 'image_url': {'url': data_url}}]}]}
        req = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                     json.dumps(body).encode('utf8'),
                                     {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        start = time.perf_counter()
        record = {'pdf_page': number, 'source_sha256': source_sha, 'model': args.model,
                  'status': 'error', 'verification': 'model description; must verify against original page'}
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.load(response)
            record['usage'] = result.get('usage', {})
            content = result['choices'][0]['message']['content']
            parsed = json.loads(content)
            if not isinstance(parsed, dict) or not isinstance(parsed.get('summary'), str) or not isinstance(parsed.get('visual_items'), list):
                raise ValueError('Invalid visual description schema')
            record.update(status='ok', description=parsed)
        except Exception as exc:
            record['error_type'] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError): record['http_status'] = exc.code
        record['elapsed_seconds'] = time.perf_counter() - start
        with path.open('x', encoding='utf8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
            f.write('\n')
        return number, record['status']
    pending = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for number in range(args.first, last+1):
            target = args.output / f'page_{number:04d}.json'
            if target.exists():
                continue
            pix = doc[number-1].get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
            pending.append(pool.submit(analyze, number, pix.tobytes('jpeg', jpg_quality=82)))
        for future in concurrent.futures.as_completed(pending):
            number, status = future.result()
            print(f'page {number}: {status}', flush=True)


if __name__ == '__main__':
    main()
