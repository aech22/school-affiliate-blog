# scripts/config.py
# ── カテゴリ体系（大元の性別軸 gender × ジャンル軸 category）──
# gender: "men" | "women" | "unisex"
# CATEGORIES の slug は Astro 側 src/data/taxonomy.ts と一致させること（記事URL・カテゴリページの結合キー）。
# ガジェナビはガジェット物販特化のため全カテゴリ unisex。
CATEGORIES = {
    "earphones":     {"label": "イヤホン・ヘッドホン",           "gender": "unisex"},
    "charging":      {"label": "モバイルバッテリー・充電器",     "gender": "unisex"},
    "pc-peripheral": {"label": "PC周辺機器",                     "gender": "unisex"},
    "smart-home":    {"label": "スマート家電",                   "gender": "unisex"},
    "camera-gear":   {"label": "カメラ・周辺機器",               "gender": "unisex"},
    "gaming":        {"label": "ゲーミングデバイス",             "gender": "unisex"},
    "wearable":      {"label": "スマートウォッチ・ウェアラブル", "gender": "unisex"},
    "home-gadget":   {"label": "生活家電ガジェット",             "gender": "unisex"},
}

# ── 生成対象。1エントリ = 1記事。cat は CATEGORIES のキー。gender は cat から自動導出。──
TOPICS = [
    # イヤホン・ヘッドホン
    {"theme": "通勤で選ぶワイヤレスイヤホン比較",       "keyword": "ワイヤレスイヤホン",           "cat": "earphones",     "hits": 4},
    {"theme": "ノイズキャンセリングヘッドホンの選び方", "keyword": "ノイズキャンセリング ヘッドホン", "cat": "earphones",     "hits": 4},
    # モバイルバッテリー・充電器
    {"theme": "大容量モバイルバッテリー比較",           "keyword": "モバイルバッテリー",           "cat": "charging",      "hits": 4},
    {"theme": "急速充電できるUSB充電器の選び方",         "keyword": "USB 充電器",                   "cat": "charging",      "hits": 4},
    # PC周辺機器
    {"theme": "在宅ワーク向けワイヤレスマウス比較",     "keyword": "ワイヤレスマウス",             "cat": "pc-peripheral", "hits": 4},
    {"theme": "打ちやすいメカニカルキーボードの選び方", "keyword": "メカニカルキーボード",         "cat": "pc-peripheral", "hits": 4},
    # スマート家電
    {"theme": "スマートスピーカーの選び方",             "keyword": "スマートスピーカー",           "cat": "smart-home",    "hits": 4},
    {"theme": "見守りに使えるスマートカメラ比較",       "keyword": "ネットワークカメラ",           "cat": "smart-home",    "hits": 4},
    # カメラ・周辺機器
    {"theme": "旅行に持って行く軽量三脚の選び方",       "keyword": "三脚",                         "cat": "camera-gear",   "hits": 4},
    {"theme": "撮影に効くSDカードの選び方",             "keyword": "SDカード",                     "cat": "camera-gear",   "hits": 4},
    # ゲーミングデバイス
    {"theme": "長時間でも疲れないゲーミングチェア比較", "keyword": "ゲーミングチェア",             "cat": "gaming",        "hits": 4},
    {"theme": "FPS向けゲーミングマウスの選び方",        "keyword": "ゲーミングマウス",             "cat": "gaming",        "hits": 4},
    # スマートウォッチ・ウェアラブル
    {"theme": "毎日使えるスマートウォッチ比較",         "keyword": "スマートウォッチ",             "cat": "wearable",      "hits": 4},
    {"theme": "睡眠も測れる活動量計の選び方",           "keyword": "活動量計",                     "cat": "wearable",      "hits": 4},
    # 生活家電ガジェット
    {"theme": "速乾で選ぶ高性能ドライヤー比較",         "keyword": "ドライヤー",                   "cat": "home-gadget",   "hits": 4},
    {"theme": "肌にやさしい電動シェーバーの選び方",     "keyword": "電気シェーバー",               "cat": "home-gadget",   "hits": 4},
    # 追加はここに1行ずつ（cat は CATEGORIES のキーから選ぶ）
]
