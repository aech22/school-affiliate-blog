// サイトの分類体系（大元の性別軸 gender × ジャンル軸 category）。
// slug は scripts/config.py の CATEGORIES と一致させること（記事frontmatterの categorySlug と結合する）。

export type GenderSlug = 'men' | 'women' | 'unisex';

export interface Category {
  slug: string;
  label: string;
  gender: GenderSlug;
  emoji: string;
  blurb: string; // カテゴリページの説明・meta description に使う
}

export interface Gender {
  slug: GenderSlug;
  label: string;
  emoji: string;
  blurb: string;
}

// ガジェナビは全カテゴリ unisex のため、メンズ系/レディース系タブは廃止（2026-08-03）。
// unisex のみ残す（/unisex/ ページと各種ヘルパーの後方互換を維持）。
export const GENDERS: Gender[] = [
  { slug: 'unisex', label: 'ユニセックス系', emoji: '🧑', blurb: '性別を問わず使える人気アイテムをまとめてチェック。' },
];

// ガジェナビ：ガジェット物販特化のため全カテゴリ unisex（slug は scripts/config.py と一致）。
export const CATEGORIES: Category[] = [
  { slug: 'earphones',     label: 'イヤホン・ヘッドホン',           gender: 'unisex', emoji: '🎧', blurb: '通勤・在宅で使えるワイヤレスイヤホン・ヘッドホンを比較。' },
  { slug: 'charging',      label: 'モバイルバッテリー・充電器',     gender: 'unisex', emoji: '🔋', blurb: '大容量バッテリー・急速充電器など、電源まわりのアイテムを比較。' },
  { slug: 'pc-peripheral', label: 'PC周辺機器',                     gender: 'unisex', emoji: '🖱️', blurb: 'マウス・キーボード・モニターなど、作業効率を上げる周辺機器を比較。' },
  { slug: 'smart-home',    label: 'スマート家電',                   gender: 'unisex', emoji: '🏠', blurb: 'スマートスピーカー・見守りカメラなど、暮らしを便利にする家電を比較。' },
  { slug: 'camera-gear',   label: 'カメラ・周辺機器',               gender: 'unisex', emoji: '📷', blurb: '三脚・SDカードなど、撮影を支える周辺機器を比較。' },
  { slug: 'gaming',        label: 'ゲーミングデバイス',             gender: 'unisex', emoji: '🎮', blurb: 'ゲーミングチェア・マウスなど、快適なプレイ環境を作るデバイスを比較。' },
  { slug: 'wearable',      label: 'スマートウォッチ・ウェアラブル', gender: 'unisex', emoji: '⌚', blurb: '健康管理・通知に使えるスマートウォッチ・活動量計を比較。' },
  { slug: 'home-gadget',   label: '生活家電ガジェット',             gender: 'unisex', emoji: '💨', blurb: 'ドライヤー・シェーバーなど、毎日使う生活家電を比較。' },
];

export const categoryBySlug = (slug?: string | null): Category | undefined =>
  CATEGORIES.find((c) => c.slug === slug);

export const genderBySlug = (slug?: string | null): Gender | undefined =>
  GENDERS.find((g) => g.slug === slug);

export const categoriesOfGender = (gender: GenderSlug): Category[] =>
  CATEGORIES.filter((c) => c.gender === gender);
