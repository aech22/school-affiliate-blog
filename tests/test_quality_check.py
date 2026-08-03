# tests/test_quality_check.py — 品質ゲート check() の純粋関数テスト（stdlibのみ）
# 実行: python -m unittest discover -s tests
import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from quality_check import check

FM = '---\ntitle: "テスト記事"\ndate: 2026-08-02\n---\n'
LINK = "https://hb.afl.rakuten.co.jp/ichiba/xxxx/yyyy/?pc=zzzz"
BODY = "これは十分に長い本文です。" * 80  # 800字以上を確保


class TestQualityCheck(unittest.TestCase):
    def test_valid_article_passes(self):
        md = FM + BODY + f"\n\n[商品を見る]({LINK})\n"
        self.assertEqual(check(md), [])

    def test_short_body_fails(self):
        md = FM + "短い本文" + f"\n[商品]({LINK})\n"
        self.assertTrue(any("短すぎる" in e for e in check(md)))

    def test_missing_affiliate_link_fails(self):
        md = FM + BODY
        self.assertTrue(any("アフィリンク" in e for e in check(md)))

    def test_missing_frontmatter_fails(self):
        md = BODY + f"\n[商品]({LINK})\n"
        self.assertTrue(any("frontmatter" in e for e in check(md)))

    def test_banned_word_fails(self):
        md = FM + BODY + "この商品は絶対に最安値です。" + f"\n[商品]({LINK})\n"
        errs = check(md)
        self.assertTrue(any("禁止語" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
