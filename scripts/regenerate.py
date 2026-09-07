# scripts/regenerate.py — 公開済み記事を現在のプロンプトで書き直す（手動実行）
#
# なぜ要るか:
#   generate.py は queue.json から1日1本だけ生成する。生成プロンプト（BODY_RULES 等）を
#   変えても、既に公開されている記事は古い文体のまま残り続ける。文体の基準を変えたときに
#   既存記事を追随させる手段がこれ。
#
# 使い方:
#   python3 scripts/regenerate.py            # content/articles にある全記事を作り直す
#   python3 scripts/regenerate.py <slug> ... # 指定した slug だけ
#   python3 scripts/regenerate.py --dry-run  # 対象を数えるだけ（LLMを呼ばない）
#
# 安全策:
#   - date（公開日）は generate.build_topic が既存記事から引き継ぐので遡らない。
#   - ゲート（gate.py）に落ちた記事は**上書きせず既存のまま残す**。台帳外の数値が入った
#     文章で公開済みの記事を壊さないため。落ちた slug は最後にまとめて出す。
#   - queue.json は触らない（未生成分の待ち行列とは無関係）。
from __future__ import annotations
import datetime, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate as G

JST = datetime.timezone(datetime.timedelta(hours=9))


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv[1:]
    today = datetime.datetime.now(JST).date().isoformat()

    by_slug = {t["slug"]: t for t in G.TOPICS}
    existing = sorted(p.stem for p in G.OUT_DIR.glob("*.md"))
    targets = args or existing

    missing = [s for s in targets if s not in by_slug]
    todo = [s for s in targets if s in by_slug]
    if missing:
        print(f"[SKIP] topics.json に定義が無い slug: {missing}")
    print(f"対象 {len(todo)} 本（公開済み {len(existing)} 本 / topics.json {len(by_slug)} 件）")
    if dry:
        return

    ok, gated, failed = [], [], []
    for i, slug in enumerate(todo, 1):
        try:
            fm, body, violations = G.build_topic(by_slug[slug], today)
        except Exception as e:
            failed.append((slug, f"{type(e).__name__}: {e}"))
            print(f"[{i}/{len(todo)}] ERROR {slug}: {type(e).__name__}: {e}")
            continue
        if violations:
            gated.append((slug, violations))
            print(f"[{i}/{len(todo)}] GATE  {slug}: 未検証の数値 {violations} → 既存のまま残す")
            continue
        if not fm:
            failed.append((slug, "生成対象なし"))
            print(f"[{i}/{len(todo)}] SKIP  {slug}: 生成対象なし")
            continue
        (G.OUT_DIR / f"{slug}.md").write_text(G.to_markdown(fm, body), encoding="utf-8")
        ok.append(slug)
        print(f"[{i}/{len(todo)}] ok    {slug}（本文{len(body)}字）")

    print(f"\n書き直し {len(ok)} 本 / ゲート落ち {len(gated)} 本 / 失敗 {len(failed)} 本")
    for slug, v in gated:
        print(f"  GATE {slug}: {v}")
    for slug, e in failed:
        print(f"  FAIL {slug}: {e}")


if __name__ == "__main__":
    main()
