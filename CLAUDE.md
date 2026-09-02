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
| workflow | `.github/workflows/deploy.yml`（**push main で build+deploy**・シークレット不要） |

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

`AdBanner.astro` は記事下の お名前.com 728×90。

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
- `.github/workflows/generate.yml` が**隔日 JST 10:00**（cron `0 1 */2 * *`）に回す。生成→ゲート→main へ commit → `deploy.yml` が公開
- ゲートに落ちたらキューを進めず再試行。**3回連続で落ちたら `blocked: true` にして末尾へ送る**（無いと更新が静かに止まる）
- 記事の型は `type` で3種: `compare`（比較）/ `guide`（制度解説）/ `problem`（悩み起点）。型ごとにシステムプロンプトが違う
- `date`（公開日）は `_existing_publish_date()` が維持する。**公開日を遡らせない**
- bot が main にコミットするので、ローカルから push する前に `git pull --rebase`

設計と実装計画: `docs/superpowers/specs/2026-09-02-需要起点リビルド-design.md` / `docs/superpowers/plans/2026-09-02-需要起点リビルド.md`

## 残タスク

- [ ] **`ANTHROPIC_API_KEY` を repo secret に登録**（人間ステップ。これが無いと隔日生成が動かない）
- [ ] **GA4 の測定ID発行 → `consts.ts` の `GA_MEASUREMENT_ID` に貼る**（現在このサイトは**未計測**。何が読まれたかの記録が無い）
- [ ] **Search Console の所有権確認**（`consts.ts` に `SEARCH_CONSOLE_VERIFY` の定義自体が無い。検索クエリが取れないとキーワード補充が勘になる）
- [ ] programming カテゴリの提携承認（承認は6件中1件のみ。記事3本あるのに収益接点が薄い）
- [ ] `services.json` の priceNote の一次情報検証（mystar のみ 2026-09-02 に検証・是正済み。**数値を含む残り3件 video-editor-course / creators-japan / nova は未検証のまま本番表示中**）
- [ ] `officialUrl` に A8 URL が入っている12件を本当の公式URLへ（**全件 approved なので現状の描画は正しいが**、どれかが `approved: false` になると A8 URL へ `rel="nofollow"` でフォールバックする潜在バグ）

### 完了済み
- ~~`public/ogp.png` 差し替え~~ → コドナビ専用OGP（1200×630）に差し替え済み（`ca8d249`）
