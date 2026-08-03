# scripts/generate_article.py
# 事実データ（商品名・価格・画像・アフィリンク・レビュー）は楽天APIの値をそのまま使い、
# LLM(Haiku)には「講評文（intro/outro/長所/短所/向き不向き）」だけを JSON で書かせる。
# → 価格やURLのLLM誤記が構造的に起きない。画像・商品名リンクはレンダリング側が構造データから描く。
import argparse, json, re
import anthropic
import yaml

client = anthropic.Anthropic()

# 楽天のサムネイルURLは末尾に ?_ex=128x128 のようなサイズ指定が付く。カード表示用に拡大する。
def _upscale_image(url: str, size: int = 400) -> str:
    if not url:
        return ""
    return re.sub(r"_ex=\d+x\d+", f"_ex={size}x{size}", url)

def _first_image(p: dict) -> str:
    imgs = p.get("mediumImageUrls") or p.get("smallImageUrls") or []
    if imgs and isinstance(imgs[0], dict):      # formatVersion=1 の {imageUrl} 形式フォールバック
        imgs = [x.get("imageUrl", "") for x in imgs]
    return _upscale_image(imgs[0]) if imgs else ""

SYSTEM_PROMPT = """あなたは日本語のアフィリエイト比較記事のライターです。
与えられた商品データ（実在の楽天商品）をもとに、読者目線の正直な比較記事の「文章部分」だけをJSONで返します。

厳守ルール:
- 誇大表現・根拠のない最上級表現を使わない（「最安値」「絶対」「No.1」「日本一」「業界最安」等は禁止）。楽天アフィリエイトの規約に沿う。
- 価格・商品名・URL・レビュー数などの事実は書かない（それらはシステム側が別途埋め込む）。あなたは講評・特徴・向き不向きの文章だけ書く。
- pros は各商品の spec や用途から自然に言える具体的な長所を3つ（各30〜55字程度・内容を薄くしない）。
- cons は正直な短所や購入前の注意点を1〜2文で具体的に。target は「こんな人に向いている」を1文で具体的に。priceBand は価格帯の一言（例:「手頃価格」「中価格帯」「高価格帯」）。
- intro は記事全体の導入(3〜4文)。outro はまとめ(3〜4文・選び方の指針)。
- 出力は JSON のみ。コードフェンス(```)で囲まない。前置き・後書きを付けない。

出力JSONスキーマ（items の要素数と順序は入力の商品と必ず一致させる）:
{"title":"SEOを意識した30字前後の記事タイトル","description":"100字程度の要約","intro":"...","outro":"...","items":[{"pros":["...","...","..."],"cons":"...","target":"...","priceBand":"..."}]}"""

def _extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        nl = t.find("\n")
        t = t[nl + 1:] if nl != -1 else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    i, j = t.find("{"), t.rfind("}")
    if i != -1 and j != -1:
        t = t[i:j + 1]
    return json.loads(t)

def _llm_prose(products: list, theme: str) -> dict:
    brief = [{
        "name":    p.get("itemName", ""),
        "caption": (p.get("itemCaption") or "")[:300],
        "shop":    p.get("shopName", ""),
    } for p in products]
    user = (f"テーマ: {theme}\n"
            f"商品データ(順序厳守・{len(brief)}件):\n"
            f"{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
            f"上記スキーマのJSONだけを返してください。")
    last_err = None
    for attempt in range(2):
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",   # コスト最適化（事実はAPI値を使うのでHaikuで十分）
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user",
                       "content": user if attempt == 0 else user + "\n\n前回JSONとして解釈できませんでした。有効なJSONオブジェクトのみを返してください。"}],
        )
        try:
            return _extract_json(msg.content[0].text)
        except Exception as e:
            last_err = e
    raise ValueError(f"LLM出力をJSONとして解釈できませんでした: {last_err}")

def build_article(products: list, theme: str, date_str: str, category: str,
                  category_slug: str = "", gender: str = "unisex", updated_str: str = "") -> dict:
    """楽天APIの事実データ + LLMの講評文 を1記事分の frontmatter dict にまとめる。"""
    prose = _llm_prose(products, theme)
    items = prose.get("items", [])
    out_products = []
    for i, p in enumerate(products):
        it = items[i] if i < len(items) else {}
        prod = {
            "rank":          i + 1,
            "name":          p.get("itemName", ""),
            "price":         p.get("itemPrice"),
            "image":         _first_image(p),
            "url":           p.get("affiliateUrl") or p.get("itemUrl", ""),
            "shop":          p.get("shopName", ""),
            "reviewAverage": p.get("reviewAverage"),
            "reviewCount":   p.get("reviewCount"),
            "priceBand":     it.get("priceBand", ""),
            "pros":          (it.get("pros") or [])[:3],
            "cons":          it.get("cons", ""),
            "target":        it.get("target", ""),
        }
        out_products.append({k: v for k, v in prod.items() if v not in (None, "", [])})
    fm = {
        "title":        prose.get("title") or theme,
        "date":         date_str,                    # 公開日（固定URLでは初回のみ確定し以降維持）
        "updated":      updated_str or date_str,     # 最終更新日（毎日の再生成で更新）
        "description":  prose.get("description", ""),
        "category":     category,                    # 表示ラベル（例: メンズファッション）
        "categorySlug": category_slug,               # 結合キー（例: mens-fashion）
        "gender":       gender,                      # men | women | unisex
        "intro":        prose.get("intro", ""),
        "outro":        prose.get("outro", ""),
        "products":     out_products,
    }
    return {k: v for k, v in fm.items() if v not in (None, "")}

def to_markdown(fm: dict) -> str:
    """frontmatter dict を Astro が読める Markdown（frontmatterのみ・本文なし）へ。"""
    y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=100000)
    return f"---\n{y}---\n"

# CLI（単体テスト用）: python scripts/generate_article.py --input products.json --theme "..." --output out.md
if __name__ == "__main__":
    import datetime
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="fetch_products.py が出力した products.json")
    ap.add_argument("--theme", default="おすすめ商品比較")
    ap.add_argument("--category", default="")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    with open(args.input, encoding="utf-8") as f:
        products = json.load(f)
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
    fm = build_article(products, args.theme, today, args.category or args.theme)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(to_markdown(fm))
    print(f"wrote article -> {args.output}")
