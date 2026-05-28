"""
/api/サジェスト

チャット欄に表示する入力例を、DB のカテゴリ分布から動的に生成して返す。
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..suggestions import 推奨サジェスト一覧, _フォールバックサジェスト一覧

ルーター = APIRouter(tags=["サジェスト"])


class サジェストレスポンス(BaseModel):
    サジェスト一覧: List[str]
    生成元: str


@ルーター.get(
    "/api/サジェスト",
    response_model=サジェストレスポンス,
    summary="動的に生成したチャット入力例を返す",
)
async def サジェスト取得(件数: int = Query(default=4, ge=1, le=8)) -> サジェストレスポンス:
    """ks_m_items の人気カテゴリから入力例を組み立てる"""
    try:
        items = 推奨サジェスト一覧(件数=件数)
        if items:
            return サジェストレスポンス(サジェスト一覧=items, 生成元="DB")
    except Exception:  # noqa: BLE001
        pass

    return サジェストレスポンス(サジェスト一覧=_フォールバックサジェスト一覧(), 生成元="フォールバック")
