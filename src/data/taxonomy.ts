// サイトの分類体系（スクールのサブジャンル）。
// slug は services.json の subCategory ・記事frontmatterの categorySlug と一致させる（結合キー）。
// スクール比較サイトのため gender 軸は無い（プログラミング1本で開始。english 等は後で追加）。

export interface Category {
  slug: string;
  label: string;
  emoji: string;
  blurb: string; // カテゴリページの説明・meta description に使う
}

export const CATEGORIES: Category[] = [
  {
    slug: 'programming',
    label: 'プログラミングスクール',
    emoji: '💻',
    blurb: '未経験からエンジニアを目指せるプログラミングスクールを、料金・特徴・サポート内容で比較。',
  },
];

export const categoryBySlug = (slug?: string | null): Category | undefined =>
  CATEGORIES.find((c) => c.slug === slug);
