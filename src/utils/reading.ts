// 読了目安（分）。日本語の黙読はおおよそ1分500字で、記事本文と導入・まとめの文字数から出す。
// 記事ページと一覧行の表示が同じ値を使う。
import type { CollectionEntry } from 'astro:content';

const CHARS_PER_MINUTE = 500;

function plainLength(md: string): number {
  return md
    .replace(/```[\s\S]*?```/g, '')          // コードブロック
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')    // 画像
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // リンクは文字だけ残す
    .replace(/<[^>]+>/g, '')                 // HTML タグ
    .replace(/[#>*_`|\-]/g, '')              // Markdown 記号
    .replace(/\s+/g, '').length;
}

export function readingMinutes(article: CollectionEntry<'articles'>): number {
  const d = article.data;
  const chars = plainLength(article.body ?? '') + (d.intro?.length ?? 0) + (d.outro?.length ?? 0);
  return Math.max(1, Math.round(chars / CHARS_PER_MINUTE));
}

// 記事の型を、読者がいまいる段階の言葉に置き換える。トップの索引と一覧行が使う。
// 読了目安で選ばせる案は、全記事が2〜4分に収まっていて分かれないため採らなかった（2026-10-02 実測）。
export const STAGES = [
  { key: 'guide', label: '知る', hint: '制度や仕組みを知りたい' },
  { key: 'problem', label: '迷う', hint: 'つまずいていることがある' },
  { key: 'compare', label: '比べる', hint: 'サービスを比べて決めたい' },
  { key: 'essay', label: '考える', hint: '進め方を考えたい' },
] as const;

export function stageOf(type: string | null | undefined) {
  return STAGES.find((s) => s.key === type) ?? null;
}
