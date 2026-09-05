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

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate import check as gate_check  # noqa: E402

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
#
# 前半は案件（services.json）向け、後半は楽天商品（products.json）向けの語である。
# 楽天側の語を入れないと、essay に載せる道具の需要が一度も観測されず、
# 補充が案件記事だけに偏る（2026-09-05 に実測して判明）。
# 種キーワード。案件向けの語と楽天商品向けの語の両方を持つ（片方だけだと補充が偏る）。
# 2026-09-05: 読者像を「学び直し・働き方を変える社会人」に広げたのに合わせ、
# 副業・フリーランス・在宅ワークの回線・レンタルサーバー・留学の語を足した。
# slug は増やさない（判断ログ 2026-09-05）。新しい語は既存4カテゴリのどれかに入れる。
SEED_QUERIES = {
    "qualification": ["教育訓練給付金", "リスキリング 補助金", "動画編集 スクール", "資格 独学",
                      "勉強 デスク 環境", "簿記3級 独学 テキスト", "TOEIC 単語帳", "勉強 タイマー"],
    "career": ["社内SE 転職", "転職エージェント 20代", "未経験 転職 IT",
               "オンライン面接 カメラ", "web面接 照明",
               "副業 始め方 会社員", "フリーランス 独立 準備", "在宅ワーク 回線 速度"],
    "programming": ["プログラミングスクール 比較", "プログラミング 独学 挫折",
                    "プログラミング モニター 2画面", "ノートパソコン スタンド",
                    "レンタルサーバー 個人 おすすめ", "ドメイン 取得 個人"],
    "language": ["英会話スクール 比較", "中国語 教室", "社会人 英語 やり直し", "英語 参考書 おすすめ",
                 "社会人 留学 短期", "語学研修 費用"],
}

# src/data/taxonomy.ts の label と同じ文字列にする（記事frontmatter の category に入る）。
CATEGORY_LABEL = {
    "qualification": "学び・スキル講座",
    "career": "転職・働き方",
    "programming": "プログラミング・IT",
    "language": "語学・留学",
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


def extract_json(text: str) -> dict:
    """LLM出力からJSONを取り出す。コードフェンスと前後の散文に耐える。

    scripts/generate.py もこれを import して使う（定義を1箇所に保つ）。
    素の json.loads だとフェンス付きの応答で落ちる。2026-09-05 の dry run で
    実際に補充が「JSONとして読めません」で見送られたのがこれ。
    """
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


def _slugify_ok(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug or ""))


def validate(cand: dict, allowed: dict, existing_slugs: set[str],
             demand_all: set[str], facts_by_id: dict | None = None) -> str | None:
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
    # アフィリリンクを持たないコラムは許す。比較記事だけは比べる対象（案件）が要る。
    # generate.py の compare プロンプトはサービスを並べる前提なので、
    # productIds だけの compare も成立しない。
    if cand["type"] == "compare" and not cand.get("serviceIds"):
        return "type=compare なのに serviceIds が空（比べる対象が無い）"

    # タイトルとテーマに、そのトピックの factIds で裏付けられない金額・率が入っていたら弾く。
    # 入れたままにすると、本文が必ずその数値を書こうとしてゲートに3回落ち、blocked になる。
    # ゲートはトークン照合なので、台帳に同じ数字が別の意味で在ると素通りする危険もある
    # （実例: 2026-09-05 の dry run で「70%が脱落する」が提案された。台帳の 70% は
    #  専門実践教育訓練の給付率で、脱落率とは無関係）。
    if facts_by_id is not None:
        topic_facts = [facts_by_id[i] for i in (cand.get("factIds") or []) if i in facts_by_id]
        # 判定は gate.check に一本化する（金額は台帳にあっても不許可・率は台帳照合）
        bad = gate_check(f"{cand['title']}\n{cand['theme']}", topic_facts)
        if bad:
            return f"タイトル/テーマに書けない数値が含まれる（金額は一律不可・率は台帳照合）: {bad}"
    return None


def main(dry_run: bool = False, force: bool = False, need_override: int | None = None) -> int:
    if dry_run:
        print("=== DRY RUN: サジェスト取得・提案・構造検査まで行い、ファイルは書きません ===")
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    pending = queue["pending"]
    remaining = len([x for x in pending if not x.get("blocked")])
    if remaining > LOW_QUEUE_THRESHOLD and not force:
        print(f"キューは{remaining}件。しきい値{LOW_QUEUE_THRESHOLD}件を上回っているので補充しません。")
        return 0

    topics_doc = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    topics = topics_doc["topics"]
    existing_slugs = {t["slug"] for t in topics}

    facts = json.loads((ROOT / "src" / "data" / "facts.json").read_text(encoding="utf-8"))["facts"]
    services = json.loads((ROOT / "src" / "data" / "services.json").read_text(encoding="utf-8"))["services"]
    products = json.loads((ROOT / "src" / "data" / "products.json").read_text(encoding="utf-8"))["products"]
    facts_by_id = {f["id"]: f for f in facts}
    allowed = {
        "facts": {f["id"] for f in facts},
        # 承認済み案件だけ。未承認に繋いでも収益接点にならない（1533cd3 と同じ基準）
        "services": {s["id"] for s in services if s.get("approved")},
        "products": {p["id"] for p in products if p.get("approved")},
    }

    print(f"キューが{remaining}件です（目標{TARGET_QUEUE}件）。"
          + ("しきい値を無視して実行します（--force）。" if force and remaining > LOW_QUEUE_THRESHOLD else "補充します。"))
    demand = collect_demand()
    demand_all = {q for qs in demand.values() for q in qs}
    if not demand_all:
        print("::warning::Googleサジェストが1件も取得できませんでした。"
              "需要データ無しでトピックを創作はしないため、補充を見送ります。"
              "手動で topics.json と queue.json を補充してください")
        return 0
    print(f"サジェストから実需要 {len(demand_all)}件を取得しました。")

    need = need_override if need_override else max(1, TARGET_QUEUE - remaining)
    import anthropic  # 需要が取れたときだけ必要
    client = anthropic.Anthropic()

    payload = {
        "既存トピックのタイトル（重複を避ける）": [t["title"] for t in topics],
        "カテゴリごとの実需要クエリ": demand,
        "使ってよい factIds": sorted(allowed["facts"]),
        "使ってよい serviceIds（承認済み案件のみ）": sorted(allowed["services"]),
        "使ってよい productIds": sorted(allowed["products"]),
    }
    # 型が偏らないようにする。件数が少ないときは無理に配分を求めない。
    mix_line = ("提案{n}件のうち、少なくとも1件は「道具のエッセイ」、少なくとも1件は"
                "「アフィリリンクを持たないコラム」にしてください。残りは案件記事と制度解説から選びます。"
                ).format(n=need) if need >= 4 else "型は上の4つから、テーマに合うものを選んでください。"
    instruction = f"""上のデータから、新しい記事トピックを{need}件提案してください。

厳守:
- 出力は {{"topics": [...]}} の JSON のみ。
- 各トピックの形: slug(英小文字とハイフンのみ・既存と重複しない) / type(compare|guide|problem|essay) /
  title(日本語) / categorySlug(qualification|career|programming|language) / theme(日本語1〜2文) /
  factIds[] / serviceIds[] / productIds[] / sourceQuery(根拠にした実需要クエリを1つ、原文のまま)
- **factIds / serviceIds / productIds は上のリストにある id しか使えません。** 新しい id を発明しない。
- factIds / serviceIds / productIds のうち、少なくとも1つは空でないこと。
- sourceQuery は「カテゴリごとの実需要クエリ」に載っている文字列をそのまま使うこと。
- **title には sourceQuery の中心になる語を、言い換えずにそのまま含めること**（検索している人の
  言葉のまま出す）。ただし語を並べただけの不自然なタイトルにはしない。読んで意味の通る日本語にする。
- 制度の解説が要るトピック(guide)は、上の factIds で説明しきれる範囲に限ること。
  台帳に無い制度・金額を前提にするトピックは提案しない。
- 既存トピックと内容が重なるものは提案しない。

トピックには4つの作り方があります。**この4つを混ぜて提案してください。**
1. 案件記事(compare / problem): serviceIds にスクールや転職エージェントを入れる。
   **compare には serviceIds が必須**です（比べる対象が無いと成立しません）。
2. 制度解説(guide): factIds を入れる。台帳にある事実だけで書ける範囲に限ります。
3. 道具のエッセイ(essay): productIds に学習環境の道具を入れる。
   場面（夜に学ぶ・オンライン面接・画面が1枚しかない等）を主役にし、道具はその帰結として出します。
   商品名を並べる記事にはしません。
4. アフィリリンクを持たないコラム(essay / problem): factIds も serviceIds も productIds も空にする。
   読者が自分で判断するための整理だけを書く記事です。収益接点はありません。

{mix_line}
"""
    base_msg = json.dumps(payload, ensure_ascii=False, indent=2) + "\n\n" + instruction
    proposed = None
    last_err = None
    for attempt in range(2):
        content = base_msg if attempt == 0 else (
            base_msg + "\n\n前回JSONとして解釈できませんでした。"
                       "コードフェンスも前置きも付けず、有効なJSONオブジェクトだけを返してください。")
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        if msg.stop_reason == "max_tokens":
            # 途中で切れた応答は必ずJSONとして壊れる。原因を取り違えないよう明示する。
            print(f"[WARN] 応答が max_tokens で打ち切られました（{attempt + 1}回目）")
        try:
            proposed = extract_json(text)["topics"]
            break
        except Exception as e:
            last_err = e
            print(f"[WARN] {attempt + 1}回目の応答をJSONとして読めませんでした: {type(e).__name__}: {e}")
            print(f"       応答の先頭200字: {text[:200]!r}")
    if proposed is None:
        print(f"::warning::提案をJSONとして読めませんでした（{type(last_err).__name__}）。補充を見送ります")
        return 0

    accepted, rejected = [], []
    for cand in proposed:
        reason = validate(cand, allowed, existing_slugs, demand_all, facts_by_id)
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

    if dry_run:
        print(f"[DRY RUN] 検査を通った提案: {len(accepted)}件（却下 {len(rejected)}件）。ファイルは書いていません")
        for t in accepted:
            print(f"  (追加されるはず) {t['slug']}  [{t['type']}/{t['categorySlug']}]  ← 「{t['sourceQuery']}」")
            print(f"      title: {t['title']}")
            print(f"      theme: {t['theme']}")
            kind = ("道具のエッセイ" if t.get("productIds") else
                    "案件記事" if t["serviceIds"] else
                    "制度解説" if t["factIds"] else "アフィリンク無しのコラム")
            print(f"      factIds={t['factIds']} serviceIds={t['serviceIds']} "
                  f"productIds={t.get('productIds', [])}  → {kind}")
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
    ap = argparse.ArgumentParser(description="キューが少なければ需要データからトピックを補充する")
    ap.add_argument("--dry-run", action="store_true",
                    help="サジェスト取得・提案・構造検査まで行い、ファイルを書かない（動作確認用）")
    ap.add_argument("--force", action="store_true",
                    help="キューがしきい値を上回っていても実行する（動作確認用）")
    ap.add_argument("--need", type=int, default=None,
                    help="提案させる件数を指定する（動作確認用。既定は目標件数との差）")
    args = ap.parse_args()
    sys.exit(main(dry_run=args.dry_run, force=args.force, need_override=args.need))
