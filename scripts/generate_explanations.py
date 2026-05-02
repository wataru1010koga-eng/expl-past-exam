#!/usr/bin/env python3
"""
CSVを読んで解説MDファイルを生成するスクリプト。
使い方:
  python3 scripts/generate_explanations.py --year r7
  python3 scripts/generate_explanations.py --year r7 --number 1
  python3 scripts/generate_explanations.py --year r7 --start 5 --end 10
  python3 scripts/generate_explanations.py --year r7 --force
  python3 scripts/generate_explanations.py --year r7 --dry-run
  python3 scripts/generate_explanations.py --year r7 --model claude-sonnet-4-6
"""
import csv
import argparse
import time
import os
from datetime import datetime
from pathlib import Path

YEAR_TO_YEAR_INT = {"r3": 2021, "r4": 2022, "r5": 2023, "r6": 2024, "r7": 2025}
ANSWER_SYMBOLS = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}

SYSTEM_PROMPT = """あなたは技術士第一次試験（森林部門）の過去問解説を作成する専門家です。
受験者が答え合わせをしながらすぐに理解できる、簡潔で正確な解説を書いてください。
以下のフォーマットを厳守してください：

【正答】〇

【誤りのポイント】
正答の選択肢がなぜ誤りか（または最も不適切か）を1〜3文で説明する。
専門用語は使ってよいが、簡潔に核心だけ述べる。

【各選択肢の解説】
①〜（1〜2文で正誤と理由）
②〜（正答の番号はスキップ）
（以下同様）

【参考】
信頼できる情報源（公式資料、学術文献、教科書等）のURLや書誌情報を記載。
該当するものがなければ省略。

禁止事項：
- 同じ内容の繰り返し
- 「重要ポイント」などの追加セクション
- 100文字を超える箇条書き"""


def build_user_prompt(row: dict) -> str:
    answer_num = int(row["answer"])
    answer_symbol = ANSWER_SYMBOLS.get(answer_num, str(answer_num))
    lines = [f"以下の問題の解説を作成してください。正答は{answer_symbol}です。", ""]
    lines.append(row["question"])
    lines.append("")
    for i in range(1, 6):
        choice = row.get(f"choice{i}", "")
        if choice:
            lines.append(choice)
    return "\n".join(lines)


def build_frontmatter(row: dict) -> str:
    question = row["question"].replace('"', '\\"')
    return (
        f'---\n'
        f'year: {row["year"]}\n'
        f'number: {row["number"]}\n'
        f'question: "{question}"\n'
        f'answer: {row["answer"]}\n'
        f'---\n'
    )


def call_api(client, row: dict, model: str) -> str:
    user_prompt = build_user_prompt(row)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text


def output_path(content_dir: Path, year_key: str, number: int) -> Path:
    return content_dir / f"{year_key}_III_{number:02d}.md"


def main():
    parser = argparse.ArgumentParser(description="CSVから解説MDを生成")
    parser.add_argument("--year", required=True, choices=list(YEAR_TO_YEAR_INT.keys()))
    parser.add_argument("--number", type=int, help="1問だけ処理")
    parser.add_argument("--start", type=int, default=1, help="開始番号（デフォルト: 1）")
    parser.add_argument("--end", type=int, default=35, help="終了番号（デフォルト: 35）")
    parser.add_argument("--force", action="store_true", help="既存MDを上書き")
    parser.add_argument("--dry-run", action="store_true", help="APIを叩かず処理予定を表示")
    parser.add_argument("--delay", type=float, default=1.0, help="API呼び出し間の待機秒数")
    parser.add_argument("--model", default="claude-haiku-4-5", help="使用モデル（デフォルト: claude-haiku-4-5）")
    args = parser.parse_args()

    base = Path(__file__).parent.parent / "content"
    csv_path = base / args.year / f"{args.year}_questions.csv"
    content_dir = base / args.year

    if not csv_path.exists():
        print(f"CSVが見つかりません: {csv_path}")
        return

    with open(csv_path, encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    if args.number:
        rows = [r for r in all_rows if int(r["number"]) == args.number]
    else:
        rows = [r for r in all_rows if args.start <= int(r["number"]) <= args.end]

    if not rows:
        print("処理対象の行がありません。")
        return

    skip_flags = [
        output_path(content_dir, args.year, int(r["number"])).exists() and not args.force
        for r in rows
    ]
    skip_count = sum(skip_flags)
    process_count = len(rows) - skip_count
    year_label = f"[{args.year.upper()}]"

    if args.dry_run:
        print(f"{year_label} dry-run: {process_count}問処理 / {skip_count}問スキップ")
        for row, will_skip in zip(rows, skip_flags):
            path = output_path(content_dir, args.year, int(row["number"]))
            status = "[SKIP]" if will_skip else "[NEW] "
            print(f"  {status} {path.name}")
        return

    print(f"{year_label} 解説MD生成を開始します（{len(rows)}問中 {skip_count}問スキップ = {process_count}問処理）")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("エラー: 環境変数 ANTHROPIC_API_KEY が設定されていません。")
        return

    try:
        import anthropic
    except ImportError:
        print("エラー: anthropic パッケージが見つかりません。`pip install anthropic` を実行してください。")
        return

    client = anthropic.Anthropic()
    log_path = content_dir / f"{args.year}_generate.log"
    ok_count = 0
    err_count = 0
    actual_skip = 0

    with open(log_path, "a", encoding="utf-8") as log_f:

        def log(msg: str):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_f.write(f"[{ts}] {msg}\n")
            log_f.flush()

        for i, (row, will_skip) in enumerate(zip(rows, skip_flags), 1):
            num = int(row["number"])
            path = output_path(content_dir, args.year, num)
            label = f"{i:2d}/{len(rows)}"

            if will_skip:
                print(f"  {label} {path.name} ... [SKIP]")
                log(f"[SKIP]  {path.name} (既存)")
                actual_skip += 1
                continue

            print(f"  {label} {path.name} ...", end="", flush=True)
            t0 = time.time()
            try:
                explanation = call_api(client, row, args.model)
                content = build_frontmatter(row) + "\n" + explanation + "\n"
                path.write_text(content, encoding="utf-8")
                elapsed = time.time() - t0
                print(f" [OK] ({elapsed:.1f}s)")
                log(f"[OK]    {path.name}")
                ok_count += 1
            except Exception as e:
                elapsed = time.time() - t0
                print(f" [ERROR] ({elapsed:.1f}s) {e}")
                log(f"[ERROR] {path.name} - {e}")
                err_count += 1

            if i < len(rows):
                time.sleep(args.delay)

    print(f"\n完了: {ok_count}問生成 / {err_count}問エラー / {actual_skip}問スキップ")


if __name__ == "__main__":
    main()
