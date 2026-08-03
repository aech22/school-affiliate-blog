# scripts/quality_check.py — 公開前の機械ゲート。CLI: python scripts/quality_check.py content/articles
# 新フォーマット（frontmatterに products 配列と講評文を持つ）に対応。
# 不合格が1件でもあれば非ゼロ終了で workflow を止める＝低品質記事を公開しない。
import sys
from pathlib import Path
import yaml

MIN_PROSE_CHARS = 450                       # intro+outro+各商品の講評 の合計下限（4商品比較の実測下限に合わせる）
BANNED = ["最安値", "絶対", "No.1", "ｎｏ.1", "日本一", "業界最安", "完全無料"]
AFFILIATE_HOST = "hb.afl.rakuten.co.jp"

def _prose_text(fm: dict) -> str:
    parts = [fm.get("intro", ""), fm.get("outro", "")]
    for p in fm.get("products", []) or []:
        parts += (p.get("pros") or [])
        parts += [p.get("cons", ""), p.get("target", "")]
    return " ".join(x for x in parts if x).strip()

def check(md: str) -> list:
    errors = []
    if not md.startswith("---"):
        return ["frontmatter が無い"]
    try:
        fm = yaml.safe_load(md.split("---", 2)[1]) or {}
    except Exception as e:
        return [f"frontmatter を YAML として解釈できない: {e}"]

    if not fm.get("title") or not fm.get("date"):
        errors.append("frontmatter に title / date が無い")

    if not fm.get("categorySlug"):
        errors.append("categorySlug が無い")
    if fm.get("gender") not in ("men", "women", "unisex"):
        errors.append(f"gender が不正（{fm.get('gender')!r}）")

    products = fm.get("products") or []
    if not products:
        errors.append("products が空")

    if not any(AFFILIATE_HOST in (p.get("url") or "") for p in products):
        errors.append(f"アフィリンク（{AFFILIATE_HOST}）が無い")

    noimg = [str(p.get("name", "?"))[:16] for p in products if not p.get("image")]
    if noimg:
        errors.append("商品画像が無い: " + ", ".join(noimg))

    prose = _prose_text(fm)
    if len(prose) < MIN_PROSE_CHARS:
        errors.append(f"講評文が短すぎる（{len(prose)}字 < {MIN_PROSE_CHARS}）")

    # 禁止語は「自社の編集文（タイトル＋講評）」だけを対象にする。
    # 商品名は楽天の実データ（例: 商品名に「No.1」を含む）で、こちらが変更できず事実表記なので対象外。
    editorial = (fm.get("title", "") or "") + " " + prose
    hit = [w for w in BANNED if w in editorial]
    if hit:
        errors.append("禁止語を含む: " + ", ".join(hit))
    return errors

def main(dir_path: str, prune: bool = False) -> None:
    """prune=False（ローカル/既定）: NGが1件でもあれば非ゼロ終了。
       prune=True（日次workflow）: NG記事だけ除外して他は公開し、全滅時のみ失敗。
       →1記事の講評が短い等でサイト全体の公開が止まるのを防ぐ。"""
    files = sorted(Path(dir_path).glob("*.md"))
    if not files:
        print(f"[WARN] {dir_path} に記事がありません")
    ok_count, ng = 0, []
    for path in files:
        errors = check(path.read_text(encoding="utf-8"))
        if errors:
            ng.append(path)
            print(f"[NG] {path.name}: {'; '.join(errors)}")
        else:
            ok_count += 1
            print(f"[OK] {path.name}")

    if prune:
        for path in ng:
            path.unlink()
            print(f"[PRUNED] {path.name} を今回の公開から除外（次回再生成で再挑戦）")
        if ok_count == 0:
            print("[FATAL] 公開可能な記事が0件のため中止")
            sys.exit(1)
        return
    if ng:
        sys.exit(1)   # 非ゼロ終了で workflow を止める（厳格モード）

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    prune = "--prune" in sys.argv
    main(args[0] if args else "content/articles", prune=prune)
