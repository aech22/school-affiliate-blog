# scripts/test_generate.py — generate.py の終了コードのテスト。実行: python3 scripts/test_generate.py
#
# 何を守るか: 「API に断られた日は赤、ゲート落ちの日は緑」。
# 2026-09-10〜17 にクレジット切れの 400 が8日間続いたが、当時は例外を握って return していたため
# Actions が緑のまま生成だけが止まり、誰にも通知が届かなかった。
import os
import sys
from pathlib import Path

# generate.py は import 時に anthropic.Anthropic() を作るので、キーが無い環境でも読めるようにする。
# ここでは API を一切呼ばない（build_topic を差し替える）。
os.environ.setdefault("ANTHROPIC_API_KEY", "test-dummy-key")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anthropic
import generate


class _FakeAPIError(anthropic.APIError):
    """anthropic.APIError の最小の偽物。
    本物は httpx の Request/Response を要求するが、CI の anthropic 1.x は httpx2 を使い
    `import httpx` が通らない（2026-09-18 に実際に落ちた）。判定は isinstance だけなので
    HTTP 層を持たない子クラスで足りる。"""

    def __init__(self, status: int, message: str):
        Exception.__init__(self, message)
        self.message = message
        self.status_code = status

    def __str__(self) -> str:
        return self.message


def _api_error(status: int, message: str) -> anthropic.APIError:
    return _FakeAPIError(status, message)


def _run(monkey_build):
    """build_topic を差し替えて main() を1回走らせ、(終了コード, 保存されたキュー) を返す。"""
    saved = []
    orig_build, orig_save = generate.build_topic, generate._save_queue
    generate.build_topic = monkey_build
    generate._save_queue = lambda q: saved.append(q)
    try:
        try:
            generate.main()
            code = 0
        except SystemExit as e:
            code = e.code
    finally:
        generate.build_topic, generate._save_queue = orig_build, orig_save
    return code, saved


def test_credit_exhaustion_fails_the_run_and_keeps_queue():
    def boom(topic, today):
        raise _api_error(400, "Your credit balance is too low to access the Anthropic API.")
    code, saved = _run(boom)
    assert code == 1, f"API エラーは終了コード1で赤くする（実際: {code}）"
    assert saved == [], "API エラーの日はキューを書き換えない（翌日そのまま再試行する）"


def test_server_side_error_also_fails_the_run():
    def boom(topic, today):
        raise _api_error(529, "Overloaded")
    code, saved = _run(boom)
    assert code == 1
    assert saved == []


def test_gate_violation_is_a_green_skip():
    def rejected(topic, today):
        return {"title": "x"}, "本文", ["1万円"]
    code, saved = _run(rejected)
    assert code == 0, "ゲート落ちは見送り（緑）のまま"
    assert len(saved) == 1, "ゲート落ちは failures を進めてキューを保存する"


def test_unparsable_llm_output_is_a_green_skip():
    def broken(topic, today):
        raise ValueError("LLM出力をJSONとして解釈できませんでした")
    code, saved = _run(broken)
    assert code == 0
    assert saved == []


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {name}: {e}")
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
