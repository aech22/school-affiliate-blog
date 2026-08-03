# rakuten-affiliate-blog

楽天商品レビュー記事を Claude API で自動生成し、Astro で静的サイト化して GitHub Pages に自動公開するシステム。
計画書: Obsidian `Projects/楽天アフィリエイト/計画書.md`。

## 構成

- 記事生成: Python（`scripts/`）— 楽天商品検索API → Claude Haiku → Markdown
- 公開前ゲート: `scripts/quality_check.py`（機械チェック・人手レビューなし。不合格でCI失敗＝公開しない）
- サイト: Astro + Tailwind（`src/`, `content/articles/`）
- 自動化: GitHub Actions（毎日実行＝価格・在庫を24時間以内に更新）→ GitHub Pages

## ローカルでの動かし方

```bash
# Python（記事生成・ゲート）
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 実値を入れる（.env は gitignore 済み）

# サイト（雛形の確認・ビルド）
npm install
npm run dev     # http://localhost:4321
npm run build   # dist/ に静的サイト生成
```

生成〜ゲートの単体確認:

```bash
python scripts/fetch_products.py --keyword "コーヒーメーカー" --hits 3 --output products.json
python scripts/generate_article.py --input products.json --theme "コーヒーメーカー比較" --output content/articles/test.md
python scripts/quality_check.py content/articles     # [OK] なら合格
python -m unittest discover -s tests                 # ゲートの純粋関数テスト
```

## 🔴 あなたにしかできない設定（着手前に必要）

Claude は以下を代行できません（アカウント作成・秘密情報の入力のため）。

- [ ] **楽天市場アカウント** を作成
- [ ] **楽天アフィリエイト** (https://affiliate.rakuten.co.jp/) に申請し `affiliateId` を取得
- [ ] **楽天デベロッパー** (https://webservice.rakuten.co.jp/) でアプリ登録し `applicationId` を取得
- [ ] **Anthropic APIキー** を取得（`ANTHROPIC_API_KEY`）
- [ ] `.env` に4つの値を設定（ローカル実行用）: `RAKUTEN_APP_ID`（UUID）/ `RAKUTEN_ACCESS_KEY`（`pk_...`・機密）/ `RAKUTEN_AFFILIATE_ID` / `ANTHROPIC_API_KEY`
- [ ] GitHub にこのリポジトリを push し、**Settings → Secrets and variables → Actions** に
      `RAKUTEN_APP_ID` / `RAKUTEN_ACCESS_KEY` / `RAKUTEN_AFFILIATE_ID` / `ANTHROPIC_API_KEY` を登録

> ※ 楽天API は新方式（Rakuten Developers コンソール）。実測で判明した要件:
> - エンドポイント: `openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701`（旧 `app.rakuten.co.jp/...20220601` は UUID Application ID を受け付けない）
> - 認証: `applicationId`(UUID) + `accessKey`(pk_) をクエリで送る
> - **必須ヘッダ: `Referer` と `Origin` の両方**（登録した Allowed websites ドメインと一致。片方だけだと 403 `REFERRER_MISSING`）
> - レスポンスは `Items`（大文字）配列でフラット構造。`affiliateUrl` は `hb.afl.rakuten.co.jp` 形式で品質ゲートと整合
- [ ] **Settings → Pages** で公開ソースを `gh-pages` ブランチに設定
- [ ] `astro.config.mjs` の `site` を公開URLに変更（sitemap・OGP用）

設定後、Actions の **workflow_dispatch（手動実行）** で1回まわして公開確認 → 以降は毎日自動実行。

> ⚠️ 楽天の審査日数・レート上限・キャッシュ期間は変わり得る。着手前に公式ドキュメントで現行値を確認すること。

## ブランチ運用と乗り換え条件

- `main` = 本番（GitHub Actions が公開）。開発はローカルの `npm run dev` で確認してから push。
- 本構成は「コンテンツ主体・SEO重視」のため Astro（静的サイトの王道）を採用。
- **乗り換え条件**: 動的機能（ユーザー投稿・ログイン・DB連携）が本質的に必要になったら、王道スタック（Next.js + Firebase 等）への移行を検討する。
