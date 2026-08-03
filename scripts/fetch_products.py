# scripts/fetch_products.py
import argparse, json, os, time
import requests

RAKUTEN_APP_ID     = os.environ["RAKUTEN_APP_ID"]
RAKUTEN_ACCESS_KEY = os.environ["RAKUTEN_ACCESS_KEY"]
AFFILIATE_ID       = os.environ["RAKUTEN_AFFILIATE_ID"]
# 新APIは Referer と Origin の両方が必須（片方だけだと REQUEST_CONTEXT_BODY_HTTP_REFERRER_MISSING）。
# 登録した「Allowed websites」ドメインと一致させる。
RAKUTEN_REFERER    = os.environ.get("RAKUTEN_REFERER", "https://aech22.github.io/rakuten-affiliate-blog/")
RAKUTEN_ORIGIN     = os.environ.get("RAKUTEN_ORIGIN", "https://aech22.github.io")

# 新コンソール(Rakuten Developers)発行の UUID Application ID + Access Key に対応した
# 新エンドポイント(2026-07-01)。旧 app.rakuten.co.jp/services/api/...20220601 は
# UUID の applicationId を受け付けない（wrong_parameter）ため使わない。
ENDPOINT = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"

# 楽天API制限（1秒1リクエスト）を守るための最小間隔。
RATE_LIMIT_SEC = 1.0

def fetch_products(keyword: str, hits: int = 5) -> list:
    params = {
        "applicationId": RAKUTEN_APP_ID,
        "accessKey":     RAKUTEN_ACCESS_KEY,   # 新方式で必須（クエリ or ヘッダ）
        "affiliateId":   AFFILIATE_ID,         # 付けると affiliateUrl が返る
        "keyword":       keyword,
        "hits":          hits,
        "sort":          "-reviewCount",        # レビュー数降順（人気順）
        "imageFlag":     1,
        "formatVersion": 2,                     # items[] の各要素が商品dict直下になる新形式
    }
    if not RAKUTEN_ACCESS_KEY:
        raise SystemExit("RAKUTEN_ACCESS_KEY が空です。.env に Access Key(pk_...) を入れてください。")

    headers = {"Referer": RAKUTEN_REFERER, "Origin": RAKUTEN_ORIGIN}  # 両方必須
    res = requests.get(ENDPOINT, params=params, headers=headers)
    if res.status_code != 200:
        # 楽天APIのエラー本文（errors.errorMessage）をそのまま表示して切り分けしやすくする
        raise SystemExit(f"Rakuten API {res.status_code}: {res.text}")
    time.sleep(RATE_LIMIT_SEC)                  # レート制御（1req/秒）
    # 実レスポンスは {"Items": [ {itemName, itemPrice, affiliateUrl, mediumImageUrls, ...}, ... ]}
    # 形式差（Items/items・Item入れ子の有無）を吸収して商品dictのリストを返す
    data = res.json()
    items = data.get("Items") or data.get("items") or []
    return [it.get("Item", it) for it in items]

# CLI: python scripts/fetch_products.py --keyword "..." --hits 3 --output products.json
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--hits", type=int, default=5)
    ap.add_argument("--output", default="products.json")
    args = ap.parse_args()

    products = fetch_products(args.keyword, args.hits)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(products)} products -> {args.output}")
