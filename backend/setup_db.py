"""
フェーズ① 初期セットアップ：
- 壊れた名前で作成された既存DBを安全に削除
- UTF-8 で 商品マスター DB を作り直す
- phase1_user を作り直してGRANTする

PowerShell の Shift-JIS 強制で文字化けしたDB名にも対処する。
接続情報はすべて backend/.env から読み込む。
"""

import os
import sys

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

ROOT_HOST = os.getenv("DB_HOST", "127.0.0.1")
ROOT_PORT = int(os.getenv("DB_PORT", "3306"))
ROOT_USER = os.getenv("DB_ROOT_USER", "root")
ROOT_PASS = os.getenv("DB_ROOT_PASSWORD", "")

TARGET_DB = os.getenv("DB_NAME", "商品マスター")
APP_USER = os.getenv("DB_USER", "phase1_user")
APP_PASS = os.getenv("DB_PASSWORD", "")

if not APP_PASS:
    print("[NG] .env に DB_PASSWORD が設定されていません。中断します。")
    sys.exit(1)

conn = mysql.connector.connect(
    host=ROOT_HOST,
    port=ROOT_PORT,
    user=ROOT_USER,
    password=ROOT_PASS,
    charset="utf8mb4",
    use_pure=True,
    raise_on_warnings=False,
)
cur = conn.cursor()

# ── 既存DB一覧 ──────────────────────────────
cur.execute("SHOW DATABASES")
all_dbs = [row[0] for row in cur.fetchall()]
print("[現在のDB一覧]")
for d in all_dbs:
    try:
        print(f"  - {d!r}")
    except Exception:
        print(f"  - (表示不可) bytes={d}")

# ── 不要なDBを全部落とす（UTF-8で書ける名前のみ）──
candidates = [d for d in all_dbs if "商品" in d or "マスタ" in d or d == TARGET_DB]
for d in candidates:
    print(f"[DROP DATABASE] {d!r}")
    try:
        cur.execute(f"DROP DATABASE `{d}`")
    except mysql.connector.Error as e:
        print(f"  → 失敗: {e}")

# ── UTF-8でターゲットDBを作る ─────────────
print(f"[CREATE DATABASE] {TARGET_DB}")
cur.execute(
    f"CREATE DATABASE `{TARGET_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
)

# ── アプリ用ユーザーをいったん落として作り直す ──
print(f"[DROP USER IF EXISTS] {APP_USER}@localhost")
try:
    cur.execute(f"DROP USER IF EXISTS '{APP_USER}'@'localhost'")
except mysql.connector.Error as e:
    print(f"  → 失敗（無視）: {e}")

print(f"[CREATE USER] {APP_USER}@localhost")
cur.execute(
    f"CREATE USER '{APP_USER}'@'localhost' IDENTIFIED BY %s",
    (APP_PASS,),
)
cur.execute(
    f"GRANT ALL PRIVILEGES ON `{TARGET_DB}`.* TO '{APP_USER}'@'localhost'"
)
cur.execute("FLUSH PRIVILEGES")

# ── 検証 ──────────────────────────────────
cur.execute("SHOW DATABASES")
after = [row[0] for row in cur.fetchall()]
print("\n[完了後のDB一覧]")
for d in after:
    print(f"  - {d!r}")

cur.close()
conn.close()

if TARGET_DB not in after:
    print(f"\n[NG] {TARGET_DB} が見つかりません。setup失敗。")
    sys.exit(1)

print(f"\n[OK] {TARGET_DB} を UTF-8 で再作成し、{APP_USER} を再作成しました。")
print("次は ks_m_items_Table.sql → ks_m_items_both.sql の順に取り込んでください。")
