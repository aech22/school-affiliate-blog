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

## 生成エンジン

`scripts/generate.py` ＋ `scripts/topics.json`（比較記事の定義）。**手動実行**（`ANTHROPIC_API_KEY` 必要）。`services.json` / `topics.json` を編集→実行で記事の講評文を再生成する（`date` は初回維持）。**編集主体なので日次 cron には載せない。**

## 残タスク

- [ ] ASP登録＋提携承認（A8 / afb / もしも推奨）→ `services.json` に `affiliateUrl` 記入＋`approved: true`
- [ ] `services.json` の seed 事実を一次情報で検証
- [ ] `public/ogp.png` 差し替え（今は gagetnavi / picknavi のまま）
- [ ] `topics.json` 拡充＋`generate.py` 実行で記事増
