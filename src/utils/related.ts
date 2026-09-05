// 関連記事の選定（2026-09-06）。
//
// 記事どうしを内部リンクで繋ぐための並べ替え。記事末に置く数本を機械的に選ぶ。
// LLM にリンク先を書かせると存在しない slug を書きうるので、frontmatter の結合キーだけで決める。
//
// スコアは「同じ案件・同じ道具を扱っている」を最優先にする。教育訓練給付金の記事群のように
// 同じ制度を別角度から書いた記事が互いに繋がり、話題のまとまりが検索エンジンに伝わる。
// 該当が無くても新着で埋めて必ず本数を返す（リンクの無い行き止まりページを作らないため）。
import type { CollectionEntry } from 'astro:content';

type Article = CollectionEntry<'articles'>;

const SCORE_SHARED_SERVICE = 3;
const SCORE_SHARED_PRODUCT = 3;
const SCORE_SAME_CATEGORY = 2;
const SCORE_SAME_TYPE = 1;

export function relatedArticles(all: Article[], current: Article, limit = 4): Article[] {
  const cur = current.data;
  const curServices = new Set((cur.services ?? []).map((s) => s.id));
  const curProducts = new Set(cur.products ?? []);

  return all
    .filter((a) => a.id !== current.id)
    .map((a) => {
      const d = a.data;
      let score = 0;
      for (const s of d.services ?? []) if (curServices.has(s.id)) score += SCORE_SHARED_SERVICE;
      for (const p of d.products ?? []) if (curProducts.has(p)) score += SCORE_SHARED_PRODUCT;
      if (d.categorySlug && d.categorySlug === cur.categorySlug) score += SCORE_SAME_CATEGORY;
      if (d.type && d.type === cur.type) score += SCORE_SAME_TYPE;
      return { a, score };
    })
    .sort((x, y) => y.score - x.score || y.a.data.date.valueOf() - x.a.data.date.valueOf())
    .slice(0, limit)
    .map((x) => x.a);
}
