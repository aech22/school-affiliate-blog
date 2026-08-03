import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// content/articles/*.md を記事コレクションとして読む（生成物はこのディレクトリに出力される）。
// 事実データ（スクール名・料金・リンク等）は src/data/services.json に一元化し、記事は id で参照する。
// 記事frontmatterが持つのは「並び順(rank)とLLM講評(pros/cons/target/highlight)」だけ＝事実の二重管理を避ける。
const serviceRef = z.object({
  id: z.string(),                    // services.json の services[].id への結合キー
  rank: z.number().nullish(),
  pros: z.array(z.string()).nullish(),
  cons: z.string().nullish(),
  target: z.string().nullish(),
  highlight: z.string().nullish(),   // 価格帯やポジションの一言（例:「転職保証で選ぶなら」）
});

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './content/articles' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().nullish(),
    description: z.string().nullish(),
    category: z.string().nullish(),       // 表示ラベル（例: プログラミングスクール）
    categorySlug: z.string().nullish(),   // 結合キー（例: programming）
    intro: z.string().nullish(),
    outro: z.string().nullish(),
    noindex: z.boolean().nullish(),
    services: z.array(serviceRef).nullish(),
  }),
});

export const collections = { articles };
