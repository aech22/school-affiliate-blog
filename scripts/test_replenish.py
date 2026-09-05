#!/usr/bin/env python3
"""scripts/replenish.py の構造検査のテスト。

このスクリプトが守っているのは「LLM に事実を増やさせない」こと。
検査が緩むと、存在しない id や需要データに無いクエリを根拠にしたトピックが
キューに入り、生成本文が台帳外の数値を書いてゲートで落ち続ける。
ここが通らない状態で本番の補充を回さないよう、CI では生成の前に実行する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from replenish import validate, extract_json  # noqa: E402

ALLOWED = {
    "facts": {"kyufu-ippan", "kyufu-senmon-jissen"},
    "services": {"se-navi", "nova"},
    "products": {"mobile-monitor"},
}
EXISTING = {"already-used-slug"}
DEMAND = {"教育訓練給付金 条件", "英会話スクール 比較"}


def base(**over) -> dict:
    cand = {
        "slug": "kyufu-jouken-no-mikata",
        "type": "guide",
        "title": "教育訓練給付金の条件の見方",
        "categorySlug": "qualification",
        "theme": "受給条件をどう確かめるかを整理する",
        "factIds": ["kyufu-ippan"],
        "serviceIds": [],
        "productIds": [],
        "sourceQuery": "教育訓練給付金 条件",
    }
    cand.update(over)
    return cand


def test_valid_candidate_passes():
    assert validate(base(), ALLOWED, EXISTING, DEMAND) is None


def test_rejects_unknown_fact_id():
    r = validate(base(factIds=["kyufu-ippan", "not-a-real-fact"]), ALLOWED, EXISTING, DEMAND)
    assert r is not None and "factIds" in r


def test_rejects_unapproved_service_id():
    # 未承認案件は allowed に入っていないので、id として存在しても弾かれる
    r = validate(base(factIds=[], serviceIds=["techacademy"]), ALLOWED, EXISTING, DEMAND)
    assert r is not None and "serviceIds" in r


def test_rejects_duplicate_slug():
    r = validate(base(slug="already-used-slug"), ALLOWED, EXISTING, DEMAND)
    assert r is not None and "重複" in r


def test_rejects_bad_slug_format():
    for bad in ["日本語スラッグ", "Upper-Case", "trailing-", "double--hyphen", ""]:
        r = validate(base(slug=bad), ALLOWED, EXISTING, DEMAND)
        assert r is not None, f"通ってしまった: {bad}"


def test_rejects_source_query_not_in_demand():
    # 需要データに無いクエリを根拠にしたら、それは実需要ではなく創作
    r = validate(base(sourceQuery="でっちあげたキーワード"), ALLOWED, EXISTING, DEMAND)
    assert r is not None and "sourceQuery" in r


def test_rejects_all_empty_ids():
    r = validate(base(factIds=[], serviceIds=[], productIds=[]), ALLOWED, EXISTING, DEMAND)
    assert r is not None and "すべて空" in r


def test_rejects_invalid_type_and_category():
    assert validate(base(type="news"), ALLOWED, EXISTING, DEMAND) is not None
    assert validate(base(categorySlug="cooking"), ALLOWED, EXISTING, DEMAND) is not None


def test_rejects_missing_required_field():
    for key in ("slug", "type", "title", "categorySlug", "theme", "sourceQuery"):
        r = validate(base(**{key: ""}), ALLOWED, EXISTING, DEMAND)
        assert r is not None and key in r, f"{key} の欠落を検出できていない"


def test_accepts_service_only_topic():
    # factIds が空でも serviceIds があれば generate.py は生成できる
    r = validate(base(type="compare", slug="eikaiwa-hikaku-2026", factIds=[],
                      serviceIds=["nova"], categorySlug="language",
                      sourceQuery="英会話スクール 比較"), ALLOWED, EXISTING, DEMAND)
    assert r is None, r


def test_extract_json_plain():
    assert extract_json('{"topics": []}') == {"topics": []}


def test_extract_json_strips_code_fence():
    # 2026-09-05 の dry run で実際に補充を止めたのがこの形
    fenced = '```json\n{"topics": [{"slug": "a"}]}\n```'
    assert extract_json(fenced)["topics"][0]["slug"] == "a"


def test_extract_json_strips_bare_fence_and_prose():
    assert extract_json('```\n{"topics": []}\n```') == {"topics": []}
    assert extract_json('はい、こちらです:\n{"topics": []}\nご確認ください。') == {"topics": []}


def test_extract_json_raises_on_garbage():
    try:
        extract_json("JSONではない文章")
    except Exception:
        return
    raise AssertionError("壊れた入力で例外が出ていない")


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as e:
                failed += 1
                print(f"  FAIL {name}: {e}")
    print(f"\n{'FAILED' if failed else 'OK'}: {failed} failure(s)")
    sys.exit(1 if failed else 0)
