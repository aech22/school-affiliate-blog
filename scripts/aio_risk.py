# scripts/aio_risk.py — 補充候補の sourceQuery が「AI要約で完結する検索語」かを判定する。
#
# なぜ要るのか:
#   Pew Research Center（900人・68,879検索・2025年3月）の実測では、AI要約が
#   表示された検索で従来の検索結果がクリックされたのは 8%、表示されなかった検索では
#   15% だった。要約内のリンクがクリックされたのは 1%。つまり AI要約が出る検索語は、
#   順位を取っても流入が約半分になる。
#   https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/
#
# 何を軸にするのか（ここを間違えると効かないゲートになる）:
#   Seer Interactive が 49,353 クエリを分類した集計では、AI要約の出現率は
#   情報意図 36% / 商業意図 8% / 取引意図 5%。一方で**形式別では比較型（AとBどっち・vs）が
#   95.4%、質問形が 85.9%、レビュー形が 86.3%** と極めて高い。
#   したがって「比較記事にすれば避けられる」は成立しない。避けられるのは
#   **検索語が取引に近いとき**であって、記事の型（compare/guide/essay）は関係ない。
#   だから判定対象は cand["type"] ではなく cand["sourceQuery"] である。
#   ※この出現率はSEOベンダーの自社集計で、標本の抽出条件が公開されていない（🟡）。
#     順序（情報 > 商業 > 取引）は複数の独立した出所で一貫するので順序だけを使い、
#     36%/8%/5% という値そのものをしきい値に焼き込まない。
#
# 落とし方を弱くしてある理由:
#   AFFILIATE.md ハマりどころ22 の再発防止。薬機法ゲートの初回実装は禁止語に
#   「医薬部外品」を入れたせいで、公開済み61本のうち3本の正常な記事を誤検出で落とした。
#   ここでも「比較」「おすすめ」を一律に弾くとコドナビの記事型そのものが成立しなくなり、
#   キューが枯れる。よって:
#     - **ハード却下は定義型クエリだけ**（「〜とは」「〜 意味」「〜 読み方」）。
#       購買意図がゼロで、かつAI要約で答えが確定する。ここだけは疑いが無い。
#     - それ以外は却下せず**分類して比率で抑える**（enforce_intent_ratio）。
#       既存の enforce_lifestyle_ratio と同じ仕組みにしてある。
from __future__ import annotations

import re

# 定義型。これに当たる語はハード却下する。
# 「〜とは何か」まで含めたいので前方一致ではなく部分一致で見る。
_DEFINITIONAL = re.compile(r"とは|意味|読み方|どういう意味|何の略")

# 情報意図の強いマーカー。質問形・比較対戦形・レビュー形。
# Seer の形式別集計で 85〜95% が AI要約を伴っていた形である。
_INFORMATIONAL = (
    "なぜ", "どうして", "いつから", "いつまで", "どこで", "どっち", "どちら",
    "違い", "vs", "ｖｓ", "メリット", "デメリット", "仕組み", "理由",
    "口コミ", "評判", "レビュー", "体験談", "ランキング", "一覧",
)

# 取引意図の強いマーカー。申し込む・払う・手続きする、という**読者の動作**に触れている語。
# ここに当たるものは AI要約が出にくく、出ても読者が原典を確認しに来る。
#
# ⚠️ 制度名の一部になる語（給付・支給・還付）をここに入れてはいけない。
#    「教育訓練給付金とは」が部分一致だけで取引意図に化け、コドナビの資格カテゴリが
#    まるごと素通りする（初回実装で実際に踏み、test_summarize_counts_all_buckets が検出した）。
#    AFFILIATE.md ハマりどころ25「トークン照合は台帳に値を足すほど衝突する」と同型。
#    軸は**主題が何か**ではなく**読者が何をしようとしているか**に置く。
_TRANSACTIONAL = (
    "申請", "申込", "申し込み", "登録", "無料体験", "資料請求", "見学",
    "料金", "費用", "価格", "いくら", "月額", "分割", "支払",
    "予約", "購入", "解約", "返金", "キャンペーン", "クーポン",
    "対象", "条件", "要件",
    "必要書類", "手続き", "窓口", "期限", "締切",
)

# 情報意図の候補がキュー全体に占めてよい上限。
# 0 にしないのは、情報意図の語が入口として機能する経路（内部リンクで取引側へ送る）を
# 完全には否定できないため。7:3 の日常比率と同じ考え方で、3割までは許す。
INFORMATIONAL_MAX_RATIO = 0.3


def is_definitional(query: str) -> bool:
    """定義型クエリか。ハード却下の対象。"""
    return bool(_DEFINITIONAL.search(query or ""))


def classify(query: str) -> str:
    """検索語を transactional / informational / neutral に分類する。

    取引マーカーを情報マーカーより優先する。「教育訓練給付金 対象 いつから」のように
    両方を含む語は、読者が自分の条件を確定させに来ているので取引側に数える。
    """
    q = query or ""
    if any(m in q for m in _TRANSACTIONAL):
        return "transactional"
    if any(m in q for m in _INFORMATIONAL):
        return "informational"
    return "neutral"


def enforce_intent_ratio(accepted: list[dict], pending: list[dict],
                         topics: list[dict]) -> tuple[list[dict], list[dict]]:
    """情報意図の候補がキューの3割を超えないよう間引く。

    比率は補充後のキュー全体で測る。1件ずつ足しながら判定すると、キューが空に
    近いときに最初の1件が必ず上限を超えて情報意図が永久に入らなくなる
    （enforce_lifestyle_ratio と同じ理由・同じ書き方にしてある）。

    戻り値は (残したもの, 落としたもの)。
    """
    by_slug = {t.get("slug"): t for t in topics}
    queued = [by_slug.get(p.get("slug")) or {} for p in pending]
    info_now = sum(1 for t in queued
                   if classify(t.get("sourceQuery", "")) == "informational")

    final_total = len(queued) + len(accepted)
    allowance = max(0, int(INFORMATIONAL_MAX_RATIO * final_total) - info_now)

    kept, dropped = [], []
    for cand in accepted:
        if classify(cand.get("sourceQuery", "")) == "informational":
            if allowance <= 0:
                dropped.append(cand)
                continue
            allowance -= 1
        kept.append(cand)
    return kept, dropped


def summarize(queries: list[str]) -> dict[str, int]:
    """検索語の集合を分類して件数を返す。既存トピックの点検に使う。"""
    counts = {"transactional": 0, "neutral": 0, "informational": 0, "definitional": 0}
    for q in queries:
        if is_definitional(q):
            counts["definitional"] += 1
        counts[classify(q)] += 1
    return counts
