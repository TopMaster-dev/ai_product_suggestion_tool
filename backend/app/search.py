"""
ks_m_items テーブルに対する商品検索のSQLビルダ。

戻り値は app.columns.一覧表示SELECT句 で射影されたフロントエンド互換の辞書。

設計方針（クライアントFB反映後）：
- カテゴリ／カラー／キャラクター／条件リスト／価格 はすべて **AND の必須フィルター**
- 用途 と キーワードリスト は **関連度スコア（ORDER BY 用）**、ただし
  「カテゴリ未指定」のときに限り最低限の WHERE 必須条件にする
- 各フィルター値は シノニム辞書 で OR 展開して LIKE する（例 黒 → ブラック / BK / BLACK）
- **絞り込みを緩める段階的フォールバックは廃止**（5件水増しで関連性のない商品が混ざる問題）
- 「結果が0件のときは正直に0件を返す」のが原則。recommend.py が「見つかりません」と回答する。
- 並び順は ① 関連度（OR一致件数の和） ② 重点商品 → 発注ランク ③ 在庫 → 登録日
"""

from __future__ import annotations

from typing import Any, List, Tuple

from . import columns
from .database import 辞書カーソル
from .intent import 条件シノニム辞書, カラーシノニム辞書, キャラクターシノニム辞書


# ──────────────────────────────────────────────────────────
# LIKE 句ヘルパ
# ──────────────────────────────────────────────────────────
def _LIKE_句(対象カラム一覧: List[str], 値: str) -> Tuple[str, List[str]]:
    """
    カラム複数に対する OR 条件と、対応するパラメータを返す。

    COLLATE utf8mb4_bin を強制することで、デフォルト照合
    (utf8mb4_unicode_ci) が ひらがな↔カタカナ や小書きカナ
    を等価扱いして発生する誤マッチを防ぐ。
    """
    プレースホルダ = " OR ".join(
        f"`{c}` LIKE %s COLLATE utf8mb4_bin" for c in 対象カラム一覧
    )
    値リスト = [f"%{値}%"] * len(対象カラム一覧)
    return f"({プレースホルダ})", 値リスト


def _シノニム拡張(値: str, 辞書: dict) -> List[str]:
    """値とそのシノニム候補を重複除去して返す"""
    候補 = list(dict.fromkeys(辞書.get(値, [値])))
    if 値 not in 候補:
        候補.insert(0, 値)
    return 候補


def _シノニムLIKE句(対象カラム一覧: List[str], 値: str, 辞書: dict) -> Tuple[str, List[Any]]:
    """
    値とシノニム全候補で OR LIKE する句を構築する。
    例：値="黒" → 「カラー LIKE %黒% OR ... OR カラー LIKE %ブラック% OR ...」
    """
    候補語 = _シノニム拡張(値, 辞書)
    句一覧: List[str] = []
    パラメータ: List[Any] = []
    for 語 in 候補語:
        節, 値リスト = _LIKE_句(対象カラム一覧, 語)
        句一覧.append(節)
        パラメータ.extend(値リスト)
    return "(" + " OR ".join(句一覧) + ")", パラメータ


# ──────────────────────────────────────────────────────────
# 関連度スコア句（ORDER BY 用）
#   キーワードと用途が各カラムに含まれた個数を合算する
# ──────────────────────────────────────────────────────────
def _関連度スコア句(フィルター: dict) -> Tuple[str, List[Any]]:
    """マッチした補助シグナルの数を合算する CASE 式と対応パラメータを返す"""
    部分式: List[str] = []
    パラメータ: List[Any] = []

    def _add(対象カラム一覧: List[str], 値: str) -> None:
        for c in 対象カラム一覧:
            部分式.append(
                f"(CASE WHEN `{c}` LIKE %s COLLATE utf8mb4_bin THEN 1 ELSE 0 END)"
            )
            パラメータ.append(f"%{値}%")

    用途 = フィルター.get("用途")
    if 用途:
        _add(columns.用途検索カラム一覧, str(用途))

    for kw in フィルター.get("キーワードリスト") or []:
        _add(columns.キーワード検索カラム一覧, str(kw))

    if not 部分式:
        return "0", []
    return "(" + " + ".join(部分式) + ")", パラメータ


# ──────────────────────────────────────────────────────────
# 検索本体
# ──────────────────────────────────────────────────────────
def 商品検索(フィルター: dict) -> List[dict]:
    """
    厳密 AND の必須フィルター + 関連度ソートで商品を取得する。
    水増しのためのフォールバック展開は行わない（0件なら 0件で返す）。
    """

    # 何のシグナルもない場合は早期 return（無条件全件表示を避ける）
    有意なシグナル = any([
        フィルター.get("カテゴリ"),
        フィルター.get("カラー"),
        フィルター.get("キャラクター"),
        フィルター.get("用途"),
        フィルター.get("季節"),
        フィルター.get("最大価格"),
        フィルター.get("最小価格"),
        (フィルター.get("条件リスト") or []),
        (フィルター.get("キーワードリスト") or []),
    ])
    if not 有意なシグナル:
        return []

    # ── WHERE 条件 ──
    # ベース: 廃番なし & 在庫あり
    WHERE条件: List[str] = [
        "(`廃番処理日` IS NULL OR YEAR(`廃番処理日`) = 0)",
        "COALESCE(`有効在庫数`, 0) > 0",
    ]
    WHEREパラメータ: List[Any] = []

    # カテゴリ（AND）— **完全一致 or 末尾一致** で厳密に絞る
    # 中カテゴリ "キッチン収納用品" の 小小カテゴリ "包丁スタンド" が
    # 「包丁」検索にヒットして「包丁ホルダー」が混入する事故を防ぐため、
    # 部分一致 LIKE %値% ではなく、より厳密なマッチを使う。
    #
    #   ・中カテゴリ = 値                        … 例 "包丁" "まな板" "フライパン"
    #   ・中カテゴリ LIKE '%値'                  … 例 "子供用お弁当箱" を "弁当箱" で拾う
    #   ・小カテゴリ = 値                        … 例 中カテゴリ"コップ"の下の 小カテゴリ"マグカップ"
    #   ・小小カテゴリ = 値
    カテゴリ指定あり = bool(フィルター.get("カテゴリ"))
    if カテゴリ指定あり:
        値 = str(フィルター["カテゴリ"])
        節 = (
            "("
            "`中カテゴリ` = %s COLLATE utf8mb4_bin "
            "OR `中カテゴリ` LIKE %s COLLATE utf8mb4_bin "
            "OR `小カテゴリ` = %s COLLATE utf8mb4_bin "
            "OR `小小カテゴリ` = %s COLLATE utf8mb4_bin"
            ")"
        )
        WHERE条件.append(節)
        WHEREパラメータ.extend([値, f"%{値}", 値, 値])

    # カラー（AND、シノニム OR 展開）
    if フィルター.get("カラー"):
        節, 値 = _シノニムLIKE句(
            columns.カラー検索カラム一覧,
            str(フィルター["カラー"]),
            カラーシノニム辞書,
        )
        WHERE条件.append(節)
        WHEREパラメータ.extend(値)

    # キャラクター（AND、シノニム OR 展開）
    if フィルター.get("キャラクター"):
        節, 値 = _シノニムLIKE句(
            columns.キャラクター検索カラム一覧,
            str(フィルター["キャラクター"]),
            キャラクターシノニム辞書,
        )
        WHERE条件.append(節)
        WHEREパラメータ.extend(値)

    # 条件リスト（複数 AND、各条件はシノニム OR）
    for 条件 in フィルター.get("条件リスト") or []:
        節, 値 = _シノニムLIKE句(
            columns.条件検索カラム一覧,
            str(条件),
            条件シノニム辞書,
        )
        WHERE条件.append(節)
        WHEREパラメータ.extend(値)

    # 除外キーワード（AND NOT）— カテゴリに応じてアクセサリー語を除外する
    # 例：「包丁」検索時に「シャープナー」「包丁ケース」「ホルダー」を含む商品は除外
    除外列一覧 = ["小カテゴリ", "アスパック商品名", "メーカー正式商品名"]
    for 除外語 in フィルター.get("除外キーワード") or []:
        除外OR = " OR ".join(
            f"COALESCE(`{c}`, '') LIKE %s COLLATE utf8mb4_bin"
            for c in 除外列一覧
        )
        WHERE条件.append(f"NOT ({除外OR})")
        WHEREパラメータ.extend([f"%{除外語}%"] * len(除外列一覧))

    # 価格範囲
    if フィルター.get("最大価格"):
        WHERE条件.append("`売価(税込)` <= %s")
        WHEREパラメータ.append(フィルター["最大価格"])
    if フィルター.get("最小価格"):
        WHERE条件.append("`売価(税込)` >= %s")
        WHEREパラメータ.append(フィルター["最小価格"])

    # ── 補助シグナル（用途・キーワード・季節）──
    # カテゴリ・カラー・キャラ等の絞り込みが全く無い場合に限り、
    # キーワード/用途を WHERE 必須にする（全件返しを防ぐ）。
    強い絞り込みあり = (
        カテゴリ指定あり
        or bool(フィルター.get("カラー"))
        or bool(フィルター.get("キャラクター"))
        or bool(フィルター.get("条件リスト") or [])
    )

    if not 強い絞り込みあり:
        最低限句一覧: List[str] = []
        最低限パラメータ: List[Any] = []
        if フィルター.get("用途"):
            節, 値 = _LIKE_句(columns.用途検索カラム一覧, str(フィルター["用途"]))
            最低限句一覧.append(節)
            最低限パラメータ.extend(値)
        for kw in フィルター.get("キーワードリスト") or []:
            節, 値 = _LIKE_句(columns.キーワード検索カラム一覧, str(kw))
            最低限句一覧.append(節)
            最低限パラメータ.extend(値)
        if フィルター.get("季節"):
            節, 値 = _LIKE_句(
                ["キーワード1", "キーワード2", "サブキーワード", "商品説明"],
                str(フィルター["季節"]),
            )
            最低限句一覧.append(節)
            最低限パラメータ.extend(値)
        if 最低限句一覧:
            WHERE条件.append("(" + " OR ".join(最低限句一覧) + ")")
            WHEREパラメータ.extend(最低限パラメータ)

    WHERE句 = " AND ".join(WHERE条件)

    # ── ORDER BY ──
    # 1) **属性列直接一致**を最優先
    #    カラー/キャラクター を指定したら「カラー列・キャラクター列にズバリ書いてある商品」を上位に。
    #    商品名や説明にうっすら混ざってる程度の商品より、属性列で答えている商品を優先する。
    # 2) 関連度スコア（補助シグナルの一致個数）
    # 3) 重点商品 → 発注ランク
    # 4) 在庫 → 登録日
    属性優先式一覧: List[str] = []
    属性優先パラメータ: List[Any] = []
    カラー値 = フィルター.get("カラー")
    if カラー値:
        候補語 = _シノニム拡張(str(カラー値), カラーシノニム辞書)
        条件群 = " OR ".join(["`カラー` LIKE %s COLLATE utf8mb4_bin"] * len(候補語))
        属性優先式一覧.append(f"(CASE WHEN ({条件群}) THEN 1 ELSE 0 END)")
        属性優先パラメータ.extend([f"%{語}%" for 語 in 候補語])
    キャラクター値 = フィルター.get("キャラクター")
    if キャラクター値:
        候補語 = _シノニム拡張(str(キャラクター値), キャラクターシノニム辞書)
        条件群 = " OR ".join(["`キャラクター` LIKE %s COLLATE utf8mb4_bin"] * len(候補語))
        属性優先式一覧.append(f"(CASE WHEN ({条件群}) THEN 1 ELSE 0 END)")
        属性優先パラメータ.extend([f"%{語}%" for 語 in 候補語])

    # 属性優先式が空（カラー/キャラ未指定）なら ORDER BY に含めない。
    # （MariaDB は ORDER BY の裸数値リテラルを列インデックスとして解釈してしまうため）
    属性優先式_あり = bool(属性優先式一覧)
    属性優先式 = "(" + " + ".join(属性優先式一覧) + ")" if 属性優先式_あり else None

    # ── 本体色純度スコア ──
    # 「黒い包丁」→ メーカー正式商品名 に「セラミック/漆黒/ナチュラルブラック...」が
    # あれば +10ずつ、「ステンレス製ブラック/カラーハンドル」が
    # あれば -5ずつ。これでカラー="ブラック" でも 黒柄(=刃は銀) の商品を
    # 本物の黒刃商品の下に押し下げる。
    本体色純度式: str | None = None
    本体色純度パラメータ: List[Any] = []
    プラス語一覧 = フィルター.get("本体色強指標") or []
    マイナス語一覧 = フィルター.get("柄色強指標") or []
    if プラス語一覧 or マイナス語一覧:
        部分式: List[str] = []
        for 語 in プラス語一覧:
            部分式.append(
                "(CASE WHEN `メーカー正式商品名` LIKE %s COLLATE utf8mb4_bin "
                "THEN 10 ELSE 0 END)"
            )
            本体色純度パラメータ.append(f"%{語}%")
        for 語 in マイナス語一覧:
            部分式.append(
                "(CASE WHEN `メーカー正式商品名` LIKE %s COLLATE utf8mb4_bin "
                "THEN -5 ELSE 0 END)"
            )
            本体色純度パラメータ.append(f"%{語}%")
        本体色純度式 = "(" + " + ".join(部分式) + ")"

    スコア式, スコアパラメータ = _関連度スコア句(フィルター)
    ORDER_BY_部分 = []
    if 本体色純度式:
        ORDER_BY_部分.append(f"{本体色純度式} DESC")
    if 属性優先式_あり:
        ORDER_BY_部分.append(f"{属性優先式} DESC")
    ORDER_BY_部分.append(f"{スコア式} DESC")
    ORDER_BY_部分.append(columns.ランクORDER_SQL)
    ORDER_BY_部分.append("`有効在庫数` DESC, `アスパック登録日` DESC")
    ORDER_BY = ", ".join(ORDER_BY_部分)

    # 取得件数。属性列に直接書いてる本物の該当商品を漏らさないため、要求の5倍取得する。
    要求件数 = max(1, min(int(フィルター.get("提案件数", 5)), 30))

    if 属性優先式_あり:
        SQL = f"""
            SELECT
                {columns.一覧表示SELECT句},
                {スコア式} AS _関連度,
                {属性優先式} AS _属性優先
            FROM `{columns.テーブル名}`
            WHERE {WHERE句}
            ORDER BY {ORDER_BY}
            LIMIT {要求件数 * 5}
        """
        # %s 出現順: SELECT(スコア式 → 属性優先式) → WHERE → ORDER BY(本体色純度? → 属性優先式 → スコア式)
        パラメータ = (
            スコアパラメータ
            + 属性優先パラメータ
            + WHEREパラメータ
            + 本体色純度パラメータ
            + 属性優先パラメータ
            + スコアパラメータ
        )
    else:
        SQL = f"""
            SELECT
                {columns.一覧表示SELECT句},
                {スコア式} AS _関連度
            FROM `{columns.テーブル名}`
            WHERE {WHERE句}
            ORDER BY {ORDER_BY}
            LIMIT {要求件数 * 5}
        """
        # %s 出現順: SELECT(スコア式) → WHERE → ORDER BY(本体色純度? → スコア式)
        パラメータ = (
            スコアパラメータ
            + WHEREパラメータ
            + 本体色純度パラメータ
            + スコアパラメータ
        )

    with 辞書カーソル() as カーソル:
        カーソル.execute(SQL, パラメータ)
        行一覧 = list(カーソル.fetchall())

    # スコア==0 の行をふるい落とすのは「強い絞り込み (カラー/キャラクター/条件) が
    # 一つもなく、キーワードや用途しかない」場合だけ。強い絞り込みが効いていれば
    # キーワードの含有数が 0 でも該当商品である可能性が高い（例：商品名が全てカタカナ
    # で「包丁」漢字が一切ない黒色包丁）。
    強い絞り込みあり_for_filter = (
        bool(フィルター.get("カテゴリ"))
        or bool(フィルター.get("カラー"))
        or bool(フィルター.get("キャラクター"))
        or bool(フィルター.get("条件リスト") or [])
    )
    if not 強い絞り込みあり_for_filter:
        補助シグナルあり = bool(
            フィルター.get("用途")
            or (フィルター.get("キーワードリスト") or [])
        )
        if 補助シグナルあり:
            行一覧 = [r for r in 行一覧 if (r.get("_関連度") or 0) > 0]

    # 内部用列を落として、要求件数まで返す
    for r in 行一覧:
        r.pop("_関連度", None)
        r.pop("_属性優先", None)

    return 行一覧[:要求件数]


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
