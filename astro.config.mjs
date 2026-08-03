import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// 独自ドメイン gagetnavi.net のルートで配信（base無し）。SEO・sitemap・OGP・canonical で使用。
// 内部リンクは import.meta.env.BASE_URL 方式のため、base 未設定時は BASE_URL='/' となり全リンクがルート相対で解決される。
export default defineConfig({
  site: 'https://gagetnavi.net',
  integrations: [sitemap({ changefreq: 'weekly', priority: 0.7 })],
  vite: {
    plugins: [tailwindcss()],
  },
});
