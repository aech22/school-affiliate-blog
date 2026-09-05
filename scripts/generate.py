# scripts/generate.py — 記事の生成エンジン（キュー消費型・1回1本）
#
# 事実の分離:
#   スクール名・料金・リンクは src/data/services.json（レジストリ）。
#   制度の給付率・上限は src/data/facts.json（検証済み台帳）。
#   LLM が書くのは講評と本文だけで、金額・率は台帳にある値しか書けない。
#   台帳外の金額・率が本文に現れたら scripts/gate.py が記事を破棄する。
#
# 使い方: ANTHROPIC_API_KEY を環境変数に設定して `python3 scripts/generate.py`
#   1回の実行で scripts/queue.json の先頭1件だけを処理する。
#   GitHub Actions が隔日で回す（.github/workflows/generate.yml）。
from __future__ import annotations
import datetime, json, os, sys
from pathlib import Path

import anthropic
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate import check as gate_check

ROOT = Path(__file__).resolve().parent.parent
SERVICES = json.loads((ROOT / "src" / "data" / "services.json").read_text(encoding="utf-8"))["services"]
FACTS = json.loads((ROOT / "src" / "data" / "facts.json").read_text(encoding="utf-8"))["facts"]
PRODUCTS = json.loads((ROOT / "src" / "data" / "products.json").read_text(encoding="utf-8"))["products"]
TOPICS = json.loads((ROOT / "scripts" / "topics.json").read_text(encoding="utf-8"))["topics"]
QUEUE_PATH = ROOT / "scripts" / "queue.json"
OUT_DIR = ROOT / "content" / "articles"
JST = datetime.timezone(datetime.timedelta(hours=9))

BY_ID = {s["id"]: s for s in SERVICES}
FACT_BY_ID = {f["id"]: f for f in FACTS}
PRODUCT_BY_ID = {p["id"]: p for p in PRODUCTS}
MAX_FAILURES = 3
# しきい値は scripts/replenish.py が正本（補充の発動条件と同じ値でないと意味が無い）。
from replenish import LOW_QUEUE_THRESHOLD

client = anthropic.Anthropic()

BODY_RULES = """
本文の厳守ルール:
- 金額・率（円・万円・%）は、渡された「使ってよい事実」に載っている値だけを書く。
  載っていない金額・率は、概算・言い換え・「約」付きも含めて一切書かない。
  受講料や月額に触れたいときは、金額を書かずに「各校の料金は記事内のカードを参照」と促す。
  金額を書いた場合、記事は自動的に破棄される。
- 制度の話をするときは、いつ時点の情報かがわかる書き方にする（例:「2026年9月時点」）。
- 「最安」「絶対」「No.1」「必ず転職できる」等の断定的な最上級表現を使わない。景表法・ASP規約に沿う。
- 見出しに 01/02/03 のような連番を付けない。絵文字を使わない。
- 読者の状況を具体的に想定して書く。抽象的な一般論を並べない。
"""

SCHEMA_LINE = """出力は JSON のみ。コードフェンス(```)で囲まない。前置き・後書きを付けない。
スキーマ（items の要素数と順序は入力のサービスと必ず一致させる）:
{"description":"100字程度の要約","intro":"導入3〜4文","body":"Markdown本文。H2(##)を3〜5個。各H2の下は2〜4段落","outro":"まとめ3〜4文","items":[{"pros":["...","...","..."],"cons":"...","target":"..."}]}"""

SYSTEM_COMPARE = """あなたは日本語のスクール比較記事のライターです。
選び方の観点 → 各サービスの位置づけ → 目的別の結論、の順で本文を書きます。
pros は各サービスの tags/target から自然に言える具体的な長所を3つ（各30〜55字程度）。
cons は正直な注意点を1〜2文。target は「こんな人に向いている」を1文。
""" + BODY_RULES + SCHEMA_LINE

SYSTEM_GUIDE = """あなたは日本語で、公的な学び支援制度をわかりやすく説明するライターです。
制度の要件 → 対象講座の探し方 → 申請の流れ → 注意点、の順で本文を書きます。
読者は制度を初めて調べる社会人です。用語をその場で開いて説明します。
""" + BODY_RULES + SCHEMA_LINE

SYSTEM_PROBLEM = """あなたは日本語で、キャリアやスキル習得の悩みに答えるライターです。
悩みの言語化 → 選択肢の整理 → 判断基準 → 次の一歩、の順で本文を書きます。
読者が自分で決められるようにするのが目的で、特定のサービスへ誘導するのが目的ではありません。
""" + BODY_RULES + SCHEMA_LINE

SYSTEM_ESSAY = """あなたは日本語で、学び直しや働き方についてのブログを書くライターです。
ある場面を起点に、そこで何に詰まるのかを書き、詰まりを埋める道具に触れる、という順で本文を書きます。

このブログの立場:
- **一人称の体験談を書かない。** 「私が使ってよかった」「実際に買ってみた」等、実体験を主張する表現は使わない。
  代わりに「〜という場面で効く」「〜する人がつまずくのはここ」という、場面と機能の話として書く。
  体験していないことを体験として書くのは、景表法・ステマ規制が最も厳しく見る形にあたる。
- 商品は本文の主役ではない。場面の説明が主で、道具はその帰結として出てくる。
- 断定的な効果の約束をしない（「これで必ず続く」等）。
""" + BODY_RULES + SCHEMA_LINE

SYSTEM_BY_TYPE = {"compare": SYSTEM_COMPARE, "guide": SYSTEM_GUIDE,
                  "problem": SYSTEM_PROBLEM, "essay": SYSTEM_ESSAY}


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


def _llm_prose(services: list, theme: str, facts: list, topic_type: str, products: list | None = None) -> dict:
    brief = [{
        "name": s.get("name", ""),
        "tags": s.get("tags", []),
        "target": s.get("target", ""),
    } for s in services]
    fact_brief = [{"claim": f["claim"], "value": f["value"], "note": f.get("note", "")} for f in facts]
    # gate.py が許可する金額・率をそのままプロンプトへ渡す。台帳の claim/value/note は
    # 散文なので、それだけではモデルが「書いてよい値」を列挙できない。渡さないと台帳外の
    # 数値が創作されてゲートに落ちる（2026-09-05 kyufu-taisho-kouza-sagashikata の「1万円」）。
    allowed_numbers = sorted({n for f in facts for n in (f.get("numbers") or [])})
    # URL は見せない（LLMがリンクを書く必要はない。描画は ProductMention が持つ）
    product_brief = [{"label": p["label"], "scene": p.get("scene", ""), "whyItHelps": p.get("whyItHelps", "")}
                     for p in (products or [])]
    system = SYSTEM_BY_TYPE.get(topic_type, SYSTEM_COMPARE)
    allowed_line = ("、".join(allowed_numbers) if allowed_numbers
                    else "（1つもありません。金額・率を一切書かないでください）")
    user = (f"テーマ: {theme}\n"
            f"使ってよい事実（ここに無い金額・率は書かない）:\n"
            f"{json.dumps(fact_brief, ensure_ascii=False, indent=2)}\n\n"
            f"本文に書いてよい金額・率はこの{len(allowed_numbers)}個だけです: {allowed_line}\n"
            f"この一覧に無い金額・率は、概算でも「約」付きでも言い換えでも書かないでください。"
            f"書いた時点で記事は破棄され、公開されません。\n\n"
            f"サービスデータ(順序厳守・{len(brief)}件):\n"
            f"{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
            + (f"本文で触れる道具（記事の主役ではない・{len(product_brief)}件）:\n"
               f"{json.dumps(product_brief, ensure_ascii=False, indent=2)}\n\n" if product_brief else "")
            + 
            f"上記スキーマのJSONだけを返してください。")
    last_err = None
    for attempt in range(2):
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user",
                       "content": user if attempt == 0 else user + "\n\n前回JSONとして解釈できませんでした。有効なJSONオブジェクトのみを返してください。"}],
        )
        try:
            return _extract_json(msg.content[0].text)
        except Exception as e:
            last_err = e
    raise ValueError(f"LLM出力をJSONとして解釈できませんでした: {last_err}")


def _existing_publish_date(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        fm = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        d = fm.get("date")
        return d.isoformat() if hasattr(d, "isoformat") else (str(d) if d else None)
    except Exception:
        return None


def build_topic(topic: dict, today: str) -> tuple[dict | None, str, list[str]]:
    """(frontmatter, body, violations) を返す。violations が空でなければ破棄する。"""
    services = [BY_ID[i] for i in topic.get("serviceIds", []) if i in BY_ID]
    facts = [FACT_BY_ID[i] for i in topic.get("factIds", []) if i in FACT_BY_ID]
    products = [PRODUCT_BY_ID[i] for i in topic.get("productIds", []) if i in PRODUCT_BY_ID]
    if not services and not facts and not products:
        print(f"[SKIP] {topic['slug']}: serviceId・factId・productId のいずれも0件")
        return None, "", []

    prose = _llm_prose(services, topic["theme"], facts, topic.get("type", "compare"), products)
    body = (prose.get("body") or "").strip()

    items = prose.get("items", [])

    # 検証ゲート: 読者の目に触れる LLM 生成テキストを全部通す。
    # pros/cons/target も ServiceCard が描画するので、body/intro/outro だけでは穴になる。
    checked_parts = [body, prose.get("intro", ""), prose.get("outro", ""), prose.get("description", "")]
    for it in items:
        checked_parts.extend(it.get("pros") or [])
        checked_parts.append(it.get("cons") or "")
        checked_parts.append(it.get("target") or "")
    violations = gate_check("\n".join(checked_parts), facts)
    if violations:
        return None, "", violations
    refs = []
    for i, s in enumerate(services):
        it = items[i] if i < len(items) else {}
        ref = {
            "id": s["id"],
            "rank": i + 1,
            "pros": (it.get("pros") or [])[:3],
            "cons": it.get("cons", ""),
            "target": it.get("target", ""),
        }
        refs.append({k: v for k, v in ref.items() if v not in (None, "", [])})

    path = OUT_DIR / f"{topic['slug']}.md"
    publish_date = _existing_publish_date(path) or today
    fm = {
        "title": topic["title"],
        "date": publish_date,
        "updated": today,
        "description": prose.get("description", ""),
        "category": topic.get("category", ""),
        "categorySlug": topic.get("categorySlug", ""),
        "type": topic.get("type", "compare"),
        "products": [p["id"] for p in products],
        "intro": prose.get("intro", ""),
        "outro": prose.get("outro", ""),
        "services": refs,
    }
    return {k: v for k, v in fm.items() if v not in (None, "")}, body, []


def to_markdown(fm: dict, body: str) -> str:
    y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=100000)
    return f"---\n{y}---\n\n{body}\n" if body else f"---\n{y}---\n"


def _save_queue(queue: dict) -> None:
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY が未設定です。環境変数に設定してから実行してください。")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now(JST).date().isoformat()

    # 台帳の鮮度。制度は改定されるので、古い一次情報を黙って使わない。
    stale = [f["id"] for f in FACTS
             if f.get("sourceType") == "primary"
             and (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(f["verifiedAt"])).days > 90]
    if stale:
        print(f"[WARN] 検証から90日を超えた事実があります: {stale}。一次情報を確認してください")

    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    pending = queue["pending"]
    by_slug = {t["slug"]: t for t in TOPICS}

    item = next((x for x in pending if not x.get("blocked")), None)
    if item is None:
        # 日次運用ではキューの枯渇がそのまま更新停止になる。緑のまま黙って止まると
        # 気づけないので、Actions のログに警告として出す。
        blocked = [x["slug"] for x in pending if x.get("blocked")]
        print("::warning::キューに処理できる項目がありません。topics.json と queue.json の補充が必要です。"
              + (f" blocked: {blocked}" if blocked else ""))
        return

    topic = by_slug.get(item["slug"])
    if topic is None:
        print(f"[SKIP] {item['slug']}: topics.json に定義がありません。キューから外します")
        pending.remove(item)
        _save_queue(queue)
        return

    try:
        fm, body, violations = build_topic(topic, today)
    except Exception as e:
        print(f"[ERROR] {item['slug']}: {type(e).__name__}: {e}")
        return

    if violations:
        item["failures"] = item.get("failures", 0) + 1
        item["lastViolations"] = violations
        print(f"[GATE] {item['slug']}: 未検証の数値 {violations}（{item['failures']}回目）")
        if item["failures"] >= MAX_FAILURES:
            item["blocked"] = True
            pending.remove(item)
            pending.append(item)
            print(f"[BLOCKED] {item['slug']}: {MAX_FAILURES}回連続で落ちたためキュー末尾へ送りました。"
                  f"facts.json に根拠を追加するか topics.json の theme を見直してください")
        _save_queue(queue)
        return

    if not fm:
        print(f"[SKIP] {item['slug']}: 生成対象なし")
        return

    (OUT_DIR / f"{item['slug']}.md").write_text(to_markdown(fm, body), encoding="utf-8")
    pending.remove(item)
    _save_queue(queue)
    print(f"generated -> {item['slug']}.md（本文{len(body)}字・{len(fm.get('services', []))}件）")
    remaining = len([x for x in pending if not x.get("blocked")])
    print(f"残りキュー: {remaining}件")
    # 日次なので残り件数がそのまま「あと何日もつか」になる。尽きる前に気づけるようにする。
    if remaining <= LOW_QUEUE_THRESHOLD:
        print(f"[INFO] 残りキューが{remaining}件です（日次実行なのであと{remaining}日ぶん）。"
              f"このあと scripts/replenish.py が需要データから補充します")


if __name__ == "__main__":
    main()
