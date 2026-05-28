"""
OpenAI Chat Completions API への薄いラッパー。

- 標準ライブラリの urllib しか使わないので追加の依存は発生しない。
- 失敗時は OpenAIエラー を上げ、上位レイヤでフォールバックさせる。
- AI 接続確認用の軽量プローブをキャッシュ付きで提供する。
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple

from .config import 設定


class OpenAIエラー(RuntimeError):
    """OpenAI 呼び出しが失敗したことを表す例外"""


def チャット補完(
    プロンプト: str,
    *,
    最大トークン: int,
    温度: float,
    レスポンス形式: Optional[dict] = None,
) -> str:
    """OpenAI Chat Completions を呼び出し、応答テキストを返す"""
    if not 設定.OPENAI_API_KEY:
        raise OpenAIエラー("OPENAI_API_KEY が設定されていません。")

    ペイロード: dict = {
        "model": 設定.OPENAI_MODEL,
        "messages": [{"role": "user", "content": プロンプト}],
        "max_tokens": 最大トークン,
        "temperature": 温度,
    }
    if レスポンス形式:
        ペイロード["response_format"] = レスポンス形式

    リクエスト = urllib.request.Request(
        url="https://api.openai.com/v1/chat/completions",
        data=json.dumps(ペイロード).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {設定.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(リクエスト, timeout=設定.OPENAI_REQUEST_TIMEOUT) as レスポンス:
            データ = json.loads(レスポンス.read().decode("utf-8"))
            return (データ["choices"][0]["message"]["content"] or "").strip()
    except urllib.error.HTTPError as エラー:
        詳細 = エラー.read().decode("utf-8", errors="ignore")
        raise OpenAIエラー(f"HTTP {エラー.code} - {詳細}") from エラー
    except urllib.error.URLError as エラー:
        raise OpenAIエラー(f"接続失敗: {エラー.reason}") from エラー


# ─────────────────────────────────────────────
# AI 接続状態のキャッシュ付きプローブ
# ─────────────────────────────────────────────
_キャッシュ間隔秒 = 60
_状態キャッシュ: Optional[Tuple[float, bool, str, str]] = None  # (timestamp, ok, code, detail)


def AI接続確認(強制: bool = False) -> dict:
    """
    OpenAI API への接続を確認する。
    結果は 60 秒キャッシュし、頻繁な呼び出しでも実 API コールを抑える。

    戻り値:
      {
        "有効": bool,
        "状態コード": "OK" | "MISSING_KEY" | "INVALID_KEY" | "RATE_LIMITED"
                       | "NETWORK" | "QUOTA" | "ERROR",
        "詳細": "...",
        "確認時刻": "ISO8601",
      }
    """
    global _状態キャッシュ
    現在 = time.time()

    if not 強制 and _状態キャッシュ:
        発生時刻, OK, コード, 詳細 = _状態キャッシュ
        if 現在 - 発生時刻 < _キャッシュ間隔秒:
            return {
                "有効": OK,
                "状態コード": コード,
                "詳細": 詳細,
                "キャッシュ済み": True,
            }

    結果 = _実プローブ()
    _状態キャッシュ = (現在, 結果["有効"], 結果["状態コード"], 結果["詳細"])
    結果["キャッシュ済み"] = False
    return 結果


def _実プローブ() -> dict:
    """OpenAI に最小トークンで実 API コールしてキー有効性を判定する"""
    if not 設定.OPENAI_API_KEY:
        return {
            "有効": False,
            "状態コード": "MISSING_KEY",
            "詳細": "OPENAI_API_KEY が設定されていません。",
        }

    ペイロード = {
        "model": 設定.OPENAI_MODEL,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    リクエスト = urllib.request.Request(
        url="https://api.openai.com/v1/chat/completions",
        data=json.dumps(ペイロード).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {設定.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(リクエスト, timeout=10) as レスポンス:
            レスポンス.read()
            return {"有効": True, "状態コード": "OK", "詳細": "AI接続OK"}
    except urllib.error.HTTPError as エラー:
        詳細本文 = エラー.read().decode("utf-8", errors="ignore")
        コード = "ERROR"
        if エラー.code == 401:
            コード = "INVALID_KEY"
        elif エラー.code == 429:
            コード = "QUOTA" if "insufficient_quota" in 詳細本文 else "RATE_LIMITED"
        elif エラー.code == 404:
            コード = "MODEL_NOT_FOUND"
        return {
            "有効": False,
            "状態コード": コード,
            "詳細": f"HTTP {エラー.code}: {_短縮詳細(詳細本文)}",
        }
    except urllib.error.URLError as エラー:
        return {
            "有効": False,
            "状態コード": "NETWORK",
            "詳細": f"OpenAI に接続できません: {エラー.reason}",
        }
    except Exception as エラー:  # noqa: BLE001
        return {
            "有効": False,
            "状態コード": "ERROR",
            "詳細": f"予期しないエラー: {エラー}",
        }


def _短縮詳細(本文: str, 最大: int = 240) -> str:
    """エラーメッセージから OpenAI が返す主要メッセージだけを抜き出して短縮する"""
    try:
        データ = json.loads(本文)
        メッセージ = (
            データ.get("error", {}).get("message")
            if isinstance(データ.get("error"), dict)
            else None
        )
        if メッセージ:
            return メッセージ[:最大]
    except Exception:  # noqa: BLE001
        pass
    return 本文[:最大]


def AI接続キャッシュをクリア() -> None:
    """次回呼び出しで強制再プローブさせる"""
    global _状態キャッシュ
    _状態キャッシュ = None
