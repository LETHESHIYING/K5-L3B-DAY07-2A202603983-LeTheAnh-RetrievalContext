"""Make a new vision snapshot with one source-checked chart correction."""
import argparse
import json
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    if a.output.exists():
        raise SystemExit('Output exists; refuse to overwrite')
    files = sorted(a.input.glob('page_*.json'))
    if len(files) != 127:
        raise SystemExit('Expected 127 page records')
    a.output.mkdir(parents=True)
    for f in files:
        shutil.copy2(f, a.output / f.name)
    target = a.output / 'page_0022.json'
    data = json.loads(target.read_text(encoding='utf8'))
    chart = [x for x in data['description']['visual_items'] if x.get('type') == 'stacked bar chart']
    if len(chart) != 1:
        raise SystemExit('Expected one stacked bar chart on page 22')
    original = chart[0]['visible_values']
    expected3 = 'FY 2024 green 10, yellow 1, red 1.'
    expected4 = 'FY 2023 green 10, red 1, gray 1;'
    if expected3 not in original or expected4 not in original:
        raise SystemExit('Source description differs; do not apply correction blindly')
    corrected = original.replace(expected3, 'FY 2024 green 10, yellow 1.')
    corrected = corrected.replace(expected4, 'FY 2023 green 10, yellow 1, red 1;')
    chart[0]['visible_values'] = corrected
    data['manual_corrections'] = [{'location':'physical PDF page 22, central chart',
        'reason':'Original chart shows goal 3 FY2024 green 10/yellow 1 and goal 4 FY2023 green 10/yellow 1/red 1.',
        'original_visible_values': original, 'corrected_visible_values': corrected,
        'review_scope':'Only the two specified bar segments; all other model descriptions remain unverified.'}]
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Created new 127-page snapshot; page 22 two chart errors corrected, original preserved.')


if __name__ == '__main__':
    main()
