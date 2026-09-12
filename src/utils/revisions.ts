export interface Revision {
  /** 改訂日（YYYY-MM-DD） */
  date: string;
  /** 対象年度ラベル（例: 'R4'）。サイト全体に関わる改訂は省略可 */
  yearLabel?: string;
  /** 対象の問題番号。年度全体・サイト全体の改訂は省略可 */
  number?: number;
  /** 該当ページへのリンク（例: '/r4/24/'）。あれば改訂内容から遷移できる */
  href?: string;
  /** 改訂内容の要約 */
  summary: string;
}

/**
 * 改訂履歴。新しいものを先頭に追加する。
 * 解説の修正・誤字訂正・問題文の修正などを記録し、トップページに表示する。
 */
export const REVISIONS: Revision[] = [
  {
    date: '2026-09-12',
    yearLabel: 'R7',
    number: 4,
    href: '/r7/4/',
    summary: '第4問 選択肢④の問題文OCR誤字「柑高」を「樹高」に修正。内容の正誤に変更はありません。',
  },
  {
    date: '2026-08-08',
    yearLabel: 'R4',
    number: 24,
    href: '/r4/24/',
    summary: '第24問（排水施設）解説の表現を修正（誤字の訂正）。内容の正誤に変更はありません。',
  },
];
