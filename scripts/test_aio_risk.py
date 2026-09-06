# scripts/test_aio_risk.py — aio_risk.py のテスト。実行: python3 scripts/test_aio_risk.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aio_risk import (  # noqa: E402
    INFORMATIONAL_MAX_RATIO,
    classify,
    enforce_intent_ratio,
    is_definitional,
    summarize,
)


def test_definitional_is_detected():
    assert is_definitional("教育訓練給付金とは")
    assert is_definitional("リスキリング 意味")
    assert is_definitional("SIer 読み方")
    # 取引に近い語は定義型ではない
    assert not is_definitional("教育訓練給付金 申請 必要書類")


def test_transactional_beats_informational():
    # 両方のマーカーを持つ語は取引側に数える（読者は自分の条件を確定させに来ている）
    assert classify("教育訓練給付金 対象 いつから") == "transactional"
    assert classify("プログラミングスクール 料金 比較") == "transactional"


def test_informational_markers():
    assert classify("転職エージェント 20代 どっち") == "informational"
    assert classify("プログラミングスクール 評判") == "informational"
    assert classify("простой vs テスト") == "informational"  # vs は形式マーカー


def test_neutral_when_no_marker():
    assert classify("動画編集 スクール") == "neutral"
    assert classify("在宅ワーク 環境") == "neutral"


def test_ratio_allows_first_informational_when_queue_empty():
    """キューが空でも情報意図が1件も入らない、という壊れ方をしないこと。"""
    topics = [{"slug": "a", "sourceQuery": "転職 評判"}]
    accepted = [{"slug": "a", "sourceQuery": "転職 評判"},
                {"slug": "b", "sourceQuery": "給付金 申請"},
                {"slug": "c", "sourceQuery": "スクール 料金"},
                {"slug": "d", "sourceQuery": "スクール 費用"}]
    kept, dropped = enforce_intent_ratio(accepted, [], topics)
    # 合計4件なので情報意図の許容は int(0.3*4)=1 件
    assert len(kept) == 4
    assert dropped == []


def test_ratio_drops_excess_informational():
    topics = [{"slug": s, "sourceQuery": "転職 評判"} for s in ("a", "b", "c")]
    accepted = [{"slug": s, "sourceQuery": "転職 評判"} for s in ("a", "b", "c")]
    kept, dropped = enforce_intent_ratio(accepted, [], topics)
    # 合計3件で許容は int(0.3*3)=0 件。全部落ちる
    assert kept == []
    assert len(dropped) == 3


def test_ratio_counts_existing_queue():
    """既にキューに入っている情報意図の件数を勘定に入れること。"""
    topics = [{"slug": "old1", "sourceQuery": "転職 評判"},
              {"slug": "old2", "sourceQuery": "給付金 申請"},
              {"slug": "new1", "sourceQuery": "スクール 口コミ"}]
    pending = [{"slug": "old1"}, {"slug": "old2"}]
    accepted = [{"slug": "new1", "sourceQuery": "スクール 口コミ"}]
    kept, dropped = enforce_intent_ratio(accepted, pending, topics)
    # 合計3件で許容は int(0.3*3)=0、既に情報意図が1件あるので新規は入らない
    assert kept == []
    assert len(dropped) == 1


def test_summarize_counts_all_buckets():
    got = summarize(["教育訓練給付金とは", "給付金 申請 期限", "転職 どっち", "動画編集 スクール"])
    assert got["definitional"] == 1
    assert got["transactional"] == 1
    assert got["informational"] == 1
    # 「教育訓練給付金とは」は definitional かつ neutral に数えられる
    assert got["neutral"] == 2


def test_subject_noun_does_not_leak_into_transactional():
    """制度名の一部（給付・支給）で取引意図に化けないこと。

    初回実装で踏んだ実バグの回帰テスト。ここが壊れるとコドナビの資格カテゴリが
    まるごと素通りする。
    """
    assert classify("教育訓練給付金") == "neutral"
    assert classify("教育訓練給付金 なぜ") == "informational"
    # 読者自身の動作に触れて初めて取引意図になる
    assert classify("教育訓練給付金 申請") == "transactional"
    assert classify("教育訓練給付金 対象") == "transactional"


def test_ratio_constant_is_sane():
    assert 0 < INFORMATIONAL_MAX_RATIO < 1


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
