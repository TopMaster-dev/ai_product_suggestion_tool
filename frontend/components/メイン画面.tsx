"use client";
import { useEffect, useRef, useState } from "react";
import { MessageSquare, Package, TrendingUp, Users, Zap, ArrowRight } from "lucide-react";

interface プロップス {
  チャットを開く: () => void;
  チャット中: boolean;
  モバイル?: boolean;
}

const 統計データ = [
  { ラベル: "総商品数",         値: "120,000+", 補足: "今月 +2,847点増加", アイコン: Package,       色: "#1e4d8c" },
  { ラベル: "本日の提案件数",   値: "7",        補足: "目標 10件",         アイコン: TrendingUp,    色: "#00c9a7" },
  { ラベル: "AI検索回数（今日）", 値: "23",     補足: "前日比 +12%",      アイコン: Zap,           色: "#f59e0b" },
  { ラベル: "利用中ユーザー数", 値: "18",       補足: "社内100名中",       アイコン: Users,         色: "#8b5cf6" },
];

const 最近の検索履歴 = [
  { 検索内容: "春のレジャー向け商品を10個提案してください", 時間: "10分前", 件数: 8 },
  { 検索内容: "食洗機に対応したプラスチックのまな板",       時間: "32分前", 件数: 5 },
  { 検索内容: "キッチン用の分別ゴミ箱",                   時間: "1時間前",件数: 6 },
  { 検索内容: "折りたたみ式の収納ボックス",               時間: "2時間前", 件数: 4 },
];

export default function メイン画面({ チャットを開く, チャット中, モバイル = false }: プロップス) {
  const [システム稼働中, setシステム稼働中] = useState(false);
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "";
  const API_BASE候補 = [
    API_BASE_URL,
    "http://127.0.0.1:8000",
    "http://localhost:8000",
  ].filter(Boolean);
  const 連続失敗回数 = useRef(0);

  useEffect(() => {
    let 破棄済み = false;

    const 稼働確認 = async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 5000);
      try {
        let 稼働判定 = false;
        for (const base of API_BASE候補) {
          try {
            const レスポンス = await fetch(`${base}/api/ヘルスチェック`, {
              method: "GET",
              signal: controller.signal,
              cache: "no-store",
              headers: {
                ...(base.includes("ngrok") ? { "ngrok-skip-browser-warning": "true" } : {}),
                "Cache-Control": "no-cache",
                Pragma: "no-cache",
              },
            });
            if (!レスポンス.ok) continue;
            const データ = await レスポンス.json();
            const 状態文字列 = String(データ?.状態 || "");
            稼働判定 = 状態文字列.includes("正常") || 状態文字列.includes("稼働");
            if (稼働判定) break;
          } catch {
            // 次候補へ
          }
        }

        if (稼働判定) {
          連続失敗回数.current = 0;
          if (!破棄済み) setシステム稼働中(true);
        } else {
          連続失敗回数.current += 1;
          if (連続失敗回数.current >= 2 && !破棄済み) setシステム稼働中(false);
        }
      } catch {
        連続失敗回数.current += 1;
        if (連続失敗回数.current >= 2 && !破棄済み) setシステム稼働中(false);
      } finally {
        clearTimeout(timer);
      }
    };

    稼働確認();
    const intervalId = setInterval(稼働確認, 15000);
    return () => {
      破棄済み = true;
      clearInterval(intervalId);
    };
  }, [API_BASE_URL]);

  return (
    <div style={{ padding: モバイル ? "16px 14px" : "28px 30px", minHeight: "100vh", background: "var(--表面)" }}>

      {/* ヘッダー */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: モバイル ? "flex-start" : "center", justifyContent: "space-between", gap: 8 }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: "var(--紺)", letterSpacing: "-0.01em" }}>
              商品提案ダッシュボード
            </h1>
            <p style={{ color: "var(--文字薄)", fontSize: 12, marginTop: 3 }}>
              フェーズ① — 社内AIチャットボット
            </p>
          </div>
          <div
            translate="no"
            style={{
            background: システム稼働中 ? "#dcfce7" : "#fee2e2",
            border: `1px solid ${システム稼働中 ? "#22c55e" : "#ef4444"}`,
            borderRadius: 20, padding: "4px 12px",
            color: システム稼働中 ? "#15803d" : "#b91c1c", fontSize: 11, fontWeight: 700,
            display: "flex", alignItems: "center", gap: 5,
          }}>
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: システム稼働中 ? "#22c55e" : "#ef4444",
              }}
            />
            {システム稼働中 ? "システム実行中" : "システム停止"}
          </div>
        </div>
      </div>

      {/* 統計カード */}
      <div style={{
        display: "grid",
        gridTemplateColumns: モバイル ? "1fr 1fr" : (チャット中 ? "1fr 1fr" : "repeat(4, 1fr)"),
        gap: 12, marginBottom: 20,
        transition: "grid-template-columns 0.3s ease",
      }}>
        {統計データ.map((統計, i) => (
          <div key={i} style={{
            background: "#fff", borderRadius: 12,
            border: "1px solid var(--境界線)",
            padding: "16px 18px",
            boxShadow: "0 1px 3px rgba(15,31,61,0.04)",
          }}>
            <div style={{ marginBottom: 10 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 9,
                background: 統計.色 + "18",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <統計.アイコン size={17} style={{ color: 統計.色 }} />
              </div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--紺)" }}>{統計.値}</div>
            <div style={{ fontSize: 11, color: "var(--文字薄)", marginTop: 2 }}>{統計.ラベル}</div>
            <div style={{ fontSize: 11, color: 統計.色, marginTop: 4, fontWeight: 500 }}>{統計.補足}</div>
          </div>
        ))}
      </div>

      {/* AIチャットボット案内 */}
      {!チャット中 && (
        <div style={{
          background: "linear-gradient(135deg, var(--紺) 0%, var(--青) 100%)",
          borderRadius: 16, padding: モバイル ? "18px 14px" : "26px 30px", marginBottom: 20,
          position: "relative", overflow: "hidden",
          boxShadow: "0 8px 32px rgba(15,31,61,0.2)",
        }}>
          {/* 背景装飾 */}
          <div style={{
            position: "absolute", right: -20, top: -20,
            width: 160, height: 160, borderRadius: "50%",
            background: "rgba(255,255,255,0.04)",
          }} />
          <div style={{
            position: "absolute", right: 40, bottom: -40,
            width: 100, height: 100, borderRadius: "50%",
            background: "rgba(0,201,167,0.06)",
          }} />

          <div style={{ position: "relative" }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              background: "rgba(0,201,167,0.2)", borderRadius: 20,
              padding: "3px 10px", marginBottom: 10,
              color: "var(--緑)", fontSize: 11, fontWeight: 600,
            }}>
              <Zap size={10} /> AIアシスタント
            </div>
            <h2 style={{ color: "#fff", fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
              商品検索 AIチャットボット
            </h2>
            <p style={{
              color: "rgba(255,255,255,0.55)", fontSize: 12, marginBottom: 18,
              lineHeight: 1.7, maxWidth: 460,
            }}>
              商品の条件を入力するだけで、AIが商品データベースから
              最適な商品を提案します。
            </p>
            <button
              onClick={チャットを開く}
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "var(--緑)", color: "var(--紺)",
                border: "none", borderRadius: 10, padding: "10px 20px",
                fontSize: 13, fontWeight: 700, cursor: "pointer",
                boxShadow: "0 4px 12px rgba(0,201,167,0.35)",
                fontFamily: "'Noto Sans JP', sans-serif",
                transition: "transform 0.15s ease",
              }}
              onMouseEnter={e => (e.currentTarget.style.transform = "translateY(-1px)")}
              onMouseLeave={e => (e.currentTarget.style.transform = "translateY(0)")}
            >
              <MessageSquare size={15} />
              チャットを開く
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}

      {/* 最近の検索履歴 */}
      <div style={{
        background: "#fff", borderRadius: 12,
        border: "1px solid var(--境界線)",
        overflow: "hidden",
        boxShadow: "0 1px 3px rgba(15,31,61,0.04)",
      }}>
        <div style={{
          padding: "13px 18px",
          borderBottom: "1px solid var(--境界線)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span style={{ fontWeight: 600, fontSize: 13, color: "var(--紺)" }}>最近の検索履歴</span>
          <span style={{ fontSize: 11, color: "var(--文字薄)" }}>本日</span>
        </div>
        {最近の検索履歴.map((履歴, i) => (
          <div key={i} style={{
            padding: "11px 18px",
            borderBottom: i < 最近の検索履歴.length - 1 ? "1px solid var(--表面2)" : "none",
            display: "flex", alignItems: "center", gap: 10,
          }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, flexShrink: 0,
              background: "var(--表面2)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <MessageSquare size={13} style={{ color: "var(--青明)" }} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 12, color: "var(--文字主)", fontWeight: 500,
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}>
                {履歴.検索内容}
              </div>
              <div style={{ fontSize: 11, color: "var(--文字薄)", marginTop: 2 }}>{履歴.時間}</div>
            </div>
            <div style={{
              background: "var(--表面2)", borderRadius: 6,
              padding: "2px 8px", fontSize: 11, color: "var(--青明)", fontWeight: 600,
              flexShrink: 0,
            }}>
              {履歴.件数}件提案
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
