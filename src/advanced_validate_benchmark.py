"""Check the structural minimums for an advanced dev/test benchmark.

This cannot establish factual correctness, evidence sufficiency or independence;
each item still requires human review against the original report.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def validate(data):
    errors = []
    ids = set()
    questions = {}
    groups = {'table': 6, 'image_diagram': 5, 'chart': 5, 'multi_hop': 4, 'text': 4}
    if not isinstance(data, dict):
        return ['Top level must be an object with dev and test lists']
    for split, minimum in [('dev', (15, 3)), ('test', (24, 6))]:
        items = data.get(split)
        if not isinstance(items, list):
            errors.append(f'{split}: expected a list')
            continue
        answerable = Counter()
        unanswerable = 0
        for i, item in enumerate(items):
            prefix = f'{split}[{i}]'
            if not isinstance(item, dict):
                errors.append(f'{prefix}: expected an object')
                continue
            ident = item.get('id')
            question = item.get('question')
            if not isinstance(ident, str) or not ident.strip() or ident in ids:
                errors.append(f'{prefix}: missing or duplicate ID')
            else:
                ids.add(ident)
            if not isinstance(question, str) or not question.strip():
                errors.append(f'{prefix}: missing question')
            else:
                normalized = ' '.join(question.casefold().split())
                if normalized in questions:
                    errors.append(f'{prefix}: duplicate question from {questions[normalized]}')
                questions[normalized] = prefix
            if not isinstance(item.get('rationale'), str) or not item['rationale'].strip():
                errors.append(f'{prefix}: missing rationale')
            if item.get('answerable') is True:
                group = item.get('group')
                if group not in groups:
                    errors.append(f'{prefix}: invalid main group')
                else:
                    answerable[group] += 1
                if not isinstance(item.get('answer'), str) or not item['answer'].strip():
                    errors.append(f'{prefix}: missing gold answer')
                evidence = item.get('evidence')
                if not isinstance(evidence, list) or not evidence:
                    errors.append(f'{prefix}: missing evidence')
                else:
                    for ev in evidence:
                        if not isinstance(ev, dict) or not isinstance(ev.get('pdf_page'), int) or not 1 <= ev['pdf_page'] <= 127 or not ev.get('region') or not ev.get('source'):
                            errors.append(f'{prefix}: evidence needs source, physical pdf_page and region')
                if item.get('original_checked') is not True:
                    errors.append(f'{prefix}: original-page check not recorded')
            elif item.get('answerable') is False:
                unanswerable += 1
                if not isinstance(item.get('absence_check'), str) or not item['absence_check'].strip():
                    errors.append(f'{prefix}: missing absence-check method')
            else:
                errors.append(f'{prefix}: answerable must be boolean')
        if sum(answerable.values()) < minimum[0] or unanswerable < minimum[1]:
            errors.append(f'{split}: needs >= {minimum[0]} answerable and >= {minimum[1]} unanswerable')
        if split == 'test':
            for group, count in groups.items():
                if answerable[group] < count:
                    errors.append(f'test: {group} needs >= {count}, found {answerable[group]}')
    return errors


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('benchmark', type=Path)
    a = p.parse_args()
    errors = validate(json.loads(a.benchmark.read_text(encoding='utf8')))
    print(json.dumps({'valid_structure': not errors, 'errors': errors,
                      'warning': 'Structural checks do not verify gold, absence, paraphrases or original evidence.'}, indent=2))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())
