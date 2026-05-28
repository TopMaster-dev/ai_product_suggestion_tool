"""
MariaDB / MySQL への接続を扱うモジュール。
コンテキストマネージャ形式で安全にカーソルを利用できる。
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import mysql.connector
from mysql.connector.cursor import MySQLCursorDict

from .config import 設定


def データベース接続を作成():
    """設定値を使って新しいDB接続を返す"""
    return mysql.connector.connect(
        host=設定.DB_HOST,
        port=設定.DB_PORT,
        user=設定.DB_USER,
        password=設定.DB_PASSWORD,
        database=設定.DB_NAME,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
        use_pure=True,
    )


@contextmanager
def 辞書カーソル() -> Iterator[MySQLCursorDict]:
    """
    `with 辞書カーソル() as cur:` の形でDBカーソルを使うためのヘルパー。
    例外が発生しても確実に接続をクローズする。
    """
    接続 = データベース接続を作成()
    カーソル: MySQLCursorDict = 接続.cursor(dictionary=True)
    try:
        yield カーソル
    finally:
        try:
            カーソル.close()
        finally:
            接続.close()
