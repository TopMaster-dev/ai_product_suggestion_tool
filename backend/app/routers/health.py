"""ヘルスチェック・ルートエンドポイント"""

from __future__ import annotations

from fastapi import APIRouter

from ..search import 総商品件数

ルーター = APIRouter(tags=["ヘルスチェック"])


@ルーター.get("/", summary="ルート確認")
async def ルート確認():
    """ルートURLアクセス時の稼働メッセージ"""
    return {
        "状態": "すべて正常に稼働しています。",
        "メッセージ": "ご利用ありがとうございます。ベストを尽くして頑張ってください！",
        "案内": "/api/ヘルスチェック で詳細な稼働状態を確認できます。",
    }


@ルーター.get("/api/ヘルスチェック", summary="システム稼働確認")
async def ヘルスチェック():
    """データベース接続と件数を返す"""
    try:
        件数 = 総商品件数()
        return {
            "状態": "正常稼働中",
            "フェーズ": "フェーズ① 社内チャットボット",
            "データベース": "接続OK",
            "登録商品数": 件数,
            "対象テーブル": "ks_m_items",
        }
    except Exception as エラー:
        return {"状態": "エラー", "詳細": str(エラー)}
