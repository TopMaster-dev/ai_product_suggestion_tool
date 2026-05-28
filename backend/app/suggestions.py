"""
チャット入力欄に表示する「動的サジェスト」を生成するモジュール。

実際の ks_m_items の在庫・カテゴリ分布をもとに、ユーザーが入力例として使える
日本語の自然な問い合わせ文をリスト化して返す。
"""

from __future__ import annotations

import random
from typing import List

from . import columns
from .database import 辞書カーソル

# ─────────────────────────────────────────────
# サジェスト文テンプレート
#   {cat} に中カテゴリを差し込み、{n} に件数を差し込む
# ─────────────────────────────────────────────
_テンプレート一覧: List[str] = [
    "{cat}を{n}点教えてください",
    "在庫の多い{cat}を{n}つ提案してください",
    "売れ筋の{cat}を{n}個",
    "{cat}のおすすめを{n}件紹介してください",
    "{cat}を予算別に{n}点",
]

# 件数バリエーション
_件数候補: List[int] = [3, 5, 7]

# 取得する中カテゴリの上限
_候補プール件数 = 24
# 表示するサジェスト件数
_表示件数 = 4

# テンプレートと相性の悪い汎用カテゴリは外す
_除外カテゴリ語句 = ["不明", "その他", "なし"]


def _人気中カテゴリ取得(プール件数: int) -> List[str]:
    """有効在庫のある商品が多い順に中カテゴリを取得する"""
    SQL = f"""
        SELECT
            `中カテゴリ` AS cat,
            COUNT(*)    AS c
        FROM `{columns.テーブル名}`
        WHERE (`廃番処理日` IS NULL OR YEAR(`廃番処理日`) = 0)
          AND COALESCE(`有効在庫数`, 0) > 0
          AND `中カテゴリ` IS NOT NULL
          AND `中カテゴリ` <> ''
        GROUP BY `中カテゴリ`
        ORDER BY c DESC
        LIMIT %s
    """
    with 辞書カーソル() as カーソル:
        カーソル.execute(SQL, [プール件数])
        行一覧 = カーソル.fetchall()

    候補一覧: List[str] = []
    for 行 in 行一覧:
        値 = (行.get("cat") or "").strip()
        if not 値:
            continue
        if any(語 in 値 for 語 in _除外カテゴリ語句):
            continue
        候補一覧.append(値)
    return 候補一覧


def 推奨サジェスト一覧(件数: int = _表示件数) -> List[str]:
    """
    DB の在庫状況から人気中カテゴリを抽出し、
    自然な日本語の入力例を `件数` 件だけ返す。

    呼び出すたびに少しずつ違う文面になるよう、テンプレート・件数をシャッフルする。
    """
    候補プール = _人気中カテゴリ取得(_候補プール件数)
    if not 候補プール:
        return _フォールバックサジェスト一覧()

    乱数 = random.Random()
    抽出カテゴリ = 乱数.sample(候補プール, k=min(len(候補プール), max(件数, 4)))

    結果: List[str] = []
    使用テンプレ: List[str] = []
    for カテゴリ in 抽出カテゴリ:
        # 直前に使ったテンプレと違うものを選ぶ
        残りテンプレ = [t for t in _テンプレート一覧 if t not in 使用テンプレ[-2:]]
        テンプレ = 乱数.choice(残りテンプレ or _テンプレート一覧)
        n = 乱数.choice(_件数候補)
        結果.append(テンプレ.format(cat=カテゴリ, n=n))
        使用テンプレ.append(テンプレ)
        if len(結果) >= 件数:
            break

    return 結果 or _フォールバックサジェスト一覧()


def _フォールバックサジェスト一覧() -> List[str]:
    """DB 接続できない／結果ゼロのときの安全な既定値"""
    return [
        "キッチンで使えるまな板を3点",
        "在庫の多いゴミ箱を5つ",
        "ステンレス製のハンガーを4個",
        "折りたたみのレジャーチェアを5点",
    ]
