import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// 独自ドメイン code-navi.net のルートで配信（base無し）。SEO・sitemap・OGP・canonical で使用。
// 内部リンクは import.meta.env.BASE_URL 方式のため、base 未設定時は BASE_URL='/' となり全リンクがルート相対で解決される（手戻りゼロ）。
export default defineConfig({
  site: 'https://code-navi.net',
  integrations: [sitemap({ changefreq: 'weekly', priority: 0.7 })],
  vite: {
    plugins: [tailwindcss()],
  },
});
