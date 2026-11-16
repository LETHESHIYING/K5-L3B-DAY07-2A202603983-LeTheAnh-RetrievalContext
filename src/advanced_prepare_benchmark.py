"""Create the first source-reviewed benchmark candidate from recorded drafts."""
import json
from pathlib import Path

SOURCE = 'https://www.nasa.gov/wp-content/uploads/2023/11/nasa-fy-2024-afr-1.pdf'


def multi(ident, question, answer, entries, rationale):
    return {'id': ident, 'group': 'multi_hop', 'answerable': True, 'question': question,
            'answer': answer, 'rationale': rationale,
            'evidence': [{'source': SOURCE, 'pdf_page': n, 'region': region} for n, region in entries],
            'original_checked': True, 'verification_note': 'AI compared original page renderings; no independent human review claimed.'}


def negative(ident, question):
    return {'id': ident, 'group': 'unanswerable', 'answerable': False, 'question': question,
            'answer': None, 'rationale': 'A completed future fiscal year postdates this 2024 report.',
            'absence_check': 'PDF page 6 is dated November 15, 2024; PDF metadata says last modified November 29, 2024. '
                             'The question asks for an actual completed later fiscal year, not a projection. '
                             'Extracted text can be searched but keyword absence alone is not proof.',
            'original_checked': True}


def main():
    dev = json.loads(Path('data/advanced_benchmark_draft_dev.json').read_text(encoding='utf8'))['items'][:15]
    candidates = json.loads(Path('data/advanced_benchmark_test_review_inprogress.json').read_text(encoding='utf8'))['items']
    test = [x for x in candidates if x['answerable'] and x['group'] != 'multi_hop']
    if len(test) != 20 or any(not x.get('original_checked') for x in test):
        raise SystemExit('Missing source check in test candidates')
    for x in dev:
        x['original_checked'] = True
        x['verification_note'] = 'AI compared the stated answer and evidence with the original rendered page; not independent human review.'
        for e in x['evidence']:
            e['pdf_page'] = e.pop('physical_pdf_page', e.get('pdf_page'))
            e['source'] = SOURCE
    x = next(t for t in test if t['id'] == 'X03')
    x.update(question='Which team supports the Mission Support Council in overseeing the internal-control evaluation and reporting process?',
             answer='Senior Assessment Team (SAT)',
             rationale='The original text identifies the SAT as supporting the MSC.',
             evidence=[{'pdf_page': 38, 'region': 'left-column paragraph about the Senior Assessment Team', 'source': SOURCE}],
             verification_note='Original rendered page 38 states that the Senior Assessment Team supports the MSC.')
    multis = [
        multi('M01', 'What is the difference, in millions of dollars, between NASA FY 2024 total budgetary resources and FY 2024 total undelivered orders?', '$17,837 million; $30,051 million minus $12,214 million.', [(53,'2024 Total Budgetary Resources row'),(70,'2024 Total Undelivered Orders row')], '30,051 − 12,214 = 17,837 million.'),
        multi('M02', 'How much higher were NASA FY 2024 total net outlays than its FY 2023 total net cost, in millions of dollars?', '$399 million; $25,015 million minus $24,616 million.', [(71,'2024 Total Net Outlays total column'),(72,'2023 Net Cost total column')], 'Different metrics and years are compared numerically: 25,015 − 24,616 = 399 million.'),
        multi('M03', 'What is the numerical difference between NASA FY 2024 total unexpended appropriations and the total principal of its lease receivables, in millions of dollars?', '$10,655 million; $13,157 million minus $697 million.', [(52,'2024 Total Unexpended Appropriations row'),(69,'Total principal of lease receivables row')], 'Different financial amounts are compared numerically: 13,157 − 697 = 10,655 million.'),
        multi('M04', 'By how much did NASA FY 2024 total budgetary resources exceed its FY 2024 net position, in millions of dollars?', '$10,211 million; $30,051 million minus $19,840 million.', [(53,'2024 Total Budgetary Resources row'),(52,'2024 Net Position row')], 'Different accounting measures are compared numerically: 30,051 − 19,840 = 10,211 million.')]
    dn = [negative('DUA', "According to the FY 2024 report, what was NASA's actual final FY 2025 net cost of operations?"),
          negative('DUB', "According to the FY 2024 report, what was NASA's final audit opinion on its FY 2025 financial statements?"),
          negative('DUC', "According to the FY 2024 report, what were NASA's actual final FY 2025 total budgetary resources after year end?")]
    tn = [negative('TUA', "According to this FY 2024 report, what were NASA's actual final FY 2026 total assets?"),
          negative('TUB', "According to this FY 2024 report, what were NASA's actual final FY 2027 total liabilities?"),
          negative('TUC', "According to this FY 2024 report, what was NASA's actual final FY 2028 net position?"),
          negative('TUD', "According to this FY 2024 report, what were NASA's actual final FY 2029 undelivered orders?"),
          negative('TUE', "According to this FY 2024 report, what were NASA's actual final FY 2030 total net outlays?"),
          negative('TUF', "According to this FY 2024 report, what were NASA's final FY 2031 total unexpended appropriations?")]
    benchmark = {'dev': dev + dn, 'test': test + multis + tn,
                 'metadata': {'status': 'source-reviewed candidate; temporal negative cases are narrow',
                              'source_url': SOURCE,
                              'source_sha256': '65ee29adf5f3a92fcd74701696c25dae8f2d18f1ba2e7f4fba2bcfc059acbefc',
                              'source_audit': 'Original pages checked by AI; not an independent human review.',
                              'independence': 'Constructed before dev selection and before formal test; pilot questions excluded.'}}
    output = Path('data/advanced_benchmark_v1.json')
    with output.open('x', encoding='utf8') as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'Wrote {len(benchmark["dev"])} dev and {len(benchmark["test"])} test items')


if __name__ == '__main__':
    main()
