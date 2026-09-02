// サイト共通の設定。外部サービスの「あなたのコード」をここに貼るだけで有効化される。
// いずれも空文字なら無効（タグを出力しない＝計測もしない）。

// ブランド名・キャッチコピー（ここ1箇所を変えれば全テンプレートに反映される）。
export const SITE_NAME = 'コドナビ';
export const SITE_TAGLINE = 'スクール・転職・資格を、料金と特徴で比較。エンジニアとキャリアの「次の一歩」を選ぶ。';

// Google Analytics 4 の測定ID（例: 'G-XXXXXXXXXX'）。このサイト用に新規発行したIDを貼る。
export const GA_MEASUREMENT_ID = '';

// Pinterest ドメイン認証コード（Pinterestの「ドメインを申請」で表示される <meta> の content 値）。
export const PINTEREST_VERIFY = '';

// Google Search Console のHTMLタグ確認コード（<meta name="google-site-verification" content="◯◯◯"> の content値）。
// 空文字ならタグを出力しない。所有権の確認が済んだあとも消さないこと（消すと確認が外れる）。
export const SEARCH_CONSOLE_VERIFY = '';

// X(Twitter) の公式アカウント（例: '@handle'）。カード下部に表示される。
export const TWITTER_SITE = '';

// Shifty 導線（ShiftyPromo.astro）の流入元計測用スラッグ。サイトごとに一意にする。
export const SHIFTY_UTM_SOURCE = 'codenavi';
