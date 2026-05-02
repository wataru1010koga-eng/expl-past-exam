#!/usr/bin/env python3
"""
corrections.txt を読んでCSVに一括修正を適用するスクリプト。

corrections.txt の書き方:
  年度 問番号 フィールド: 誤テキスト → 正テキスト
  フィールド: q=問題文, 1〜5=選択肢①〜⑤
  # から始まる行はコメント

例:
  R3 5 1: 構高 → 樹高
  R4 7 q: 炊の記述 → 次の記述
"""
import csv
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent

FIELD_MAP = {
    'q': 'question',
    '1': 'choice1', '2': 'choice2', '3': 'choice3',
    '4': 'choice4', '5': 'choice5',
}
FIELDNAMES = ['year', 'number', 'question', 'answer',
              'choice1', 'choice2', 'choice3', 'choice4', 'choice5']

YEAR_MAP = {
    'r3': 'r3', 'r4': 'r4', 'r5': 'r5', 'r6': 'r6', 'r7': 'r7',
    'R3': 'r3', 'R4': 'r4', 'R5': 'r5', 'R6': 'r6', 'R7': 'r7',
}


def parse_corrections(path: Path):
    corrections = []
    for lineno, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        # 書式: 年度 問番号 フィールド: 誤 → 正
        m = re.match(r'([Rr]\d)\s+(\d+)\s+([q1-5])\s*[:：]\s*(.+?)\s*→\s*(.+)', line)
        if not m:
            print(f'[スキップ] 行{lineno}: 書式不正「{line}」')
            continue
        year_key, num, field_key, old, new = m.groups()
        # 全角スペースを含む前後の空白を除去
        old = old.strip().strip('　')
        new = new.strip().strip('　')
        corrections.append({
            'year': YEAR_MAP[year_key],
            'num': num,
            'field': FIELD_MAP[field_key],
            'old': old.strip(),
            'new': new.strip(),
            'lineno': lineno,
        })
    return corrections


def apply(corrections):
    # 年度ごとにまとめて処理
    by_year = {}
    for c in corrections:
        by_year.setdefault(c['year'], []).append(c)

    applied = 0
    not_found = []

    for year, items in by_year.items():
        csv_path = BASE / 'content' / year / f'{year}_questions.csv'
        with open(csv_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        for item in items:
            matched = False
            for row in rows:
                if row['number'] != item['num']:
                    continue
                field = item['field']
                if item['old'] in row[field]:
                    row[field] = row[field].replace(item['old'], item['new'])
                    print(f"✓ {year.upper()} 問{item['num']} [{field}] "
                          f"「{item['old']}」→「{item['new']}」")
                    applied += 1
                    matched = True
                    break
            if not matched:
                not_found.append(item)
                print(f"✗ {year.upper()} 問{item['num']} [{item['field']}] "
                      f"「{item['old']}」が見つかりません（行{item['lineno']}）")

        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
            w.writeheader()
            w.writerows(rows)

    print(f'\n適用: {applied}件 / 未検出: {len(not_found)}件')
    return applied, not_found


def main():
    corrections_path = BASE / 'corrections.txt'
    if not corrections_path.exists():
        print('corrections.txt が見つかりません')
        sys.exit(1)

    corrections = parse_corrections(corrections_path)
    if not corrections:
        print('修正指示がありません')
        return

    print(f'{len(corrections)}件の修正を適用します\n')
    apply(corrections)


if __name__ == '__main__':
    main()
