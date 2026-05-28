"""
/api/商品説明生成 と /api/商品詳細

ユーザーが商品をクリックしたときに、その商品の **DBに入っているすべての項目** を
AIに渡して詳細な説明文を返す。
別途 /api/商品詳細 で生のDBデータと整形テキストも取得可能。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import (
    商品詳細レスポンス,
    商品説明生成リクエスト,
    商品説明生成レスポンス,
)
from ..recommend import 全カラム整形, 商品単体説明生成
from ..search import 商品コードで取得
from ..serialization import 行を安全化

ルーター = APIRouter(tags=["商品"])


def _商品コードを取得(リクエスト商品: dict) -> str:
    """フロントから来た 商品情報 から 商品コードを抜き出す"""
    候補 = (
        リクエスト商品.get("商品コード")
        or リクエスト商品.get("コード")
        or リクエスト商品.get("商品cd")
    )
    return str(候補 or "").strip()


@ルーター.post(
    "/api/商品説明生成",
    response_model=商品説明生成レスポンス,
    summary="選択商品の説明生成（全項目をAIに反映）",
)
async def 商品説明生成(リクエスト: 商品説明生成リクエスト) -> 商品説明生成レスポンス:
    """クリックされた商品の全カラムを使って説明＋推薦理由を生成する"""

    商品コード = _商品コードを取得(リクエスト.商品情報 or {})
    if not 商品コード:
        raise HTTPException(status_code=400, detail="商品コードが指定されていません。")

    全項目 = 商品コードで取得(商品コード)
    if not 全項目:
        # DBで見つからない場合はフロントから渡された情報のみで応答
        全項目 = dict(リクエスト.商品情報 or {})

    全項目_safe = 行を安全化(全項目)

    try:
        回答 = 商品単体説明生成(
            ユーザー入力=リクエスト.ユーザー入力,
            全項目=全項目_safe,
            使用フィルター=リクエスト.使用フィルター or {},
        )
    except Exception as エラー:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"商品説明生成エラー: {エラー}") from エラー

    return 商品説明生成レスポンス(
        回答=回答,
        商品コード=商品コード,
        全項目=全項目_safe,
    )


@ルーター.get(
    "/api/商品詳細/{code}",
    response_model=商品詳細レスポンス,
    summary="DB全項目の取得（AI生成なし）",
)
async def 商品詳細(code: str) -> 商品詳細レスポンス:
    """ks_m_items の全カラムをそのまま返す（パスパラメータは商品コード）"""

    全項目 = 商品コードで取得(code)
    if not 全項目:
        raise HTTPException(status_code=404, detail="商品が見つかりませんでした。")

    全項目_safe = 行を安全化(全項目)
    return 商品詳細レスポンス(
        商品コード=code,
        全項目=全項目_safe,
        整形テキスト=全カラム整形(全項目_safe),
    )
