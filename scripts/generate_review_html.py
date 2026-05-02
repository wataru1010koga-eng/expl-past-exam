#!/usr/bin/env python3
import csv
import argparse
from pathlib import Path

CHOICE_LABELS = ["①", "②", "③", "④", "⑤"]

STYLE = """
<style>
  body { font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
  h1 { color: #333; border-bottom: 2px solid #666; padding-bottom: 8px; }
  .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
  .card-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
  .q-num { font-size: 18px; font-weight: bold; color: #555; min-width: 40px; }
  .answer-badge { background: #2e7d32; color: white; border-radius: 12px; padding: 2px 12px; font-size: 14px; }
  .question { font-size: 15px; color: #222; margin-bottom: 14px; line-height: 1.6; }
  .choice { padding: 8px 12px; margin: 4px 0; border-radius: 4px; font-size: 14px; line-height: 1.5; }
  .choice.correct { background: #e8f5e9; border-left: 4px solid #2e7d32; font-weight: bold; }
  .choice.incorrect { background: #fafafa; border-left: 4px solid #ddd; color: #444; }
</style>
"""

def answer_label(answer_num):
    idx = int(answer_num) - 1
    return CHOICE_LABELS[idx] if 0 <= idx < 5 else str(answer_num)

def generate_html(year_label, rows):
    cards = []
    for row in rows:
        num = row["number"]
        question = row["question"]
        answer = int(row["answer"])
        choices = [row.get(f"choice{i}", "") for i in range(1, 6)]

        choice_html = ""
        for i, text in enumerate(choices):
            if not text:
                continue
            label = CHOICE_LABELS[i]
            css = "correct" if (i + 1) == answer else "incorrect"
            # CSV内に①②…がすでに含まれている場合は重複しないよう除去
            display_text = text.lstrip("①②③④⑤").lstrip()
            choice_html += f'<div class="choice {css}">{label} {display_text}</div>\n'

        cards.append(f"""
<div class="card">
  <div class="card-header">
    <span class="q-num">問{num}</span>
    <span class="answer-badge">正答 {answer_label(answer)}</span>
  </div>
  <div class="question">{question}</div>
  {choice_html}
</div>""")

    body = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>{year_label} レビュー</title>
{STYLE}
</head>
<body>
<h1>{year_label} 過去問レビュー（{len(rows)}問）</h1>
{body}
</body>
</html>"""


def process_year(csv_path: Path):
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    year_key = csv_path.stem.split("_")[0]  # e.g. "r3"
    year_map = {"r3": "令和3年度", "r4": "令和4年度", "r5": "令和5年度", "r6": "令和6年度", "r7": "令和7年度"}
    label = year_map.get(year_key, year_key.upper())

    html = generate_html(label, rows)
    out_path = csv_path.parent / f"{year_key}_review.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"生成: {out_path} ({len(rows)}問)")


def main():
    parser = argparse.ArgumentParser(description="CSVからレビュー用HTMLを生成")
    parser.add_argument("--year", help="年度を指定（例: r3）。省略時は全年度")
    args = parser.parse_args()

    base = Path(__file__).parent.parent / "content"

    if args.year:
        csv_path = base / args.year / f"{args.year}_questions.csv"
        if not csv_path.exists():
            print(f"ファイルが見つかりません: {csv_path}")
            return
        process_year(csv_path)
    else:
        for csv_path in sorted(base.glob("*/r*_questions.csv")):
            process_year(csv_path)


if __name__ == "__main__":
    main()
