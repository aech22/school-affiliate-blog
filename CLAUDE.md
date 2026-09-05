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
| workflow | `deploy.yml`（**人の push main で build+deploy**）と `generate.yml`（**日次cron。生成後に自分で build+deploy まで行う**） |

⚠️ **ドメインはハイフン入りの "code-navi"**（"codenavi" ではない）。

## 読者像とカテゴリ（2026-09-05 再定義）

**読者像は「働きながら学び直す／働き方を変えたい社会人」。** テーマを「スクール」に縛らず、この読者が実際に使うサービスなら A8 のカテゴリを問わず記事の土俵に載せる。逆に読者像から外れるものは、承認が取れても記事にしない（サイドバー広告に留める）。

判断ログ 2026-09-05「コドナビは総合化しない」の決定。**総合ブログにはしない。** URL・slug・ドメイン・サイト名は据え置き、定義はタグラインと about の文言で行う。

### A8 の17カテゴリの扱い

| 扱い | カテゴリ | 理由 |
|---|---|---|
| **受ける** | 仕事情報／学び・資格／Webサービス／インターネット接続／旅行（**留学・語学研修に限る**）／暮らし（**学習環境の道具に限る**） | 読者像に直結する。承認済み27件はすべてここに収まる |
| **禁止** | 健康 | AFFILIATE.md 禁止事項4（YMYL＋薬機法） |
| **見送り** | 美容／金融・投資・保険／不動産・引越／結婚・恋愛 | 美容は薬機法・医療広告ガイドラインを自動生成で守れない。金融は YMYL でトウシナビの領分。不動産は YMYL、引越は読者像外。結婚相談所は特定継続的役務。**ポリシー違反ではなく読者像との整合による判断なので、ユーザーが「載せる」と決めれば覆せる**（健康と金融は別途判断が要る） |
| **他サイトの領分** | 総合通販／グルメ・食品／ファッション／ギフト／スポーツ・趣味（picknavi）／エンタメ（ガジェナビ） | クラスタ分離の方針を崩さない |

### カテゴリ（4種・gender軸なし・slug は変えない）

`programming`（プログラミング・IT）/ `career`（転職・働き方）/ `qualification`（学び・スキル講座）/ `language`（語学・留学）

ラベルは 2026-09-05 に読者像へ合わせて広げた。**slug は変えていない**ので既存URLは全て生きている。カテゴリを増やすと記事0件の空ページが公開され、撤退時に404になるため増やさない（再着手条件は、ある分野の記事が既存カテゴリ内で5本以上になったとき、または楽天商品が20点以上に増えたとき）。

`taxonomy.ts` は `emoji` フィールドを持たない（2026-09-05 に削除）。ラベルの意味を絵文字で足せていなかったため。

## 見た目の決めごと（2026-09-05・個人ブログとして作り直した）

比較メディア風のカードUIをやめ、**働きながら学び直している人が書いている個人ブログ**として組み直した。正本は `src/styles/global.css` の `@theme` コメント。`kill-ai-slop` スキルの6原則に沿って決めている。

- **書体は2つだけ。** 見出し・記事タイトル・サイト名は明朝（Noto Serif JP 400/600）、本文とUIはゴシック（Noto Sans JP 400/500/700）。⚠️ `kill-ai-slop` のスキャナは `font-serif` を tell 07（serif-italic emphasis）として拾うが、これは体系的な意図で、装飾目的の書体切り替えではない（トリアージ済み）
- **太さは最大700。** `font-black`（900）は使わない
- **アクセントはブランドのオレンジ1色。** 文字に使うのは `brand-700`（コントラスト確保）、`brand-600` はボタンの地のみ。`brand-50`/`brand-100` の塗りつぶし面は作らない
- **角丸は `rounded-md`（6px）1種類。影は使わない。** 面の区切りは1pxの罫線（`border-ink/10`〜`/20`）だけ
- **グラデーション・ヒーローバナー・絵文字タイル・チップ型のピルは使わない。** トップは文章から始める
- **記事一覧はカードのグリッドではなく行のリスト。** `ArticleCard.astro` が1行を描く（`.article-card` と `data-category` はトップの絞り込みJSが見ているので必ず残す）
- **about の「書いている人」は運営者本人の自己紹介。** 文面は好みで書き換えてよい。ただし**記事の書き手について事実と違う主張（「実際に受講した」「毎日自分で書いている」等）を足さない**

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

**サイドバー（`Sidebar.astro`）に「広告」ラベル付きで7枠8本**（ステマ規制対応）:

| 広告 | サイズ | 文脈 |
|---|---|---|
| お名前.com | 120×600 | ドメイン取得 |
| ココナラ | 120×60 | 副業・スキル販売 |
| 社内SE転職ナビ | テキスト | エンジニア転職 |
| ユメキャリAgent | テキスト | 一般転職 |
| 動画教材エディター養成コース | テキスト | 動画編集 |
| 代理店ドットコム＋fan.salon | テキスト×2（1枠に同居） | 副業・独立（2026-08-06追加。枠数を増やしすぎないよう1セクションにまとめている） |
| なるには進学サイト | テキスト | 学び直しの進学先（2026-09-05追加。**資料請求ポータルで比較記事の土俵に載らないためサイドバーに置いた**） |

記事下の 728×90（お名前.com）は 2026-08-03 の `676855e` で「1ページ1広告」の方針により撤去済み。未使用のまま残っていた `AdBanner.astro` も 2026-09-05 に削除した。**記事ページの広告はサイドバーの6枠7本だけ**。

**A8 の広告コードは規約に従い原文のまま使う。** `&` を含むURLの JSX パースを避けるため `set:html` で挿入している。

### 承認済みサービス（`services.json` で `approved: true`）

- `se-navi`（社内SE転職ナビ）・`yumecari-agent`（ユメキャリ）— career カテゴリの比較カードで収益化済み
- 動画教材エディター養成コース・`creators-japan`・`movie-hacks`・`skillhacks` — qualification / programming カテゴリ
- **2026-08-06 追加（A8提供情報より）**: `onecareer-tenshoku`（ワンキャリア転職）・`r4career`（R4CAREER）＝career、`mystar`（MySTAR）・`estre`（エストレ）＝qualification、`nova`（駅前留学NOVA）・`shoba-chinese`（ショーバ中国語センター）＝language
- **2026-09-05 追加（A8提供情報15件）**: `anykan`・`groovement-agent`・`it-consultant-bank`・`strategy-consultant-bank`・`twinpro`・`buildjob`・`myvision`・`meiko-career`＝career、`merise`・`gaba`・`toraiz`・`wish-international`＝language、`daytra`＝programming、`cyber-university`・`amg`＝qualification。**全件 `officialUrl` は実在確認済みの公式サイト**（A8 URL を入れていない）
- これで承認済みは27件（career 12・qualification 7・language 6・programming 2）。**programming は skillhacks の1件だけだった状態から `daytra` が加わって2件**

## 事実台帳と検証ゲート（2026-09-02 追加）

`src/data/facts.json` が**検証済みの制度事実**（教育訓練給付金の給付率など）を持つ。
`scripts/gate.py` が生成本文から**金額（円・万円）と率（%）だけ**を抽出して検査する。

**金額も率も台帳（`numbers[]`）照合**で、無い値が本文に出たら破棄する。

⚠️ **台帳にある金額は「上限◯円」と、上限であることが分かる形で書かせる**（2026-09-05）。実際に受け取る額は受講する講座と本人の要件で変わるので、「◯円もらえる」と読める書き方をさせない。

⚠️ **台帳の数字から先の計算をさせない。** 自己負担額・実質価格・合計・差額・月あたりの額を自分で計算させない。**計算結果は台帳に無い数値なのでゲートが自動的に弾く**——つまり「台帳の値をそのまま書く」以外は通らない構造になっている。自己負担に触れるときは「実際の負担額は講座の受講料によって変わる」と書かせ、数字を出させない。

判定は `gate.check()` 一本で、`generate.py`（本文）も `replenish.py`（トピックのタイトル/テーマ）も同じ関数を通す。テストは `python3 scripts/test_gate.py`。

⚠️ **許可の根拠に `services.json` の `priceNote` を含めてはいけない。**
レジストリの値は一次情報で検証されておらず、初回実装ではこれが原因で是正対象の記述が素通りした。
料金は `ServiceCard` がレジストリから描画するので、本文が金額を書く必要はそもそも無い。

台帳に事実を足すときは**必ず一次情報のURLと `verifiedAt` を入れる**。90日を超えると生成時に警告が出る。

## 生成エンジン

`scripts/generate.py` ＋ `scripts/topics.json`（記事定義）＋ `scripts/queue.json`（待ち行列）。

- **1回の実行で `queue.json` の先頭1件だけ**を生成する（`ANTHROPIC_API_KEY` 必要）
- `.github/workflows/generate.yml` が**毎日 JST 10:00**（cron `0 1 * * *`・2026-09-05 に隔日から日次へ変更）に回す。生成→ゲート→main へ commit →**同じワークフロー内で build と deploy**まで行う
- ⚠️ **`deploy.yml`（`on: push`）は bot のコミットでは発火しない。** `GITHUB_TOKEN` の push は他のワークフローを起動しないという GitHub の仕様で、これを知らずに2ファイル構成にしていたため 09-03〜09-05 の記事2本が本番404のまま溜まった（`1658382` で是正）。共通正本 AFFILIATE.md のハマりどころ17番を参照
- 両ワークフローの `concurrency` は `pages-deploy` で共有し、gh-pages への同時デプロイを直列化している。peaceiris は force なしで push するので、競合すると後発が非 fast-forward で失敗する
- **金額・率は `facts.json` の `numbers[]` をプロンプトへ明示的に列挙して渡す**（`77f64b0`）。渡さないと台帳外の数値が創作されてゲートに落ちる（実例: `kyufu-taisho-kouza-sagashikata` の「1万円」）
- ゲートに落ちたらキューを進めず再試行。**3回連続で落ちたら `blocked: true` にして末尾へ送る**（無いと更新が静かに止まる）
- ⚠️ **日次なので `queue.json` の残り件数＝あと何日もつか。** 残り3件以下になると `scripts/replenish.py` が生成の前に走り、需要データからトピックを補充する（目標8件）

## キューの自動補充（2026-09-05 追加）

`scripts/replenish.py` が `generate.yml` の生成ステップ**より前**に走る。残りが `LOW_QUEUE_THRESHOLD`（3件）以下のときだけ動く。しきい値と目標件数の正本はこのファイルで、`generate.py` は `from replenish import LOW_QUEUE_THRESHOLD` で参照する（二重管理を避けるため）。

**需要データは Google サジェスト**（`suggestqueries.google.com`・UTF-8で返る）。`SEED_QUERIES` の種キーワードから実際に検索されている語を取り、それを根拠にトピックを提案させる。前回の手動補充（`1533cd3`）と同じやり方を自動化したもの。

`SEED_QUERIES` は**案件向けの語と楽天商品向けの語の両方**を持つ（2026-09-05）。楽天側の語（勉強デスク環境・オンライン面接カメラ・簿記3級テキスト等）を入れないと、`products.json` の道具に繋がる需要が一度も観測されず、補充が案件記事だけに偏る。

補充プロンプトはトピックを4つの型で作り分けさせる。①案件記事（`serviceIds`）②制度解説（`factIds`）③道具のエッセイ（`productIds`＝楽天）④アフィリリンクを持たないコラム（3つとも空）。4件以上提案させるときは、③と④を最低1件ずつ含めるよう指示している。**`compare` には `serviceIds` が必須**で、`productIds` だけの `compare` も弾く（生成側の compare プロンプトがサービスを並べる前提のため）。

⚠️ **このスクリプトは事実を増やさない。** 提案できるのは `facts.json` / `services.json` / `products.json` に**すでにある id** を参照するトピックだけで、`serviceIds` は `approved: true` の案件に限る。新しい制度事実が要るトピックは作らせない（台帳に一次情報未検証の値が入ると検証ゲートの許可集合が汚染され、ゲートそのものが意味を失うため）。**台帳へ事実を足すのは人間かセッションの仕事。**

⚠️ **サジェストが取れなければ何も足さずに警告して終わる。** サジェスト無しで作ったものは「需要データに基づく補充」ではないので、名前と中身を食い違わせない。検査を通る提案が0件のときも同じ。

構造検査は `validate()` が行い、`scripts/test_replenish.py` が17件のテストで固めている（CIで生成の前に走る）。検査項目は、slug の形式と重複、type と categorySlug の妥当性、参照 id の実在、`sourceQuery` が実際のサジェスト結果に含まれること、3種の id がすべて空でないこと、そして**タイトルとテーマに、そのトピック自身の `factIds` で裏付けられない金額・率が無いこと**。

⚠️ **ゲートはトークン照合なので、意味の違う同じ数字を見分けられない。** 2026-09-05 の動作確認で「70%が脱落する理由」というタイトルが提案された。台帳の `70%` は専門実践教育訓練の給付率で、脱落率とは無関係だが、トークンとしては一致するので本文ゲートは素通りする。だから**補充の入口**でタイトルとテーマを検査している（判定には `gate.py` をそのまま使う）。

### 動作確認のしかた

`.github/workflows/replenish-check.yml` を手動実行すると、本物のキーでサジェスト取得から構造検査までを通し、**ファイルを一切書かずに**「何が追加されるはずか」を出す。実行後に `git diff` で書き込みが無いことも機械的に確認する。

```bash
gh workflow run replenish-check.yml --repo aech22/school-affiliate-blog --ref main
```

ローカルでは `scripts/replenish.py` に2つのフラグ（書き込みを止めるものと、しきい値判定を飛ばすもの。`--help` 参照）を付けて同じことができる。ただし**ローカルの `.env` の `ANTHROPIC_API_KEY` は6文字の非ASCII文字列で実質プレースホルダー**なので LLM 呼び出しは失敗する（CIのシークレットは健全）。
- 記事の型は `type` で4種: `compare`（比較）/ `guide`（制度解説）/ `problem`（悩み起点）/ `essay`（場面起点のコラム）。型ごとにシステムプロンプトが違う
- **アフィリリンクを1本も持たない記事を作れる**（2026-09-05）。`serviceIds` / `factIds` / `productIds` がすべて空のトピックは、収益接点の無いコラムとして生成される。この場合プロンプトに「紹介する商品・サービスはない。存在しない商品名を出さず、購入や申し込みを促さない」と明示して渡す。**`compare` だけは比べる対象が無いと成立しないので従来どおり弾く**
- `date`（公開日）は `_existing_publish_date()` が維持する。**公開日を遡らせない**
- bot が main にコミットするので、ローカルから push する前に `git pull --rebase`

設計と実装計画: `docs/superpowers/specs/2026-09-02-需要起点リビルド-design.md` / `docs/superpowers/plans/2026-09-02-需要起点リビルド.md`

## 残タスク

- [ ] **programming カテゴリの提携申請**（下の「提携申請状況」表。**ユーザーが A8 管理画面で行う人間ステップ**。2026-09-05 に `daytra` が承認されて2件になったが、記事3本に対してはまだ薄い）
- [ ] 2026-09-05 追加15件の記事はキュー待ち（トピック7本を追加済み）。日次生成で順に公開される
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
