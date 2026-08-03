import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// content/articles/*.md を記事コレクションとして読む（生成物はこのディレクトリに出力される）。
// 事実データは products[] に構造化して持ち、レンダリング側がカードを描く。
const product = z.object({
  rank: z.number().nullish(),
  name: z.string(),
  price: z.number().nullish(),
  image: z.string().nullish(),
  url: z.string(),
  shop: z.string().nullish(),
  reviewAverage: z.number().nullish(),
  reviewCount: z.number().nullish(),
  priceBand: z.string().nullish(),
  pros: z.array(z.string()).nullish(),
  cons: z.string().nullish(),
  target: z.string().nullish(),
});

const articles = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './content/articles' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    updated: z.coerce.date().nullish(),
    description: z.string().nullish(),
    category: z.string().nullish(),
    categorySlug: z.string().nullish(),
    gender: z.enum(['men', 'women', 'unisex']).nullish(),
    intro: z.string().nullish(),
    outro: z.string().nullish(),
    noindex: z.boolean().nullish(),
    products: z.array(product).nullish(),
  }),
});

export const collections = { articles };
