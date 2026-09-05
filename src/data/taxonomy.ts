// サイトの分類体系（コドナビ＝働きながら学び直す社会人のための読み物と比較）。
// slug は services.json の subCategory ・記事frontmatterの categorySlug と一致させる（結合キー）。
// gender 軸は無い。
//
// 2026-09-05: 読者像を「学び直し・働き方を変える社会人」に定義し直し、slug は変えずに
// ラベルと説明だけを広げた（判断ログ 2026-09-05「コドナビは総合化しない」）。
// URL を変えないので、記事0件のカテゴリページが生まれない。
// 絵文字は持たない（アイコンで意味を足せていないため）。
export interface Category {
  slug: string;
  label: string;
  blurb: string; // カテゴリページの説明・meta description に使う
}

export const CATEGORIES: Category[] = [
  {
    slug: 'programming',
    label: 'プログラミング・IT',
    blurb: 'プログラミングスクールや独学の進め方、Web制作・開発まわりのサービスを、費用と続けやすさの観点で調べています。',
  },
  {
    slug: 'career',
    label: '転職・働き方',
    blurb: '転職エージェント、副業や独立の始め方、在宅で働くための環境づくり。今の働き方を変えたいときに調べたことをまとめています。',
  },
  {
    slug: 'qualification',
    label: '学び・スキル講座',
    blurb: '資格取得や実務スキルの講座、教育訓練給付金のような公的な学び支援制度。働きながら学び直すときの選択肢を整理しています。',
  },
  {
    slug: 'language',
    label: '語学・留学',
    blurb: '英会話やビジネス中国語のスクール、社会人の語学やり直し、留学・語学研修。仕事で使う語学を身につけたい人向けです。',
  },
];

export const categoryBySlug = (slug?: string | null): Category | undefined =>
  CATEGORIES.find((c) => c.slug === slug);
