// サイトの分類体系（コドナビ＝エンジニア/キャリアの学び・転職・資格の比較ハブ）。
// slug は services.json の subCategory ・記事frontmatterの categorySlug と一致させる（結合キー）。
// gender 軸は無い。プログラミングスクールから開始し、転職・資格まで対象を拡張（2026-08-03）。

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
  {
    slug: 'career',
    label: '転職・エージェント',
    emoji: '🧭',
    blurb: 'エンジニア・IT系を中心に、転職エージェントや転職活動の支援サービスを、特徴・サポート内容で比較。',
  },
  {
    slug: 'qualification',
    label: '資格・スキル講座',
    emoji: '📜',
    blurb: '資格取得や実務スキルの養成講座を、内容・サポート・費用の観点で比較。学びを仕事につなげたい人向け。',
  },
];

export const categoryBySlug = (slug?: string | null): Category | undefined =>
  CATEGORIES.find((c) => c.slug === slug);
