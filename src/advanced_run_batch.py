"""Run a validated advanced benchmark split without sending gold to the agent."""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from advanced_validate_benchmark import validate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark', type=Path, required=True)
    p.add_argument('--split', choices=['dev', 'test'], required=True)
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--day6-starter', type=Path, required=True)
    p.add_argument('--provider-env', type=Path, required=True)
    p.add_argument('--pymupdf-site', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--top-k', type=int, default=5)
    p.add_argument('--max-pages', type=int, default=4)
    p.add_argument('--text-strategy', default='advanced_nasa_fy2024_text_v1')
    p.add_argument('--visual-strategy', default='advanced_nasa_fy2024_vision_v1')
    p.add_argument('--workers', type=int, default=2)
    p.add_argument('--frozen-config', type=Path, help='Required for test; created after dev selection')
    a = p.parse_args()
    raw = a.benchmark.read_bytes()
    benchmark = json.loads(raw)
    errors = validate(benchmark)
    if errors:
        raise SystemExit('Benchmark invalid: ' + '; '.join(errors))
    if a.output.exists():
        raise SystemExit('Output exists; use a fresh directory to preserve evidence.')
    if not 1 <= a.workers <= 4:
        p.error('workers must be between 1 and 4')
    digest = hashlib.sha256(raw).hexdigest()
    if a.split == 'test':
        if not a.frozen_config:
            raise SystemExit('Test requires a dev-selected frozen configuration.')
        frozen = json.loads(a.frozen_config.read_text(encoding='utf8'))
        if (frozen.get('benchmark_sha256') != digest or frozen.get('top_k') != a.top_k
            or frozen.get('max_pages') != a.max_pages or frozen.get('text_strategy') != a.text_strategy
            or frozen.get('visual_strategy') != a.visual_strategy):
            raise SystemExit('Frozen configuration or benchmark hash does not match the test run.')
    a.output.mkdir(parents=True)
    items = benchmark[a.split]
    started = time.perf_counter()
    def run(item):
        ident = item['id']
        if not ident.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Unsafe question ID')
        path = a.output / (ident + '.json')
        args = [sys.executable, str(Path(__file__).with_name('advanced_agent.py')),
                '--pdf', str(a.pdf), '--day6-starter', str(a.day6_starter), '--provider-env', str(a.provider_env),
                '--question', item['question'], '--output', str(path), '--top-k', str(a.top_k), '--max-pages', str(a.max_pages),
                '--text-strategy', a.text_strategy, '--visual-strategy', a.visual_strategy]
        if a.pymupdf_site:
            args.extend(['--pymupdf-site', str(a.pymupdf_site)])
        try:
            process = subprocess.run(args, capture_output=True, text=True, timeout=240)
            status = 'completed' if path.exists() else 'runner_error'
            result = {'id': ident, 'status': status, 'exit_code': process.returncode}
        except subprocess.TimeoutExpired:
            result = {'id': ident, 'status': 'runner_timeout'}
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        results = list(pool.map(run, items))
    summary = {'split': a.split, 'benchmark_sha256': digest, 'top_k': a.top_k, 'max_pages': a.max_pages,
               'text_strategy': a.text_strategy, 'visual_strategy': a.visual_strategy,
               'elapsed_seconds': time.perf_counter()-started, 'runs': results,
               'warning': 'Run status is not a pass score. Answers require original-source review.'}
    (a.output / 'run_summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'questions':len(results),'runner_errors':sum(r['status']!='completed' for r in results)}))


if __name__ == '__main__':
    main()
