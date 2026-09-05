# scripts/gate.py — 本文に「台帳にない金額・率」が混ざっていないか検査する。
#
# なぜ金額と率だけを見るのか:
#   「3つの観点」「2〜3社」まで照合対象にすると偽陽性で全記事が落ちる。
#   景表法・ASP規約で実害が出るのは金額と率なので、そこに絞る。
from __future__ import annotations
import re

# 金額（円・万円）と率（%）だけを拾う。個数・社数・年数・日数は対象外。
# 「万円」を「円」より先に並べるのは、10万円 が 10万 + 円 に割れないようにするため。
_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:万円|円|%|％)")


def normalize(token: str) -> str:
    """表記ゆれを吸収する。カンマを外し、全角％を半角に、空白を除く。"""
    return token.strip().replace(",", "").replace("％", "%").replace(" ", "").replace("　", "")


def extract_money_and_rate(text: str) -> list[str]:
    """本文から金額・率の表現を抽出して正規化して返す（重複は保持しない）。"""
    seen: list[str] = []
    for m in _TOKEN.findall(text or ""):
        n = normalize(m)
        if n not in seen:
            seen.append(n)
    return seen


def allowed_tokens(facts: list[dict]) -> set[str]:
    """本文に出してよい金額・率の集合。出どころは facts.json だけ。

    services.json の priceNote を根拠に含めてはいけない。レジストリの値は
    一次情報での検証を経ておらず（例: mystar の「実質月6,666円から」は
    新規公募が終了したリスキリング補助金を前提にした古い値）、これを許可の
    根拠にするとゲートが素通りする。実際、初回実装ではこれで是正対象の
    記述が通ってしまった。

    料金は ServiceCard がレジストリから描画するので、本文が金額を書く必要は
    そもそも無い。本文は講評と制度の説明だけを担う。
    """
    allowed: set[str] = set()
    for f in facts or []:
        for n in f.get("numbers") or []:
            allowed.add(normalize(n))
    return allowed


def is_amount(token: str) -> bool:
    """正規化済みトークンが金額（円・万円）かどうか。率（%）と区別する。"""
    return normalize(token).endswith("円")


def check(text: str, facts: list[dict]) -> list[str]:
    """台帳に無い金額・率の一覧を返す。空リストなら合格。

    金額も率も台帳照合である。**台帳にある金額は「上限◯円」として書いてよい**が、
    そこから先の計算（自己負担額・実質価格・合計・差額）はさせない。
    計算結果は台帳に載っていないので、このゲートが自動的に弾く——
    つまり「台帳の値をそのまま書く」以外は通らない構造になっている。
    実際に受け取る額は受講料と本人の要件で変わるため、本文には
    上限であることが分かる形で書かせる（プロンプト側の BODY_RULES で指示）。
    """
    allowed = allowed_tokens(facts)
    return [t for t in extract_money_and_rate(text) if t not in allowed]
