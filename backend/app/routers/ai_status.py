"""
/api/AI状態

OpenAI API キーの有効性を返すルーター。
フロントエンドはこの情報を使って「AI接続停止中」のアラートを出す。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..openai_client import AI接続確認, AI接続キャッシュをクリア

ルーター = APIRouter(tags=["AI状態"])


class AI状態レスポンス(BaseModel):
    有効: bool
    状態コード: str
    詳細: str
    人間向けメッセージ: str
    確認時刻: str
    キャッシュ済み: Optional[bool] = None


_状態コード別メッセージ = {
    "OK": "AI生成は正常に動作しています。",
    "MISSING_KEY": "OPENAI_API_KEY が未設定です。バックエンドの .env を確認してください。",
    "INVALID_KEY": "OpenAI のAPIキーが無効です。新しいキーを発行して .env に設定してください。",
    "RATE_LIMITED": "OpenAI のレート制限に達しています。しばらく待ってから再度お試しください。",
    "QUOTA": "OpenAI の利用枠（クォータ）を超過しています。請求情報を確認してください。",
    "MODEL_NOT_FOUND": "指定された OpenAI モデルが見つかりません。OPENAI_MODEL の値を確認してください。",
    "NETWORK": "OpenAI サーバーに接続できません。ネットワーク／プロキシをご確認ください。",
    "ERROR": "AI 接続でエラーが発生しました。詳細はサーバーログを確認してください。",
}


def _人間向け(状態コード: str) -> str:
    return _状態コード別メッセージ.get(状態コード, _状態コード別メッセージ["ERROR"])


@ルーター.get(
    "/api/AI状態",
    response_model=AI状態レスポンス,
    summary="OpenAI API キーの有効性を返す",
)
async def AI状態取得(再確認: bool = Query(default=False)) -> AI状態レスポンス:
    """
    再確認=True を渡すとキャッシュを破棄して再プローブする。
    """
    if 再確認:
        AI接続キャッシュをクリア()
    結果 = AI接続確認(強制=再確認)
    return AI状態レスポンス(
        有効=結果["有効"],
        状態コード=結果["状態コード"],
        詳細=結果["詳細"],
        人間向けメッセージ=_人間向け(結果["状態コード"]),
        確認時刻=datetime.utcnow().isoformat() + "Z",
        キャッシュ済み=結果.get("キャッシュ済み"),
    )
