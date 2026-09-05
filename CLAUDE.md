# CLAUDE.md — コドナビ

**⚠️ 作業前に共通正本を必ず読むこと:**
`/Users/hiroshi/Documents/Obsidian Vault/Projects/アフィリエイト/AFFILIATE.md`

技術スタック・デプロイ手順・禁止事項（**A8のURLをブラウザで開かない**等）・ハマりどころは全て共通正本にある。このファイルには**コドナビ固有の情報だけ**を書く。

---

## サイト固有情報

| 項目 | 内容 |
|---|---|
| ブランド | コドナビ（コード＋ナビ） |
| 本番URL | https://code-navi.net（独自ドメイン・ルート配信・HTTPS強制） |
| GitHub | `aech22/school-affiliate-blog`（public） |
| 収益モデル | 成果報酬（A8.net 等のASP） |
| workflow | `deploy.yml`（**人の push main で build+deploy**）と `generate.yml`（**隔日cron。生成後に自分で build+deploy まで行う**） |

⚠️ **ドメインはハイフン入りの "code-navi"**（"codenavi" ではない）。

## カテゴリ（4種・gender軸なし）

`programming`（プログラミングスクール）/ `career`（転職・エージェント）/ `qualification`（資格・スキル講座）/ `language`（語学スクール・2026-08-06追加）

当初はプログラミングスクール特化だったが、2026-08-03 に「スクール・転職・資格」の比較ハブへ拡張した。方針は**「分野を狭めるのは顧客を減らすのと同じ／購読者への条件が違うので重複関係なく掲載」**。

## 核心の設計（物販系との最大の違い）

商品APIが無いので、**案件レジストリ `src/data/services.json` が単一ソース**。Python（生成）と Astro（描画）の両方がこの JSON を読む（物販系の `config.py` / `taxonomy.ts` 二重管理を廃止した）。

```
Service = { id, name, subCategory, tags[], priceNote, target,
            officialUrl, affiliateUrl, asp, approved, pros[], cons[] }
```

記事 frontmatter は `services: [{id, rank, pros, cons, target, highlight}]` で **id 参照**（事実の二重管理を避ける）。事実は JSON・LLM は講評だけ。

### プレースホルダーリンク運用

`ServiceCard.astro` が `approved && affiliateUrl` なら `rel="sponsored"` でアフィリンク、未承認なら公式URLへ `rel="nofollow"`。**ASP提携の承認を待たずにサイトを完成・公開でき**、承認が取れたら `services.json` を編集するだけで自動切替される。

## A8 広告の掲載状況

**サイドバー（`Sidebar.astro`）に「広告」ラベル付きで6枠7本**（ステマ規制対応）:

| 広告 | サイズ | 文脈 |
|---|---|---|
| お名前.com | 120×600 | ドメイン取得 |
| ココナラ | 120×60 | 副業・スキル販売 |
| 社内SE転職ナビ | テキスト | エンジニア転職 |
| ユメキャリAgent | テキスト | 一般転職 |
| 動画教材エディター養成コース | テキスト | 動画編集 |
| 代理店ドットコム＋fan.salon | テキスト×2（1枠に同居） | 副業・独立（2026-08-06追加。枠数を増やしすぎないよう1セクションにまとめている） |

記事下の 728×90（お名前.com）は 2026-08-03 の `676855e` で「1ページ1広告」の方針により撤去済み。未使用のまま残っていた `AdBanner.astro` も 2026-09-05 に削除した。**記事ページの広告はサイドバーの6枠7本だけ**。

**A8 の広告コードは規約に従い原文のまま使う。** `&` を含むURLの JSX パースを避けるため `set:html` で挿入している。

### 承認済みサービス（`services.json` で `approved: true`）

- `se-navi`（社内SE転職ナビ）・`yumecari-agent`（ユメキャリ）— career カテゴリの比較カードで収益化済み
- 動画教材エディター養成コース・`creators-japan`・`movie-hacks`・`skillhacks` — qualification / programming カテゴリ
- **2026-08-06 追加（A8提供情報より）**: `onecareer-tenshoku`（ワンキャリア転職）・`r4career`（R4CAREER）＝career、`mystar`（MySTAR）・`estre`（エストレ）＝qualification、`nova`（駅前留学NOVA）・`shoba-chinese`（ショーバ中国語センター）＝language

## 事実台帳と検証ゲート（2026-09-02 追加）

`src/data/facts.json` が**検証済みの制度事実**（教育訓練給付金の給付率など）を持つ。
`scripts/gate.py` が生成本文から**金額（円・万円）と率（%）だけ**を抽出し、台帳の `numbers[]` に無い値が
含まれていたら記事を破棄する。テストは `python3 scripts/test_gate.py`。

⚠️ **許可の根拠に `services.json` の `priceNote` を含めてはいけない。**
レジストリの値は一次情報で検証されておらず、初回実装ではこれが原因で是正対象の記述が素通りした。
料金は `ServiceCard` がレジストリから描画するので、本文が金額を書く必要はそもそも無い。

台帳に事実を足すときは**必ず一次情報のURLと `verifiedAt` を入れる**。90日を超えると生成時に警告が出る。

## 生成エンジン

`scripts/generate.py` ＋ `scripts/topics.json`（記事定義）＋ `scripts/queue.json`（待ち行列）。

- **1回の実行で `queue.json` の先頭1件だけ**を生成する（`ANTHROPIC_API_KEY` 必要）
- `.github/workflows/generate.yml` が**隔日 JST 10:00**（cron `0 1 */2 * *`）に回す。生成→ゲート→main へ commit →**同じワークフロー内で build と deploy**まで行う
- ⚠️ **`deploy.yml`（`on: push`）は bot のコミットでは発火しない。** `GITHUB_TOKEN` の push は他のワークフローを起動しないという GitHub の仕様で、これを知らずに2ファイル構成にしていたため 09-03〜09-05 の記事2本が本番404のまま溜まった（`1658382` で是正）。共通正本 AFFILIATE.md のハマりどころ17番を参照
- 両ワークフローの `concurrency` は `pages-deploy` で共有し、gh-pages への同時デプロイを直列化している。peaceiris は force なしで push するので、競合すると後発が非 fast-forward で失敗する
- **金額・率は `facts.json` の `numbers[]` をプロンプトへ明示的に列挙して渡す**（`77f64b0`）。渡さないと台帳外の数値が創作されてゲートに落ちる（実例: `kyufu-taisho-kouza-sagashikata` の「1万円」）
- ゲートに落ちたらキューを進めず再試行。**3回連続で落ちたら `blocked: true` にして末尾へ送る**（無いと更新が静かに止まる）
- 記事の型は `type` で4種: `compare`（比較）/ `guide`（制度解説）/ `problem`（悩み起点）/ `essay`（楽天商品を差し込むエッセイ）。型ごとにシステムプロンプトが違う
- `date`（公開日）は `_existing_publish_date()` が維持する。**公開日を遡らせない**
- bot が main にコミットするので、ローカルから push する前に `git pull --rebase`

設計と実装計画: `docs/superpowers/specs/2026-09-02-需要起点リビルド-design.md` / `docs/superpowers/plans/2026-09-02-需要起点リビルド.md`

## 残タスク

- [ ] **programming カテゴリの提携申請**（下の「提携申請状況」表。**ユーザーが A8 管理画面で行う人間ステップ**）
- [ ] `estre` の `officialUrl` が A8 URL のまま（`estre-official.com` は TLS 設定が壊れていて実在確認ができなかった。2026-09-05 実測で `WRONG_VERSION_NUMBER`）
- [ ] Pinterest ドメイン認証（`PINTEREST_VERIFY` が空。認証コード取得は人間ステップ）
- [ ] `TWITTER_SITE` が空（X アカウント未連携）

## 提携申請状況（2026-09-05 新設）

`services.json` にフィールドを増やさず、ここで状態を管理する。承認が取れたら `affiliateUrl` と `approved` を `services.json` に反映する（手順は `affiliate-offer-intake` スキル）。

| id | サービス名 | カテゴリ | 状態 | 日付 | 備考 |
|---|---|---|---|---|---|
| `techacademy` | TechAcademy | programming | 未申請 | 2026-09-05 | |
| `codecamp` | CodeCamp | programming | 未申請 | 2026-09-05 | |
| `dmm-webcamp` | DMM WEBCAMP | programming | 未申請 | 2026-09-05 | |
| `runteq` | RUNTEQ | programming | 未申請 | 2026-09-05 | |
| `samurai-engineer` | 侍エンジニア | programming | 未申請 | 2026-09-05 | |
| `levtech-career` | レバテックキャリア | career | 未申請 | 2026-09-05 | |
| `green` | Green | career | 未申請 | 2026-09-05 | |

状態は「未申請 / 申請中 / 承認 / 却下 / A8に案件なし / 見送り」から選ぶ。**「見送り」にするときは理由と再着手条件を備考に書く。** A8 に案件が無い場合、他ASP（afb・もしも等）へ申請するかはユーザーの判断。

### 完了済み
- ~~`ANTHROPIC_API_KEY` を repo secret に登録~~ → 2026-09-02 登録済み
- ~~GA4 の測定ID~~ → `G-Y1PTFCM03C` が本番HTMLに出ており稼働中（`0751419`）
- ~~Search Console の所有権確認~~ → **HTMLファイル方式**で確認済み（`public/google5958bb822f03eeaa.html`・`c44ee1e`）。⚠️ **このファイルを消すと確認が外れる。** `consts.ts` の `SEARCH_CONSOLE_VERIFY`（metaタグ方式）は未使用のまま空でよい
- ~~`priceNote` の一次情報検証~~ → 2026-09-05 に video-editor-course / creators-japan / nova から金額を外した。数値を持つのは検証済みの mystar だけ
- ~~`officialUrl` の A8 URL~~ → 2026-09-05 に11件を公式サイトへ置換（estre のみ残タスク）
- ~~`public/ogp.png` 差し替え~~ → コドナビ専用OGP（1200×630）に差し替え済み（`ca8d249`）
- ~~楽天アフィリエイトの導入~~ → 2026-09-03 に稼働。`code-navi.net` を Rakuten Developers の許可リファラと楽天アフィリエイトのサイトに登録済みで、`src/data/products.json` の8商品が `approved:true`・`rel="sponsored"` で出ている

## 楽天アフィリエイト（2026-09-03 稼働）

`src/data/products.json` が商品レジストリ。**価格を持たない**（鮮度切れがそのまま景表法リスクになるため。金額は楽天側で見てもらう）。
記事型 `essay` が本文の主役で、`ProductMention.astro` がカード羅列ではない小さめのブロックで差し込む。

⚠️ **アフィリリンク（`hb.afl.rakuten.co.jp`）をブラウザやcurlで開かない。** 誤クリックが計上される。検証はHTMLのgrepのみ。

⚠️ **APIに `affiliateId` を渡すと `itemUrl` 自体がアフィリリンクに書き換わって返る。**
商品を突き合わせるときは `pc=` パラメータをデコードして実URLと比較する（`itemCode` の組み立ては機能しない）。
