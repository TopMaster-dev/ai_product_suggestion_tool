"""
環境変数から設定値を読み込むモジュール。
.env をロードし、アプリ全体で使う設定をひとつの場所に集約する。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


@dataclass(frozen=True)
class アプリ設定:
    """アプリ全体の設定値（不変オブジェクト）"""

    # ── データベース設定 ─────────────────────────────
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "phase1_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "商品マスター")

    # ── OpenAI 設定 ──────────────────────────────────
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_REQUEST_TIMEOUT: int = int(os.getenv("OPENAI_REQUEST_TIMEOUT", "60"))

    # ── CORS 設定 ────────────────────────────────────
    CORS_ORIGINS: List[str] = field(default_factory=lambda: _split_csv(
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        )
    ))
    CORS_ORIGIN_REGEX: str = os.getenv(
        "CORS_ORIGIN_REGEX",
        r"^https://([a-zA-Z0-9-]+\.)?vercel\.app$"
        r"|^https://[a-zA-Z0-9-]+\.ngrok-free\.(app|dev)$",
    )

    # ── 検索の既定値 ─────────────────────────────────
    DEFAULT_SUGGESTION_COUNT: int = int(os.getenv("DEFAULT_SUGGESTION_COUNT", "5"))
    MAX_SUGGESTION_COUNT: int = int(os.getenv("MAX_SUGGESTION_COUNT", "30"))


設定 = アプリ設定()
