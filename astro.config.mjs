import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';

// GitHub Pages のプロジェクトサイト（https://aech22.github.io/school-affiliate-blog/）で配信。
// SEO・sitemap・OGP・canonical に site+base を使用。
// 内部リンクは import.meta.env.BASE_URL 方式のため、base='/school-affiliate-blog/' が全リンクに前置される。
export default defineConfig({
  site: 'https://aech22.github.io',
  base: '/school-affiliate-blog/',
  integrations: [sitemap({ changefreq: 'weekly', priority: 0.7 })],
  vite: {
    plugins: [tailwindcss()],
  },
});
