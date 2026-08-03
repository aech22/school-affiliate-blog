# scripts/generate.py — スクール比較記事の生成エンジン（手動実行）
# 事実（スクール名・料金目安・特徴・リンク）は src/data/services.json に一元化。
# LLM(Haiku)には「講評文（intro/outro/各校のpros/cons/target/highlight）」だけを書かせる。
# → 料金やURLのLLM誤記が構造的に起きない。事実・リンクはレンダリング側(Astro)がservices.jsonから描く。
#
# 使い方: ANTHROPIC_API_KEY を環境変数に設定して `python3 scripts/generate.py`
#   （services.json / topics.json を編集したら再実行して記事を更新する。編集主体のため日次cronには載せない）
from __future__ import annotations
import datetime, json, os, sys
from pathlib import Path

import anthropic
import yaml

ROOT = Path(__file__).resolve().parent.parent
SERVICES = json.loads((ROOT / "src" / "data" / "services.json").read_text(encoding="utf-8"))["services"]
TOPICS = json.loads((ROOT / "scripts" / "topics.json").read_text(encoding="utf-8"))["topics"]
OUT_DIR = ROOT / "content" / "articles"
JST = datetime.timezone(datetime.timedelta(hours=9))

BY_ID = {s["id"]: s for s in SERVICES}

client = anthropic.Anthropic()

SYSTEM_PROMPT = """あなたは日本語のスクール比較記事のライターです。
与えられたスクールデータ（実在のプログラミングスクール）をもとに、読者目線の正直な比較記事の「文章部分」だけをJSONで返します。

厳守ルール:
- 誇大表現・根拠のない最上級表現を使わない（「最安」「絶対」「No.1」「日本一」「必ず転職できる」等は禁止）。景表法・ASP規約に沿う。
- 料金の断定額・キャンペーン内容・URLなどの事実は書かない（それらはシステム側がservices.jsonから埋め込む）。あなたは各校の特徴・向き不向きの講評だけ書く。
- pros は各校の tags/target/priceNote から自然に言える具体的な長所を3つ（各30〜55字程度・内容を薄くしない）。
- cons は正直な注意点や検討ポイントを1〜2文で具体的に。target は「こんな人に向いている」を1文で。
- intro は記事全体の導入(3〜4文・スクール選びの観点を提示)。outro はまとめ(3〜4文・目的別の選び方指針)。
- 出力は JSON のみ。コードフェンス(```)で囲まない。前置き・後書きを付けない。

出力JSONスキーマ（items の要素数と順序は入力のスクールと必ず一致させる）:
{"description":"100字程度の要約","intro":"...","outro":"...","items":[{"pros":["...","...","..."],"cons":"...","target":"..."}]}"""


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


def _llm_prose(services: list, theme: str) -> dict:
    brief = [{
        "name": s.get("name", ""),
        "tags": s.get("tags", []),
        "priceNote": s.get("priceNote", ""),
        "target": s.get("target", ""),
    } for s in services]
    user = (f"テーマ: {theme}\n"
            f"スクールデータ(順序厳守・{len(brief)}校):\n"
            f"{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
            f"上記スキーマのJSONだけを返してください。")
    last_err = None
    for attempt in range(2):
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
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


def _existing_publish_date(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        fm = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1]) or {}
        d = fm.get("date")
        return d.isoformat() if hasattr(d, "isoformat") else (str(d) if d else None)
    except Exception:
        return None


def build_topic(topic: dict, today: str) -> dict | None:
    services = [BY_ID[i] for i in topic["serviceIds"] if i in BY_ID]
    if not services:
        print(f"[SKIP] {topic['slug']}: 有効なserviceIdが0件")
        return None
    prose = _llm_prose(services, topic["theme"])
    items = prose.get("items", [])
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
        "intro": prose.get("intro", ""),
        "outro": prose.get("outro", ""),
        "services": refs,
    }
    return {k: v for k, v in fm.items() if v not in (None, "")}


def to_markdown(fm: dict) -> str:
    y = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=100000)
    return f"---\n{y}---\n"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY が未設定です。環境変数に設定してから実行してください。")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.datetime.now(JST).date().isoformat()
    n = 0
    for topic in TOPICS:
        try:
            fm = build_topic(topic, today)
            if not fm:
                continue
            (OUT_DIR / f"{topic['slug']}.md").write_text(to_markdown(fm), encoding="utf-8")
            print(f"generated -> {topic['slug']}.md（{len(fm['services'])}校）")
            n += 1
        except Exception as e:
            print(f"[SKIP] {topic['slug']}: {type(e).__name__}: {e}")
    print(f"done: {n} 記事")


if __name__ == "__main__":
    main()
