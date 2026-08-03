# scripts/post_to_x.py
# 新しく追加された記事だけを X(Twitter) に自動投稿する。
# X APIキー（4つの環境変数）が未設定なら何もせず終了する＝完全オプトイン。
# 既投稿は scripts/posted_x.json に slug を記録し、再投稿しない（＝毎日の価格更新では投稿しない）。
from __future__ import annotations
import json, os, sys
from pathlib import Path
import yaml

SITE = "https://aech22.github.io/gadget-affiliate-blog"
ART_DIR = Path(__file__).resolve().parent.parent / "content" / "articles"
STATE = Path(__file__).resolve().parent / "posted_x.json"
MAX_PER_RUN = 3   # 1回の実行での最大投稿数（過去記事の一気投稿＝スパム化を防ぐ）

CRED_KEYS = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"]

def main() -> None:
    if not all(os.environ.get(k) for k in CRED_KEYS):
        print("X APIキーが未設定のためスキップ（オプトイン機能）")
        return
    try:
        import tweepy
    except ImportError:
        print("tweepy 未インストールのためスキップ")
        return

    posted = set(json.loads(STATE.read_text(encoding="utf-8"))) if STATE.exists() else set()
    queue = []
    for p in sorted(ART_DIR.glob("*.md")):
        slug = p.stem
        if slug in posted:
            continue
        try:
            fm = yaml.safe_load(p.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        except Exception:
            continue
        queue.append((slug, fm.get("title", slug), fm.get("category", "")))

    if not queue:
        print("新規記事なし（投稿なし）")
        return

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"], consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"], access_token_secret=os.environ["X_ACCESS_SECRET"],
    )
    posted_now = 0
    for slug, title, cat in queue[:MAX_PER_RUN]:
        url = f"{SITE}/articles/{slug}/"
        tag = f"【{cat}】" if cat else ""
        text = f"{tag}{title}\n楽天で売れている商品を写真・価格・レビューで比較しました👇\n{url}\n#おすすめ #比較"
        try:
            client.create_tweet(text=text[:275])
            posted.add(slug); posted_now += 1
            print(f"posted: {slug}")
        except Exception as e:
            print(f"post失敗: {slug}: {type(e).__name__}: {e}")

    STATE.write_text(json.dumps(sorted(posted), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"done: {posted_now}件投稿・残り{max(0, len(queue) - posted_now)}件は次回")

if __name__ == "__main__":
    main()
