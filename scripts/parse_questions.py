#!/usr/bin/env python3
"""
問題テキストファイルを解析してCSVを生成するスクリプト。
使い方:
  python3 scripts/parse_questions.py --year r6 --preview   # 問1のみ表示
  python3 scripts/parse_questions.py --year r6             # CSV生成
"""
import re
import csv
import argparse
from pathlib import Path

# answer.txt から転記した全年度の正答
ANSWERS = {
    "r3": {1:3,2:2,3:2,4:4,5:5,6:3,7:5,8:5,9:3,10:2,11:3,12:2,13:4,14:1,15:4,
           16:5,17:5,18:3,19:1,20:3,21:5,22:5,23:3,24:4,25:2,26:2,27:3,28:5,
           29:4,30:3,31:5,32:1,33:3,34:2,35:4},
    "r4": {1:1,2:4,3:3,4:2,5:5,6:5,7:2,8:3,9:3,10:1,11:3,12:2,13:1,14:5,15:3,
           16:4,17:4,18:3,19:2,20:2,21:1,22:2,23:3,24:4,25:1,26:2,27:1,28:5,
           29:1,30:4,31:2,32:2,33:4,34:4,35:5},
    "r5": {1:1,2:4,3:2,4:5,5:2,6:5,7:3,8:4,9:5,10:1,11:3,12:5,13:4,14:3,15:3,
           16:1,17:2,18:1,19:4,20:5,21:2,22:3,23:5,24:1,25:4,26:2,27:2,28:5,
           29:4,30:3,31:2,32:2,33:1,34:1,35:4},
    "r6": {1:4,2:5,3:4,4:3,5:2,6:1,7:2,8:5,9:4,10:5,11:4,12:2,13:3,14:1,15:2,
           16:5,17:4,18:3,19:5,20:1,21:1,22:2,23:4,24:3,25:1,26:2,27:4,28:1,
           29:4,30:4,31:2,32:4,33:2,34:4,35:1},
    "r7": {1:4,2:1,3:5,4:2,5:4,6:3,7:2,8:2,9:5,10:4,11:3,12:5,13:4,14:3,15:1,
           16:4,17:4,18:3,19:3,20:5,21:2,22:3,23:2,24:4,25:1,26:2,27:2,28:5,
           29:2,30:2,31:5,32:2,33:5,34:3,35:3},
}

YEAR_TO_YEAR_INT = {"r3": 2021, "r4": 2022, "r5": 2023, "r6": 2024, "r7": 2025}

# ページフッター/ヘッダーのパターン
PAGE_MARKER_RE = re.compile(r'^【13】森林')
# 問題番号マーカー: Ⅲ-数字 の各種OCR表記に対応
#   I{1,3}-N, Ⅲ-N, 皿-N          通常パターン
#   1I-N                           OCRが1を付加した誤読 (例: 1I-24)
#   1-N                            Ⅲ全体が1に誤読された場合 (例: 1-30)
#   -N                             ページブレークで頭が切れた場合 (例: -17)
PROBLEM_MARKER_RE = re.compile(
    r'^(?:'
    r'\d*(?:I{1,3}|Ⅲ|皿)-'  # (省略可の数字) + ローマ数字 + ハイフン
    r'|\d+-'                   # 数字 + ハイフン (1-30 など)
    r'|-'                      # ハイフンのみ (-17 など)
    r')(\d{1,2})(.*)'
)
# 問題文中の選択肢（全角丸数字）
CHOICE_RE = re.compile(r'[①②③④⑤]')

def collapse(line: str) -> str:
    """行内のスペースをすべて除去し、全角ハイフンをASCIIに正規化する"""
    return line.strip().replace(' ', '').replace('－', '-')

def parse_txt(txt_path: Path) -> dict[int, str]:
    """テキストファイルを読んで {問番号: 問本文} の辞書を返す"""
    with open(txt_path, encoding='utf-8') as f:
        raw_lines = f.readlines()

    problems = {}
    current_num = None
    buf = []
    skip_header = True  # 指示文より前はスキップ

    for raw in raw_lines:
        line = collapse(raw)
        if not line:
            continue
        if PAGE_MARKER_RE.match(line):
            continue

        # ヘッダー行をスキップ（「解答せよ」が含まれる行まで）
        if skip_header:
            if '解答せよ' in line or '技術士第一次試験' in line:
                continue  # この行自体もスキップ
            # ヘッダーが終わった → 問1の本文が始まる
            skip_header = False
            current_num = 1
            buf = []

        # 問題番号マーカー（問2以降）
        m = PROBLEM_MARKER_RE.match(line)
        if m:
            num = int(m.group(1))
            # 1〜35の範囲のみ問題番号として扱う
            if 1 <= num <= 35:
                if current_num is not None:
                    problems[current_num] = ''.join(buf).strip()
                current_num = num
                buf = [m.group(2)]  # マーカー後の残りテキスト
                continue

        buf.append(line)

    # 最後の問題を保存
    if current_num is not None:
        problems[current_num] = ''.join(buf).strip()

    return problems


def split_choices(text: str) -> tuple[str, list[str]]:
    """問本文を問題文と選択肢①〜⑤に分割する"""
    markers = ['①', '②', '③', '④', '⑤']
    positions = [(text.find(m), m) for m in markers if text.find(m) != -1]
    positions.sort()

    if not positions:
        return text, [''] * 5

    stem = text[:positions[0][0]].strip()
    choices = []
    for i, (pos, ch) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        choice_text = text[pos:end].strip()
        choices.append(choice_text)

    while len(choices) < 5:
        choices.append('')

    return stem, choices


def build_rows(year_key: str, txt_path: Path) -> list[dict]:
    answers = ANSWERS[year_key]
    year_int = YEAR_TO_YEAR_INT[year_key]
    problems = parse_txt(txt_path)

    rows = []
    for num in range(1, 36):
        text = problems.get(num, '')
        stem, choices = split_choices(text)
        rows.append({
            'year': year_int,
            'number': num,
            'question': stem,
            'answer': answers.get(num, ''),
            'choice1': choices[0],
            'choice2': choices[1],
            'choice3': choices[2],
            'choice4': choices[3],
            'choice5': choices[4],
        })
    return rows


def preview(row: dict):
    print(f"\n{'='*60}")
    print(f"【問{row['number']}】{row['question']}")
    print(f"{'='*60}")
    for i, key in enumerate(['choice1','choice2','choice3','choice4','choice5'], 1):
        marker = ['①','②','③','④','⑤'][i-1]
        print(f"{marker} {row[key]}")
    print(f"\n正答: {row['answer']}")
    print('='*60)


def save_csv(rows: list[dict], out_path: Path):
    fieldnames = ['year','number','question','answer','choice1','choice2','choice3','choice4','choice5']
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV保存完了: {out_path} ({len(rows)}問)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', required=True, choices=['r3','r4','r5','r6','r7'])
    parser.add_argument('--preview', action='store_true', help='問1のみ表示してCSVは生成しない')
    args = parser.parse_args()

    base = Path(__file__).parent.parent / 'content' / args.year
    txt_path = base / f'{args.year}_question.txt'

    if not txt_path.exists():
        print(f"ファイルが見つかりません: {txt_path}")
        return

    rows = build_rows(args.year, txt_path)

    if args.preview:
        preview(rows[0])
        print("\n※ 問題文・選択肢が正しければ --preview を外して実行するとCSVを生成します。")
    else:
        out_path = base / f'{args.year}_questions.csv'
        save_csv(rows, out_path)


if __name__ == '__main__':
    main()
