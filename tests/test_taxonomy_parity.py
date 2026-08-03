# tests/test_taxonomy_parity.py — config.py と taxonomy.ts の slug 一致テスト（stdlibのみ）
# 実行: python -m unittest discover -s tests
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from config import CATEGORIES  # noqa: E402


def _taxonomy_slugs():
    txt = (ROOT / "src" / "data" / "taxonomy.ts").read_text(encoding="utf-8")
    body = txt.split("CATEGORIES: Category[] = [", 1)[1].split("];", 1)[0]
    return set(re.findall(r"slug:\s*'([^']+)'", body))


class TestTaxonomyParity(unittest.TestCase):
    def test_config_and_taxonomy_slugs_match(self):
        self.assertEqual(set(CATEGORIES.keys()), _taxonomy_slugs())


if __name__ == "__main__":
    unittest.main()
