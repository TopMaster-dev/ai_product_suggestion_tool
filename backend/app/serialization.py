"""
DBの値（Decimal / datetime / 等）を JSON へ安全にシリアライズするヘルパー。

ks_m_items のテキスト系カラム（商品説明・キャッチコピー 等）には
HTML タグが含まれているため、フロントエンドに渡す前に除去する。
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List

from .recommend import HTML除去


def 値を安全化(値: Any) -> Any:
    """JSONレスポンスに乗せられる型へ変換する"""
    if 値 is None:
        return None
    if isinstance(値, Decimal):
        return float(値)
    if isinstance(値, (datetime, date)):
        return 値.isoformat()
    if isinstance(値, bytes):
        値 = 値.decode("utf-8", errors="ignore")
    if isinstance(値, str):
        # URL カラム等はそのまま返したいので、明らかな HTML が含まれる場合のみ除去する
        if "<" in 値 or "&" in 値:
            return HTML除去(値)
        return 値
    return 値


def 行を安全化(行: Dict[str, Any]) -> Dict[str, Any]:
    return {キー: 値を安全化(値) for キー, 値 in 行.items()}


def 行リストを安全化(行リスト: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [行を安全化(行) for 行 in 行リスト]
