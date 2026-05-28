"""
ks_m_items テーブルに対する商品検索のSQLビルダ。

戻り値は app.columns.一覧表示SELECT句 で射影されたフロントエンド互換の辞書。

ロジック：
- カテゴリ／条件リスト／価格は **AND** で厳密に絞り込む
- 用途／キーワード／季節は **補助シグナル** として扱い、ORDER BY のスコアにする
  （カテゴリ未指定のときだけ WHERE にも入れる）
"""

from __future__ import annotations

from typing import Any, List, Tuple

from . import columns
from .database import 辞書カーソル


def _LIKE_条件(対象カラム一覧: List[str], 値: str) -> Tuple[str, List[str]]:
    """カラム複数に対する OR 条件と、対応するパラメータを返す"""
    プレースホルダ = " OR ".join(f"`{c}` LIKE %s" for c in 対象カラム一覧)
    値リスト = [f"%{値}%"] * len(対象カラム一覧)
    return f"({プレースホルダ})", 値リスト


def _補助シグナル句構築(フィルター: dict) -> Tuple[str | None, List[Any]]:
    """用途・キーワード・季節を OR でまとめた句と、対応するパラメータを返す"""
    句一覧: List[str] = []
    パラメータ: List[Any] = []

    用途 = フィルター.get("用途")
    if 用途:
        節, 値 = _LIKE_条件(columns.用途検索カラム一覧, str(用途))
        句一覧.append(節)
        パラメータ.extend(値)

    for キーワード in フィルター.get("キーワードリスト") or []:
        節, 値 = _LIKE_条件(columns.キーワード検索カラム一覧, str(キーワード))
        句一覧.append(節)
        パラメータ.extend(値)

    if フィルター.get("季節"):
        節, 値 = _LIKE_条件(
            ["キーワード1", "キーワード2", "サブキーワード", "商品説明"],
            str(フィルター["季節"]),
        )
        句一覧.append(節)
        パラメータ.extend(値)

    if not 句一覧:
        return None, []
    return "(" + " OR ".join(句一覧) + ")", パラメータ


def 商品検索(フィルター: dict) -> List[dict]:
    """フィルターから動的にWHEREを組み立てて商品を取得する"""

    # フィルターが空（カテゴリ・条件・キーワード・用途・季節・価格 のどれも指定なし）
    # の場合、ランダムに見える商品を返してしまうのを避けるため空リストを返す。
    意味のあるシグナル = (
        フィルター.get("カテゴリ")
        or フィルター.get("用途")
        or フィルター.get("季節")
        or フィルター.get("最大価格")
        or フィルター.get("最小価格")
        or (フィルター.get("条件リスト") or [])
        or (フィルター.get("キーワードリスト") or [])
    )
    if not 意味のあるシグナル:
        return []

    # 廃番処理日 は zero-date ('0000-00-00 00:00:00') を「未廃番」として扱う運用なので、
    # NULL もしくは年が 0 のレコードを「販売中」とみなす。
    WHERE条件: List[str] = [
        "(`廃番処理日` IS NULL OR YEAR(`廃番処理日`) = 0)",
        "COALESCE(`有効在庫数`, 0) > 0",
    ]
    WHEREパラメータ: List[Any] = []

    # ── カテゴリ（AND：もっとも強い絞り込み）──────
    カテゴリ指定あり = bool(フィルター.get("カテゴリ"))
    if カテゴリ指定あり:
        節, 値 = _LIKE_条件(
            columns.カテゴリ検索カラム一覧 + columns.名称検索カラム一覧,
            str(フィルター["カテゴリ"]),
        )
        WHERE条件.append(節)
        WHEREパラメータ.extend(値)

    # ── 条件リスト（複数 AND）─────────────────────
    for 条件キーワード in フィルター.get("条件リスト", []) or []:
        節, 値 = _LIKE_条件(columns.条件検索カラム一覧, str(条件キーワード))
        WHERE条件.append(節)
        WHEREパラメータ.extend(値)

    # ── 価格範囲（売価(税込)で評価）──────────────
    if フィルター.get("最大価格"):
        WHERE条件.append("`売価(税込)` <= %s")
        WHEREパラメータ.append(フィルター["最大価格"])
    if フィルター.get("最小価格"):
        WHERE条件.append("`売価(税込)` >= %s")
        WHEREパラメータ.append(フィルター["最小価格"])

    # ── 補助シグナル（用途・キーワード・季節）─────
    補助句, 補助パラメータ = _補助シグナル句構築(フィルター)

    # カテゴリ未指定なら、補助シグナルを WHERE 必須条件にする（最低限の関連性を担保）
    WHERE用補助あり = False
    if 補助句 and not カテゴリ指定あり:
        WHERE条件.append(補助句)
        WHEREパラメータ.extend(補助パラメータ)
        WHERE用補助あり = True

    WHERE句 = " AND ".join(WHERE条件)

    # ── 並び順 ───────────────────────────────────
    並び順指定 = フィルター.get("並び順") or []
    タイブレーカー = (
        "`有効在庫数` DESC, `アスパック登録日` DESC"
        if "在庫優先" in 並び順指定
        else "`アスパック登録日` DESC, `有効在庫数` DESC"
    )

    # 補助シグナルを ORDER BY のスコアに使う
    ORDERパラメータ: List[Any] = []
    if 補助句 and not WHERE用補助あり:
        # WHERE には入れず、関連度ボーナスとしてのみ使用
        ORDER_BY = f"({補助句}) DESC, {タイブレーカー}"
        ORDERパラメータ.extend(補助パラメータ)
    else:
        ORDER_BY = タイブレーカー

    # ── 件数 ─────────────────────────────────────
    取得件数 = max(1, min(int(フィルター.get("提案件数", 5)), 30))

    SQL = f"""
        SELECT
            {columns.一覧表示SELECT句}
        FROM `{columns.テーブル名}`
        WHERE {WHERE句}
        ORDER BY {ORDER_BY}
        LIMIT {取得件数}
    """

    パラメータ = WHEREパラメータ + ORDERパラメータ

    with 辞書カーソル() as カーソル:
        カーソル.execute(SQL, パラメータ)
        return list(カーソル.fetchall())


def 商品コードで取得(商品コード: str) -> dict | None:
    """商品コード指定で ks_m_items の全カラムを返す"""
    SQL = f"SELECT * FROM `{columns.テーブル名}` WHERE `商品コード` = %s LIMIT 1"
    with 辞書カーソル() as カーソル:
        カーソル.execute(SQL, [商品コード])
        return カーソル.fetchone()


def 総商品件数() -> int:
    """ヘルスチェック用の総件数"""
    with 辞書カーソル() as カーソル:
        カーソル.execute(f"SELECT COUNT(*) AS 件数 FROM `{columns.テーブル名}`")
        行 = カーソル.fetchone()
        return int(行["件数"]) if 行 else 0
