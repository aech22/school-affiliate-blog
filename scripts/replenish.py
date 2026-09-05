#!/usr/bin/env python3
"""scripts/replenish.py — キューが少なくなったら実需要からトピックを補充する。

設計の要（変える前に読むこと）:

1. **事実を増やさない。** 提案できるのは facts.json / services.json / products.json に
   すでにある id を参照するトピックだけ。新しい制度事実を必要とするトピックは作らせない。
   台帳に一次情報未検証の値が入ると、scripts/gate.py の許可集合が汚染されて
   検証ゲートそのものが意味を失うため（CLAUDE.md「事実台帳と検証ゲート」）。
   台帳へ事実を足すのは、一次情報を確認できる人間またはセッションの仕事。

2. **需要データが取れなければ何もしない。** Google サジェストの取得に失敗したら、
   トピックを創作せずに警告だけ出して終わる。サジェスト無しで作ったものは
   「需要データに基づく補充」ではないので、名前と中身を食い違わせない。

3. **収益接点のあるトピックだけ。** serviceIds は approved:true の案件に限る
   （前回の手動補充 1533cd3 と同じ基準）。

出典: 2026-09-02 の手動補充（1533cd3）が Google サジェストで実需要を取り、
承認済み案件に接続できるトピックだけを選んだ。その手順を自動化したもの。
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS_PATH = ROOT / "scripts" / "topics.json"
QUEUE_PATH = ROOT / "scripts" / "queue.json"

# 残りがこの件数以下になったら補充する。日次実行なので件数＝残り日数。
# scripts/generate.py はこの値を import して警告のしきい値に使う（二重管理を避ける）。
LOW_QUEUE_THRESHOLD = 3
# 補充後に目指す件数。前回の手動補充（1533cd3）と同じ8件＝約1週間ぶん。
TARGET_QUEUE = 8

VALID_TYPES = {"compare", "guide", "problem", "essay"}

# サジェストを引く種キーワード。カテゴリごとに、記事化して収益接点に繋がる語を置く。
# ここを増やせば提案の幅が広がる。減らせば絞られる。
SEED_QUERIES = {
    "qualification": ["教育訓練給付金", "リスキリング 補助金", "動画編集 スクール", "資格 独学"],
    "career": ["社内SE 転職", "転職エージェント 20代", "未経験 転職 IT"],
    "programming": ["プログラミングスクール 比較", "プログラミング 独学 挫折"],
    "language": ["英会話スクール 比較", "中国語 教室"],
}

CATEGORY_LABEL = {
    "qualification": "資格・スキル講座",
    "career": "転職・エージェント",
    "programming": "プログラミングスクール",
    "language": "語学スクール",
}

SYSTEM = """あなたは日本語のアフィリエイトメディアの編集者です。
検索需要（Googleサジェストの実データ）から、記事化する価値のあるトピックを設計します。
出力は JSON のみ。コードフェンスも前置きも付けません。"""


def fetch_suggests(query: str, timeout: int = 15) -> list[str]:
    """Google サジェストを引く。失敗したら空リストを返す（例外を投げない）。"""
    url = ("https://suggestqueries.google.com/complete/search"
           f"?client=firefox&hl=ja&q={urllib.parse.quote(query)}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=timeout).read()
        data = json.loads(raw.decode("utf-8"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception as e:  # ネットワーク・形式変更・ブロックのいずれも同じ扱い
        print(f"[WARN] サジェスト取得に失敗: {query}: {type(e).__name__}: {e}")
        return []


def collect_demand() -> dict[str, list[str]]:
    """カテゴリごとに実需要のクエリを集める。"""
    demand: dict[str, list[str]] = {}
    for cat, seeds in SEED_QUERIES.items():
        found: list[str] = []
        for seed in seeds:
            for s in fetch_suggests(seed):
                if s not in found:
                    found.append(s)
        demand[cat] = found
    return demand


def _slugify_ok(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug or ""))


def validate(cand: dict, allowed: dict, existing_slugs: set[str],
             demand_all: set[str]) -> str | None:
    """構造検査。問題があれば理由の文字列を返す。合格なら None。"""
    for key in ("slug", "type", "title", "categorySlug", "theme", "sourceQuery"):
        if not cand.get(key):
            return f"{key} が空"
    if not _slugify_ok(cand["slug"]):
        return f"slug の形式が不正: {cand['slug']}"
    if cand["slug"] in existing_slugs:
        return f"slug が既存と重複: {cand['slug']}"
    if cand["type"] not in VALID_TYPES:
        return f"type が不正: {cand['type']}"
    if cand["categorySlug"] not in CATEGORY_LABEL:
        return f"categorySlug が不正: {cand['categorySlug']}"
    if cand["sourceQuery"] not in demand_all:
        # 需要データに無いクエリを根拠にしたら、それは創作であって実需要ではない
        return f"sourceQuery がサジェスト結果に無い: {cand['sourceQuery']}"
    for field, pool in (("factIds", allowed["facts"]),
                        ("serviceIds", allowed["services"]),
                        ("productIds", allowed["products"])):
        for i in cand.get(field) or []:
            if i not in pool:
                return f"{field} に存在しない id: {i}"
    if not any(cand.get(f) for f in ("factIds", "serviceIds", "productIds")):
        return "factIds / serviceIds / productIds がすべて空（generate.py が生成できない）"
    return None


def main() -> int:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    pending = queue["pending"]
    remaining = len([x for x in pending if not x.get("blocked")])
    if remaining > LOW_QUEUE_THRESHOLD:
        print(f"キューは{remaining}件。しきい値{LOW_QUEUE_THRESHOLD}件を上回っているので補充しません。")
        return 0

    topics_doc = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    topics = topics_doc["topics"]
    existing_slugs = {t["slug"] for t in topics}

    facts = json.loads((ROOT / "src" / "data" / "facts.json").read_text(encoding="utf-8"))["facts"]
    services = json.loads((ROOT / "src" / "data" / "services.json").read_text(encoding="utf-8"))["services"]
    products = json.loads((ROOT / "src" / "data" / "products.json").read_text(encoding="utf-8"))["products"]
    allowed = {
        "facts": {f["id"] for f in facts},
        # 承認済み案件だけ。未承認に繋いでも収益接点にならない（1533cd3 と同じ基準）
        "services": {s["id"] for s in services if s.get("approved")},
        "products": {p["id"] for p in products if p.get("approved")},
    }

    print(f"キューが{remaining}件なので補充します（目標{TARGET_QUEUE}件）。")
    demand = collect_demand()
    demand_all = {q for qs in demand.values() for q in qs}
    if not demand_all:
        print("::warning::Googleサジェストが1件も取得できませんでした。"
              "需要データ無しでトピックを創作はしないため、補充を見送ります。"
              "手動で topics.json と queue.json を補充してください")
        return 0
    print(f"サジェストから実需要 {len(demand_all)}件を取得しました。")

    need = TARGET_QUEUE - remaining
    import anthropic  # 需要が取れたときだけ必要
    client = anthropic.Anthropic()

    payload = {
        "既存トピックのタイトル（重複を避ける）": [t["title"] for t in topics],
        "カテゴリごとの実需要クエリ": demand,
        "使ってよい factIds": sorted(allowed["facts"]),
        "使ってよい serviceIds（承認済み案件のみ）": sorted(allowed["services"]),
        "使ってよい productIds": sorted(allowed["products"]),
    }
    instruction = f"""上のデータから、新しい記事トピックを{need}件提案してください。

厳守:
- 出力は {{"topics": [...]}} の JSON のみ。
- 各トピックの形: slug(英小文字とハイフンのみ・既存と重複しない) / type(compare|guide|problem|essay) /
  title(日本語) / categorySlug(qualification|career|programming|language) / theme(日本語1〜2文) /
  factIds[] / serviceIds[] / productIds[] / sourceQuery(根拠にした実需要クエリを1つ、原文のまま)
- **factIds / serviceIds / productIds は上のリストにある id しか使えません。** 新しい id を発明しない。
- factIds / serviceIds / productIds のうち、少なくとも1つは空でないこと。
- sourceQuery は「カテゴリごとの実需要クエリ」に載っている文字列をそのまま使うこと。
- 制度の解説が要るトピック(guide)は、上の factIds で説明しきれる範囲に限ること。
  台帳に無い制度・金額を前提にするトピックは提案しない。
- 既存トピックと内容が重なるものは提案しない。
"""
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM,
        messages=[{"role": "user",
                   "content": json.dumps(payload, ensure_ascii=False, indent=2) + "\n\n" + instruction}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    try:
        proposed = json.loads(text)["topics"]
    except Exception as e:
        print(f"::warning::提案をJSONとして読めませんでした（{type(e).__name__}）。補充を見送ります")
        return 0

    accepted, rejected = [], []
    for cand in proposed:
        reason = validate(cand, allowed, existing_slugs, demand_all)
        if reason:
            rejected.append((cand.get("slug", "?"), reason))
            continue
        existing_slugs.add(cand["slug"])
        accepted.append({
            "slug": cand["slug"],
            "type": cand["type"],
            "title": cand["title"],
            "categorySlug": cand["categorySlug"],
            "category": CATEGORY_LABEL[cand["categorySlug"]],
            "theme": cand["theme"],
            "factIds": cand.get("factIds") or [],
            "serviceIds": cand.get("serviceIds") or [],
            **({"productIds": cand["productIds"]} if cand.get("productIds") else {}),
            "sourceQuery": cand["sourceQuery"],
        })

    for slug, reason in rejected:
        print(f"[REJECT] {slug}: {reason}")
    if not accepted:
        print("::warning::検査を通ったトピックが0件でした。補充を見送ります")
        return 0

    topics.extend(accepted)
    TOPICS_PATH.write_text(json.dumps(topics_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for t in accepted:
        pending.append({"slug": t["slug"], "failures": 0, "blocked": False, "lastViolations": []})
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"補充しました: {len(accepted)}件（却下 {len(rejected)}件）")
    for t in accepted:
        print(f"  + {t['slug']}  [{t['type']}/{t['categorySlug']}]  ← 「{t['sourceQuery']}」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
