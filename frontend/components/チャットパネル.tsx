"use client";
import { useState, useRef, useEffect } from "react";
import {
  X, Send, Bot, User, Package,
  ChevronDown, CheckCircle, Loader, AlertCircle,
} from "lucide-react";

// ─────────────────────────────────────────────
// 型定義
// ─────────────────────────────────────────────
interface 商品型 {
  商品コード: string;
  商品名: string;
  メーカー名: string;
  カテゴリ: string;
  サブカテゴリ: string;
  卸価格_税抜: number;
  参考売価_税抜: number;
  商品特徴: string;
  画像URL: string;
  在庫数: number;
  販売ランク: number;
}

interface 処理ステップ型 {
  ステップ: number;
  処理名: string;
  状態: "処理中" | "完了" | "エラー";
  件数?: string;
  抽出結果?: Record<string, unknown>;
}

interface メッセージ型 {
  役割: "ユーザー" | "AI";
  内容: string;
  商品リスト?: 商品型[];
  フィルター?: Record<string, unknown>;
  処理ログ?: 処理ステップ型[];
  エラー?: boolean;
}

// ─────────────────────────────────────────────
// 既定サジェスト（API取得に失敗した場合のフォールバック）
// ─────────────────────────────────────────────
const 既定サジェスト一覧 = [
  "キッチンで使えるまな板を3点",
  "在庫の多いゴミ箱を5つ",
  "ステンレス製のハンガーを4個",
  "折りたたみのレジャーチェアを5点",
];

// ─────────────────────────────────────────────
// フィルター表示用ラベル
// ─────────────────────────────────────────────
const フィルターラベル: Record<string, string> = {
  カテゴリ: "カテゴリ",
  用途: "用途",
  条件リスト: "条件",
  キーワードリスト: "キーワード",
  季節: "季節",
  最大価格: "上限価格",
  最小価格: "下限価格",
  提案件数: "提案数",
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "";
const API_BASE候補 = [
  API_BASE_URL,
  "http://127.0.0.1:8000",
  "http://localhost:8000",
].filter(Boolean);

// ─────────────────────────────────────────────
// チャットパネル本体
// ─────────────────────────────────────────────
export default function チャットパネル({ 閉じる }: { 閉じる: () => void }) {
  const [メッセージ一覧, setメッセージ一覧] = useState<メッセージ型[]>([
    {
      役割: "AI",
      内容:
        "こんにちは！商品提案AIアシスタントです。\n\n" +
        "探している商品や提案したい企画をご入力ください。\n" +
        "データベースから最適な商品をご提案します。\n\n" +
        "例：「キッチンで使う分別ゴミ箱を提案してください」",
    },
  ]);
  const [入力テキスト, set入力テキスト] = useState("");
  const [送信中, set送信中] = useState(false);
  const [商品説明生成中コード, set商品説明生成中コード] = useState<string | null>(null);
  const [フィルター展開中インデックス, setフィルター展開中インデックス] = useState<number | null>(null);
  const [サジェスト一覧, setサジェスト一覧] = useState<string[]>(既定サジェスト一覧);
  const [サジェスト読み込み中, setサジェスト読み込み中] = useState(true);
  const [AI状態, setAI状態] = useState<{
    有効: boolean | null;
    状態コード?: string;
    人間向けメッセージ?: string;
    詳細?: string;
  }>({ 有効: null });
  const [AI状態読み込み中, setAI状態読み込み中] = useState(false);
  const [AI状態警告閉じた, setAI状態警告閉じた] = useState(false);
  const 末尾参照 = useRef<HTMLDivElement>(null);
  const 入力参照 = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    末尾参照.current?.scrollIntoView({ behavior: "smooth" });
  }, [メッセージ一覧, 送信中]);

  // ─── サジェストを動的に取得 ───
  useEffect(() => {
    let 破棄 = false;
    const 取得 = async () => {
      const パス = `/api/${encodeURIComponent("サジェスト")}?${encodeURIComponent("件数")}=4`;
      for (const base of API_BASE候補) {
        try {
          const レスポンス = await fetch(`${base}${パス}`, {
            method: "GET",
            cache: "no-store",
            headers: {
              ...(base.includes("ngrok") ? { "ngrok-skip-browser-warning": "true" } : {}),
            },
          });
          if (!レスポンス.ok) continue;
          const データ = await レスポンス.json();
          const 一覧 = Array.isArray(データ?.サジェスト一覧) ? データ.サジェスト一覧 : [];
          if (!破棄 && 一覧.length > 0) {
            setサジェスト一覧(一覧);
          }
          return;
        } catch {
          // 次候補へ
        }
      }
    };
    取得().finally(() => {
      if (!破棄) setサジェスト読み込み中(false);
    });
    return () => {
      破棄 = true;
    };
  }, []);

  // ─── AI接続状態をチェック ───
  const AI状態を確認 = async (再確認: boolean) => {
    setAI状態読み込み中(true);
    const クエリ = 再確認 ? `?${encodeURIComponent("再確認")}=true` : "";
    const パス = `/api/${encodeURIComponent("AI状態")}${クエリ}`;
    for (const base of API_BASE候補) {
      try {
        const レスポンス = await fetch(`${base}${パス}`, {
          method: "GET",
          cache: "no-store",
          headers: {
            ...(base.includes("ngrok") ? { "ngrok-skip-browser-warning": "true" } : {}),
          },
        });
        if (!レスポンス.ok) continue;
        const データ = await レスポンス.json();
        setAI状態({
          有効: !!データ?.有効,
          状態コード: データ?.状態コード,
          人間向けメッセージ: データ?.人間向けメッセージ,
          詳細: データ?.詳細,
        });
        if (データ?.有効) setAI状態警告閉じた(false);
        break;
      } catch {
        // 次候補へ
      }
    }
    setAI状態読み込み中(false);
  };

  useEffect(() => {
    AI状態を確認(false);
    const intervalId = setInterval(() => AI状態を確認(false), 60_000);
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const サジェスト再読み込み = async () => {
    setサジェスト読み込み中(true);
    const パス = `/api/${encodeURIComponent("サジェスト")}?${encodeURIComponent("件数")}=4&_t=${Date.now()}`;
    for (const base of API_BASE候補) {
      try {
        const レスポンス = await fetch(`${base}${パス}`, {
          method: "GET",
          cache: "no-store",
          headers: {
            ...(base.includes("ngrok") ? { "ngrok-skip-browser-warning": "true" } : {}),
          },
        });
        if (!レスポンス.ok) continue;
        const データ = await レスポンス.json();
        const 一覧 = Array.isArray(データ?.サジェスト一覧) ? データ.サジェスト一覧 : [];
        if (一覧.length > 0) setサジェスト一覧(一覧);
        break;
      } catch {
        // 次候補へ
      }
    }
    setサジェスト読み込み中(false);
  };

  // ─── メッセージ送信 ───
  const メッセージ送信 = async (テキスト?: string) => {
    const 送信テキスト = テキスト || 入力テキスト.trim();
    if (!送信テキスト || 送信中) return;
    set入力テキスト("");

    const ユーザーメッセージ: メッセージ型 = { 役割: "ユーザー", 内容: 送信テキスト };
    setメッセージ一覧(前 => [...前, ユーザーメッセージ]);
    set送信中(true);

    try {
      let レスポンス: Response | null = null;
      let 最終エラー: unknown = null;
      for (const base of API_BASE候補) {
        try {
          レスポンス = await fetch(`${base}/api/チャット`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(base.includes("ngrok") ? { "ngrok-skip-browser-warning": "true" } : {}),
            },
            body: JSON.stringify({ メッセージ: 送信テキスト, 会話履歴: [] }),
          });
          if (レスポンス.ok) break;
        } catch (e) {
          最終エラー = e;
        }
      }

      if (!レスポンス || !レスポンス.ok) {
        throw new Error(最終エラー ? "接続エラー" : `HTTPエラー ${レスポンス?.status}`);
      }
      const データ = await レスポンス.json();

      const AIメッセージ: メッセージ型 = {
        役割: "AI",
        内容: データ.回答,
        商品リスト: データ.提案商品リスト,
        フィルター: データ.使用フィルター,
        処理ログ: データ.処理ステップログ,
      };
      setメッセージ一覧(前 => [...前, AIメッセージ]);

    } catch {
      setメッセージ一覧(前 => [
        ...前,
        {
          役割: "AI",
          内容: `申し訳ございません。エラーが発生しました。\nバックエンドサーバーが起動しているかご確認ください。\n（${API_BASE_URL || "同一オリジン /api"}）`,
          エラー: true,
        },
      ]);
    } finally {
      set送信中(false);
    }
  };

  const キー入力処理 = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      メッセージ送信();
    }
  };

  const 直近ユーザー入力取得 = (AIメッセージindex: number) => {
    for (let i = AIメッセージindex - 1; i >= 0; i -= 1) {
      if (メッセージ一覧[i]?.役割 === "ユーザー") return メッセージ一覧[i].内容;
    }
    return "";
  };

  const 商品クリック時説明生成 = async (商品: 商品型, AIメッセージindex: number, 使用フィルター?: Record<string, unknown>) => {
    if (商品説明生成中コード) return;
    set商品説明生成中コード(商品.商品コード);

    try {
      const ユーザー入力 = 直近ユーザー入力取得(AIメッセージindex);
      let レスポンス: Response | null = null;
      for (const base of API_BASE候補) {
        try {
          レスポンス = await fetch(`${base}/api/商品説明生成`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(base.includes("ngrok") ? { "ngrok-skip-browser-warning": "true" } : {}),
            },
            body: JSON.stringify({
              ユーザー入力,
              商品情報: 商品,
              使用フィルター: 使用フィルター || {},
            }),
          });
          if (レスポンス.ok) break;
        } catch {
          // 次候補へ
        }
      }

      if (!レスポンス || !レスポンス.ok) throw new Error(`HTTPエラー ${レスポンス?.status}`);
      const データ = await レスポンス.json();
      const 返信: メッセージ型 = {
        役割: "AI",
        内容: `【${商品.商品名}】\n${データ.回答}`,
      };
      setメッセージ一覧(前 => [...前, 返信]);
    } catch {
      setメッセージ一覧(前 => [
        ...前,
        {
          役割: "AI",
          内容: "商品説明の生成中にエラーが発生しました。しばらくしてから再度お試しください。",
          エラー: true,
        },
      ]);
    } finally {
      set商品説明生成中コード(null);
    }
  };

  // ─────────────────────────────────────────────
  // レンダリング
  // ─────────────────────────────────────────────
  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      background: "#fff", fontFamily: "'Noto Sans JP', sans-serif",
    }}>

      {/* ─── ヘッダー ─── */}
      <div style={{
        padding: "13px 18px",
        background: "linear-gradient(135deg, var(--紺), var(--青))",
        display: "flex", alignItems: "center", gap: 10, flexShrink: 0,
      }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10, flexShrink: 0,
          background: "rgba(255,255,255,0.15)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Bot size={18} style={{ color: "#fff" }} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ color: "#fff", fontWeight: 700, fontSize: 14 }}>商品提案 AI</div>
          <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 11 }}>
            フェーズ① 社内チャットボット
          </div>
        </div>
        <button
          onClick={閉じる}
          style={{
            background: "rgba(255,255,255,0.12)", border: "none", borderRadius: 8,
            width: 32, height: 32,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", color: "rgba(255,255,255,0.7)",
            transition: "background 0.15s",
          }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.22)")}
          onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0.12)")}
        >
          <X size={15} />
        </button>
      </div>

      {/* ─── AI接続警告バナー ─── */}
      {AI状態.有効 === false && !AI状態警告閉じた && (
        <div style={{
          background: "#fef3c7",
          borderBottom: "1px solid #f59e0b",
          padding: "10px 14px",
          display: "flex", alignItems: "flex-start", gap: 10,
          fontSize: 12, color: "#92400e",
          flexShrink: 0,
        }}>
          <AlertCircle size={16} style={{ color: "#b45309", flexShrink: 0, marginTop: 1 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, marginBottom: 2 }}>
              AI接続停止中（{AI状態.状態コード || "ERROR"}）
            </div>
            <div style={{ lineHeight: 1.5 }}>
              {AI状態.人間向けメッセージ || "AI生成が一時的に利用できません。"}
              {" "}
              データベース検索は動作しており、商品提案はそのままご利用いただけます。
            </div>
            {AI状態.詳細 && (
              <div style={{
                marginTop: 4, fontSize: 10, color: "#78350f", opacity: 0.85,
                whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}>
                詳細：{AI状態.詳細}
              </div>
            )}
            <button
              onClick={() => AI状態を確認(true)}
              disabled={AI状態読み込み中}
              style={{
                marginTop: 6,
                background: "#b45309", color: "#fff",
                border: "none", borderRadius: 6,
                padding: "3px 10px", fontSize: 11, fontWeight: 600,
                cursor: AI状態読み込み中 ? "wait" : "pointer",
                fontFamily: "'Noto Sans JP', sans-serif",
                opacity: AI状態読み込み中 ? 0.7 : 1,
                display: "inline-flex", alignItems: "center", gap: 4,
              }}
            >
              <Loader
                size={11}
                style={{
                  animation: AI状態読み込み中 ? "回転 1s linear infinite" : "none",
                }}
              />
              {AI状態読み込み中 ? "再確認中..." : "再確認"}
            </button>
          </div>
          <button
            onClick={() => setAI状態警告閉じた(true)}
            title="このメッセージを閉じる"
            style={{
              background: "none", border: "none", padding: 2, cursor: "pointer",
              color: "#92400e", lineHeight: 0, flexShrink: 0,
            }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* ─── メッセージ一覧 ─── */}
      <div style={{ flex: 1, overflow: "auto", padding: "14px" }}>

        {メッセージ一覧.map((メッセージ, インデックス) => (
          <div
            key={インデックス}
            className="メッセージ表示"
            style={{
              marginBottom: 16,
              display: "flex", flexDirection: "column",
              alignItems: メッセージ.役割 === "ユーザー" ? "flex-end" : "flex-start",
            }}
          >
            {/* アバター＋バブル */}
            <div style={{
              display: "flex", gap: 8, alignItems: "flex-end",
              maxWidth: "90%",
              flexDirection: メッセージ.役割 === "ユーザー" ? "row-reverse" : "row",
            }}>
              {/* アバター */}
              <div style={{
                width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
                background: メッセージ.役割 === "ユーザー"
                  ? "linear-gradient(135deg, var(--青明), var(--緑))"
                  : "linear-gradient(135deg, var(--紺), var(--青))",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                {メッセージ.役割 === "ユーザー"
                  ? <User size={12} style={{ color: "#fff" }} />
                  : <Bot  size={12} style={{ color: "#fff" }} />}
              </div>

              {/* メッセージバブル */}
              <div style={{
                background: メッセージ.役割 === "ユーザー"
                  ? "var(--紺)"
                  : メッセージ.エラー ? "#fef2f2" : "var(--表面)",
                color: メッセージ.役割 === "ユーザー"
                  ? "#fff"
                  : メッセージ.エラー ? "#dc2626" : "var(--文字主)",
                border: メッセージ.役割 === "ユーザー"
                  ? "none"
                  : `1px solid ${メッセージ.エラー ? "#fecaca" : "var(--境界線)"}`,
                borderRadius: メッセージ.役割 === "ユーザー"
                  ? "16px 16px 4px 16px"
                  : "16px 16px 16px 4px",
                padding: "10px 14px",
                fontSize: 13,
                lineHeight: 1.7,
                whiteSpace: "pre-wrap",
              }}>
                {メッセージ.エラー && (
                  <AlertCircle size={13} style={{ display: "inline", marginRight: 4 }} />
                )}
                {メッセージ.内容}
              </div>
            </div>

            {/* 処理ステップログ */}
            {メッセージ.処理ログ && メッセージ.処理ログ.length > 0 && (
              <div style={{
                marginTop: 8, marginLeft: 36,
                display: "flex", flexDirection: "column", gap: 4,
              }}>
                {メッセージ.処理ログ.map((ステップ, si) => (
                  <div key={si} className="ステップ完了" style={{
                    display: "flex", alignItems: "center", gap: 6,
                    fontSize: 11, color: "var(--緑)",
                  }}>
                    <CheckCircle size={11} style={{ color: "var(--緑)", flexShrink: 0 }} />
                    <span style={{ fontWeight: 500 }}>
                      ステップ{ステップ.ステップ}：{ステップ.処理名}
                    </span>
                    {ステップ.件数 && (
                      <span style={{ color: "var(--文字薄)" }}>— {ステップ.件数}</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 使用フィルター（展開/折りたたみ） */}
            {メッセージ.フィルター &&
              Object.values(メッセージ.フィルター).some(v => v && (!Array.isArray(v) || v.length > 0)) && (
              <div style={{ marginTop: 6, marginLeft: 36 }}>
                <button
                  onClick={() =>
                    setフィルター展開中インデックス(
                      フィルター展開中インデックス === インデックス ? null : インデックス
                    )
                  }
                  style={{
                    display: "flex", alignItems: "center", gap: 4,
                    background: "none", border: "none", cursor: "pointer",
                    color: "var(--青明)", fontSize: 11, fontWeight: 600, padding: 0,
                    fontFamily: "'Noto Sans JP', sans-serif",
                  }}
                >
                  抽出フィルターを確認
                  <ChevronDown
                    size={11}
                    style={{
                      transform: フィルター展開中インデックス === インデックス
                        ? "rotate(180deg)" : "none",
                      transition: "transform 0.2s",
                    }}
                  />
                </button>

                {フィルター展開中インデックス === インデックス && (
                  <div className="フェードイン" style={{
                    marginTop: 6,
                    background: "var(--表面2)", border: "1px solid var(--境界線)",
                    borderRadius: 8, padding: "10px 12px",
                    display: "flex", flexWrap: "wrap", gap: 6,
                  }}>
                    {Object.entries(メッセージ.フィルター).map(([キー, 値]) => {
                      if (!値 || (Array.isArray(値) && !値.length)) return null;
                      const 表示値 = Array.isArray(値) ? 値.join("、") : String(値);
                      return (
                        <div key={キー} style={{
                          background: "#fff", border: "1px solid var(--境界線)",
                          borderRadius: 6, padding: "3px 8px", fontSize: 11,
                          display: "flex", gap: 4,
                        }}>
                          <span style={{ color: "var(--文字薄)" }}>
                            {フィルターラベル[キー] || キー}：
                          </span>
                          <span style={{ color: "var(--紺)", fontWeight: 600 }}>
                            {表示値}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* 商品カード一覧 */}
            {メッセージ.商品リスト && メッセージ.商品リスト.length > 0 && (
              <div style={{
                marginTop: 10, marginLeft: 36,
                display: "flex", flexDirection: "column", gap: 8,
                width: "calc(100% - 36px)",
              }}>
                <div style={{ fontSize: 11, color: "var(--文字薄)", fontWeight: 600 }}>
                  📦 提案商品一覧（{メッセージ.商品リスト.length}件）
                </div>
                <div style={{ fontSize: 10, color: "var(--文字薄)" }}>
                  ※ 商品カードをクリックすると、商品説明とおすすめ理由を生成します
                </div>

                {メッセージ.商品リスト.map((商品, pi) => (
                  <div
                    key={pi}
                    className="商品カード"
                    onClick={() => 商品クリック時説明生成(商品, インデックス, メッセージ.フィルター)}
                    style={{
                    background: "#fff", border: "1px solid var(--境界線)",
                    borderRadius: 10, padding: "12px",
                    display: "flex", gap: 10,
                    boxShadow: "0 1px 3px rgba(15,31,61,0.04)",
                    cursor: "pointer",
                    opacity: 商品説明生成中コード === 商品.商品コード ? 0.65 : 1,
                    pointerEvents: 商品説明生成中コード ? "none" : "auto",
                  }}>
                    {/* 商品画像 */}
                    <div style={{
                      width: 56, height: 56, borderRadius: 8, flexShrink: 0,
                      background: "var(--表面2)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      overflow: "hidden",
                    }}>
                      {商品.画像URL ? (
                        <img
                          src={商品.画像URL}
                          alt={商品.商品名}
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                          onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                      ) : (
                        <Package size={20} style={{ color: "var(--文字薄)" }} />
                      )}
                    </div>

                    {/* 商品情報 */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 12, fontWeight: 700, color: "var(--紺)",
                        whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                      }}>
                        {商品.商品名}
                        {商品説明生成中コード === 商品.商品コード && (
                          <span style={{ fontSize: 10, color: "var(--文字薄)", marginLeft: 6 }}>
                            （生成中...）
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 10, color: "var(--文字薄)", marginTop: 2 }}>
                        {商品.メーカー名}　·　{商品.カテゴリ}
                      </div>

                      {/* 価格情報 */}
                      <div style={{
                        marginTop: 6, display: "flex", gap: 10, alignItems: "baseline",
                      }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "var(--青)" }}>
                          ¥{商品.卸価格_税抜?.toLocaleString()}
                          <span style={{ fontSize: 10, fontWeight: 400, color: "var(--文字薄)" }}>
                            　卸価格（税抜）
                          </span>
                        </div>
                        <div style={{ fontSize: 10, color: "var(--文字薄)" }}>
                          売価 ¥{商品.参考売価_税抜?.toLocaleString()}
                        </div>
                      </div>

                      {/* バッジ */}
                      <div style={{ marginTop: 5, display: "flex", gap: 5, flexWrap: "wrap" }}>
                        <span style={{
                          background: "var(--表面2)", borderRadius: 4,
                          padding: "1px 7px", fontSize: 10, color: "var(--文字副)",
                        }}>
                          在庫：{商品.在庫数}点
                        </span>
                        <span style={{
                          background: "rgba(0,201,167,0.1)", borderRadius: 4,
                          padding: "1px 7px", fontSize: 10,
                          color: "var(--緑)", fontWeight: 600,
                        }}>
                          人気ランク #{商品.販売ランク}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* ─── 送信中インジケーター ─── */}
        {送信中 && (
          <div className="メッセージ表示" style={{
            display: "flex", gap: 8, alignItems: "flex-end", marginBottom: 16,
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
              background: "linear-gradient(135deg, var(--紺), var(--青))",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Bot size={12} style={{ color: "#fff" }} />
            </div>
            <div style={{
              background: "var(--表面)", border: "1px solid var(--境界線)",
              borderRadius: "16px 16px 16px 4px",
              padding: "12px 16px",
              display: "flex", flexDirection: "column", gap: 8,
            }}>
              <div style={{ display: "flex", gap: 4 }}>
                <span className="タイピングドット" />
                <span className="タイピングドット" />
                <span className="タイピングドット" />
              </div>
              <div style={{
                display: "flex", alignItems: "center", gap: 5,
                fontSize: 10, color: "var(--文字薄)",
              }}>
                <Loader
                  size={10}
                  style={{ animation: "回転 1s linear infinite" }}
                />
                AIが分析・検索中...
              </div>
            </div>
          </div>
        )}

        <div ref={末尾参照} />
      </div>

      {/* ─── サジェストボタン（DBから動的生成） ─── */}
      {メッセージ一覧.length <= 1 && (
        <div style={{ padding: "0 14px 10px" }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            marginBottom: 6,
          }}>
            <span style={{ fontSize: 10, color: "var(--文字薄)", fontWeight: 600 }}>
              おすすめの聞き方
              {サジェスト読み込み中 && (
                <span style={{ marginLeft: 6, color: "var(--文字薄)" }}>読み込み中...</span>
              )}
            </span>
            <button
              onClick={サジェスト再読み込み}
              disabled={サジェスト読み込み中}
              title="サジェストを更新"
              style={{
                background: "none", border: "none", padding: 0, cursor: "pointer",
                color: "var(--青明)", fontSize: 10, fontWeight: 600,
                fontFamily: "'Noto Sans JP', sans-serif",
                opacity: サジェスト読み込み中 ? 0.5 : 1,
              }}
            >
              <Loader
                size={11}
                style={{
                  display: "inline", verticalAlign: "middle", marginRight: 3,
                  animation: サジェスト読み込み中 ? "回転 1s linear infinite" : "none",
                }}
              />
              更新
            </button>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {サジェスト一覧.map((サジェスト, i) => (
              <button
                key={`${i}-${サジェスト}`}
                onClick={() => メッセージ送信(サジェスト)}
                disabled={サジェスト読み込み中}
                style={{
                  background: "var(--表面2)", border: "1px solid var(--境界線)",
                  borderRadius: 20, padding: "5px 12px",
                  fontSize: 11, color: "var(--文字副)", cursor: "pointer", fontWeight: 500,
                  fontFamily: "'Noto Sans JP', sans-serif",
                  transition: "all 0.15s ease",
                  opacity: サジェスト読み込み中 ? 0.6 : 1,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = "var(--青)";
                  e.currentTarget.style.color = "#fff";
                  e.currentTarget.style.borderColor = "var(--青)";
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = "var(--表面2)";
                  e.currentTarget.style.color = "var(--文字副)";
                  e.currentTarget.style.borderColor = "var(--境界線)";
                }}
              >
                {サジェスト}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ─── 入力エリア ─── */}
      <div style={{
        padding: "10px 14px 14px",
        borderTop: "1px solid var(--境界線)",
        background: "#fff", flexShrink: 0,
      }}>
        <div
          style={{
            display: "flex", gap: 8, alignItems: "flex-end",
            background: "var(--表面)", border: "2px solid var(--境界線)",
            borderRadius: 14, padding: "8px 8px 8px 14px",
            transition: "border-color 0.2s",
          }}
          onFocusCapture={e => (e.currentTarget.style.borderColor = "var(--青明)")}
          onBlurCapture={e  => (e.currentTarget.style.borderColor = "var(--境界線)")}
        >
          <textarea
            ref={入力参照}
            value={入力テキスト}
            onChange={e => set入力テキスト(e.target.value)}
            onKeyDown={キー入力処理}
            placeholder={"商品の条件を入力...\n例：春のレジャー向けの商品を10個提案してください"}
            rows={2}
            style={{
              flex: 1, background: "none", border: "none", outline: "none",
              resize: "none", fontSize: 13,
              fontFamily: "'Noto Sans JP', sans-serif",
              color: "var(--文字主)", lineHeight: 1.6,
              maxHeight: 120, overflowY: "auto",
            }}
          />
          <button
            onClick={() => メッセージ送信()}
            disabled={!入力テキスト.trim() || 送信中}
            style={{
              width: 36, height: 36, borderRadius: 10, flexShrink: 0,
              background: 入力テキスト.trim() && !送信中 ? "var(--紺)" : "var(--境界線)",
              border: "none",
              cursor: 入力テキスト.trim() && !送信中 ? "pointer" : "not-allowed",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "all 0.2s ease",
            }}
          >
            <Send
              size={14}
              style={{ color: 入力テキスト.trim() && !送信中 ? "#fff" : "var(--文字薄)" }}
            />
          </button>
        </div>
        <div style={{
          fontSize: 10, color: "var(--文字薄)", marginTop: 6, textAlign: "center",
        }}>
          Enterで送信　·　Shift+Enterで改行　·　商品マスターのみを参照します
        </div>
      </div>

      <style>{`
        @keyframes 回転 { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
