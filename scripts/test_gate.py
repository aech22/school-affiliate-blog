# scripts/test_gate.py — gate.py のテスト。実行: python3 scripts/test_gate.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gate import normalize, extract_money_and_rate, allowed_tokens, check

FACTS = [
    {"id": "a", "numbers": ["20%", "10万円"]},
    {"id": "b", "numbers": ["70%", "56万円"]},
]
# priceNote は許可の根拠にしない。レジストリは一次情報で検証されていないため。
UNVERIFIED_SERVICES = [
    {"id": "s1", "priceNote": "月額4,980円〜"},
    {"id": "s2", "priceNote": "補助金適用で実質月6,666円から"},
]


def test_normalize_removes_commas_and_unifies_percent():
    assert normalize("4,980円") == "4980円"
    assert normalize("20％") == "20%"
    assert normalize(" 10万円 ") == "10万円"


def test_extract_picks_up_money_and_rate_only():
    got = extract_money_and_rate("最大70%（上限56万円）が支給されます。3つの観点で2〜3社を1年以内に比較します。")
    assert "70%" in got
    assert "56万円" in got
    # 個数・社数・年数はゲート対象外
    assert not any("つ" in g or "社" in g or "年" in g for g in got)


def test_allowed_tokens_comes_from_facts_only():
    allowed = allowed_tokens(FACTS)
    assert "20%" in allowed
    assert "56万円" in allowed


def test_price_note_is_not_a_source_of_truth():
    """レジストリの priceNote を根拠にしない。ここが緩いとゲートが素通りする。"""
    allowed = allowed_tokens(FACTS)
    for token in extract_money_and_rate(UNVERIFIED_SERVICES[1]["priceNote"]):
        assert token not in allowed


def test_gate_rejects_the_real_published_claim():
    """実際に公開中だった記述をゲートが弾くこと（回帰テスト）。"""
    real = "リスキリング補助金に対応しており、条件を満たせば最大70%還元で実質月6,666円から負担を抑えられます"
    violations = check(real, FACTS)
    assert "6666円" in violations


def test_rate_passes_when_backed_but_amount_never_does():
    # 2026-09-05 方針変更: 金額は台帳にあっても書かせない。率は台帳照合のまま。
    assert check("専門実践教育訓練給付金は最大70%です。", FACTS) == []
    assert check("年間上限は56万円です。", FACTS) == ["56万円"]
    assert check("最大70%（年間上限56万円）です。", FACTS) == ["56万円"]


def test_amount_is_rejected_regardless_of_ledger():
    for t in ["10万円", "56万円", "4,980円", "1円"]:
        assert check(f"費用は{t}です。", FACTS), f"金額が通ってしまった: {t}"


def test_amount_free_sentence_passes():
    assert check("支給額は受講する講座と本人の要件で変わるため、公式の案内で確認してください。", FACTS) == []


def test_check_flags_unbacked_numbers():
    text = "この講座は最大90%還元で、実質月6,666円から受けられます。"
    violations = check(text, FACTS)
    assert "90%" in violations
    assert "6666円" in violations


def test_check_is_not_fooled_by_full_width_percent():
    assert check("給付率は20％です。", FACTS) == []


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
