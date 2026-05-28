"""APIリクエスト・レスポンスのスキーマ定義（Pydantic）"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# /api/チャット
# ─────────────────────────────────────────────
class チャットリクエスト(BaseModel):
    メッセージ: str = Field(..., description="ユーザーが入力した日本語の問い合わせ")
    会話履歴: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class チャットレスポンス(BaseModel):
    回答: str
    提案商品リスト: List[Dict[str, Any]]
    使用フィルター: Dict[str, Any]
    処理ステップログ: List[Dict[str, Any]]


# ─────────────────────────────────────────────
# /api/商品説明生成
# ─────────────────────────────────────────────
class 商品説明生成リクエスト(BaseModel):
    ユーザー入力: str
    商品情報: Dict[str, Any]
    使用フィルター: Optional[Dict[str, Any]] = Field(default_factory=dict)


class 商品説明生成レスポンス(BaseModel):
    回答: str
    商品コード: str
    全項目: Dict[str, Any] = Field(default_factory=dict, description="DBから再取得した全カラム")


# ─────────────────────────────────────────────
# /api/商品詳細
# ─────────────────────────────────────────────
class 商品詳細レスポンス(BaseModel):
    商品コード: str
    全項目: Dict[str, Any]
    整形テキスト: str
