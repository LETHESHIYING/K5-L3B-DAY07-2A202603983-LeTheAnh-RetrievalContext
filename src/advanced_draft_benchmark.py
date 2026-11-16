"""Generate draft benchmark candidates from original PDF pages, never verified gold."""
import argparse
import base64
import json
import time
import urllib.request
from pathlib import Path

import fitz
from dotenv import dotenv_values


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf', type=Path, required=True)
    p.add_argument('--provider-env', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--split', choices=['dev', 'test'], required=True)
    p.add_argument('--avoid-draft', type=Path, help='Prior dev draft; prevent repeating its answer facts in test')
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('Output exists; use a new file.')
    key = dotenv_values(a.provider_env).get('OPENROUTER_API_KEY')
    if not key:
        raise SystemExit('Missing OpenRouter key.')
    pages = {'dev': [13, 16, 21, 31, 33, 52, 71, 96],
             'test': [14, 15, 22, 25, 27, 29, 30, 32, 38, 39, 50, 51, 53, 69, 70, 72]}[a.split]
    counts = ('15 answerable and 3 unanswerable' if a.split == 'dev' else
              '24 answerable: 6 table, 5 image_diagram, 5 chart, 4 multi_hop, 4 text; and 6 unanswerable')
    prompt = ('Create DRAFT benchmark candidates using only the following original NASA report page images. '
              f'This is the {a.split} split. Produce exactly {counts}. '
              'Each answerable question must have one group from table, image_diagram, chart, multi_hop, text; '
              'a concise question, exact answer with units and conditions, a rationale, and evidence with '
              'physical pdf_page and precise region. Multi-hop must combine at least two pages. '
              'Use informative photos or diagrams and real charts, not decorative images. '
              'Multi-hop questions must require an arithmetic calculation using different facts on two different pages, not just matching a repeated number. '
              'Do not mention page numbers, citations, or locations in question text, since that would leak gold locations to retrieval. '
              'For unanswerable questions ask about information the report is unlikely to contain; '
              'set answerable false and describe how to check absence. Do not pretend the whole report was checked. '
              'Avoid questions about values in the assets smoke-test question. '
              'Return JSON {"items":[...]}; each item has id, question, group, answerable, answer, '
              'rationale, evidence list, absence_check. Page numbers are physical PDF page numbers shown before images. '
              'These are drafts: do not claim human checking.')
    doc = fitz.open(a.pdf)
    if a.avoid_draft:
        prior = json.loads(a.avoid_draft.read_text(encoding='utf8'))
        facts = [{'question': item.get('question'), 'answer': item.get('answer')} for item in prior['items']]
        prompt += ' Do not reuse or paraphrase any of these previously used dev question/answer facts: ' + json.dumps(facts, ensure_ascii=False)
    content = [{'type':'text','text':prompt}]
    for number in pages:
        pix = doc[number - 1].get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        data = base64.b64encode(pix.tobytes('jpeg', jpg_quality=82)).decode('ascii')
        content.extend([{'type':'text','text':f'Physical PDF page {number}'},
                        {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,' + data}}])
    body = {'model':'deepseek/deepseek-v4.1-flash-1017','temperature':0,
            'reasoning':{'effort':'medium'},'response_format':{'type':'json_object'},
            'provider':{'require_parameters':True},'messages':[{'role':'user','content':content}]}
    request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
        json.dumps(body).encode(), {'Content-Type':'application/json','Authorization':'Bearer '+key})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=240) as response:
        result = json.load(response)
    draft = json.loads(result['choices'][0]['message']['content'])
    record = {'status':'unverified_draft','split':a.split,'input_pages':pages,
              'usage':result.get('usage',{}),'elapsed_seconds':time.perf_counter()-started,
              'items':draft.get('items',[])}
    for item in record['items']:
        item['original_checked'] = False
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf8') as f:
        json.dump(record,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(json.dumps({'split':a.split,'count':len(record['items']),'usage':record['usage']}))


if __name__ == '__main__':
    main()
