import fs from 'node:fs';
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// 独自ドメイン code-navi.net のルートで配信（base無し）。SEO・sitemap・OGP・canonical で使用。
// 内部リンクは import.meta.env.BASE_URL 方式のため、base 未設定時は BASE_URL='/' となり全リンクがルート相対で解決される（手戻りゼロ）。

// sitemap の <lastmod> 用に、記事の frontmatter から日付だけを拾う（2026-09-06）。
// Astro の Content Collections は設定ファイルからは読めないので、ここでは frontmatter を直接読む。
// lastmod が無いと、更新した記事も新規記事と同じ扱いで再クロールが遅れる。
// .md と .mdx の両方を拾う（AFFILIATE.md のハマりどころ16番）。
const ARTICLES_DIR = new URL('./content/articles/', import.meta.url);
function articleLastmod() {
  const map = new Map();
  if (!fs.existsSync(ARTICLES_DIR)) return map;
  // トップとカテゴリページは記事一覧なので、載っている記事のいちばん新しい日付を lastmod にする。
  // 2026-09-18 の実測で、Google の site: 検索に出るトップの title/description は 09-05 の
  // 作り直し前の文言のままだった（記事だけ lastmod があり、一覧ページには無かった）。
  const bump = (key, d) => {
    const cur = map.get(key);
    if (!cur || d > cur) map.set(key, d);
  };
  for (const file of fs.readdirSync(ARTICLES_DIR)) {
    if (!/\.mdx?$/.test(file)) continue;
    const raw = fs.readFileSync(new URL(file, ARTICLES_DIR), 'utf-8');
    const fm = raw.split('---')[1] ?? '';
    const pick = (key, pattern = '\\d{4}-\\d{2}-\\d{2}') => {
      const m = fm.match(new RegExp(`^${key}:\\s*['"]?(${pattern})`, 'm'));
      return m ? m[1] : null;
    };
    const date = pick('updated') ?? pick('date');
    if (!date) continue;
    const d = new Date(`${date}T00:00:00+09:00`);
    map.set(`/articles/${file.replace(/\.mdx?$/, '')}/`, d);
    bump('/', d);
    const category = pick('categorySlug', '[a-z0-9-]+');
    if (category) bump(`/categories/${category}/`, d);
  }
  return map;
}
const LASTMOD = articleLastmod();
const withLastmod = (item, path) => {
  const lastmod = LASTMOD.get(path);
  return lastmod ? { ...item, lastmod: lastmod.toISOString() } : item;
};

export default defineConfig({
  site: 'https://code-navi.net',
  integrations: [
    sitemap({
      // 404 はインデックス対象ではないので sitemap から外す。
      filter: (page) => !page.includes('/404'),
      changefreq: 'weekly',
      priority: 0.7,
      serialize(item) {
        const path = new URL(item.url).pathname;
        if (path === '/') {
          return withLastmod({ ...item, changefreq: 'daily', priority: 1.0 }, path);
        }
        if (path.startsWith('/articles/')) {
          return withLastmod({ ...item, changefreq: 'monthly', priority: 0.8 }, path);
        }
        if (path.startsWith('/categories/')) {
          return withLastmod({ ...item, changefreq: 'weekly', priority: 0.6 }, path);
        }
        // about / privacy などの固定ページ。
        return { ...item, changefreq: 'yearly', priority: 0.3 };
      },
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});
