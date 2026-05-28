"""
Logo（ロゴ）社内チャットボット - バックエンド エントリーポイント

このファイルは FastAPI アプリ本体を構築し、各ルーターを登録するだけの
薄い「ボイラープレート」です。実際の処理は app/ パッケージに分割しています。

起動コマンド：
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import 設定
from app.routers import ai_status, chat, health, product, suggestion

# ─────────────────────────────────────────────
# FastAPI アプリ本体
# ─────────────────────────────────────────────
app = FastAPI(
    title="Logo（ロゴ）AI チャットボット API",
    description=(
        "社内商品提案チャットボット - フェーズ①\n"
        "データソース：MariaDB / 商品マスター.ks_m_items"
    ),
    version="2.0.0",
)

# ─────────────────────────────────────────────
# CORS
# ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=設定.CORS_ORIGINS,
    allow_origin_regex=設定.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# ルーター登録
# ─────────────────────────────────────────────
app.include_router(health.ルーター)
app.include_router(chat.ルーター)
app.include_router(product.ルーター)
app.include_router(suggestion.ルーター)
app.include_router(ai_status.ルーター)
