"use client";
import { useState } from "react";
import {
  LayoutDashboard, Package, Mail, MessageSquare,
  BarChart2, Settings, ChevronRight,
} from "lucide-react";

const ナビメニュー = [
  { アイコン: LayoutDashboard, ラベル: "ダッシュボード" },
  { アイコン: Package,         ラベル: "商品提案書作成" },
  { アイコン: Mail,            ラベル: "メルマガ作成" },
  { アイコン: MessageSquare,   ラベル: "商品検索 AI" },
  { アイコン: BarChart2,       ラベル: "分析レポート" },
];

export default function サイドバー({ モバイル = false }: { モバイル?: boolean }) {
  const [選択中, set選択中] = useState(0);

  if (モバイル) {
    return (
      <div style={{
        height: 56,
        flexShrink: 0,
        background: "linear-gradient(135deg, var(--紺), var(--青))",
        borderBottom: "1px solid rgba(255,255,255,0.12)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 14px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <img src="/kuras_hd_logo_png2.png" alt="Kuras Logo" style={{ height: "24px", width: "auto", objectFit: "contain" }} />
        </div>
        <div style={{ color: "rgba(255,255,255,0.75)", fontSize: 11 }}>フェーズ①</div>
      </div>
    );
  }

  return (
    <div style={{
      width: 220,
      flexShrink: 0,
      background: "linear-gradient(180deg, var(--紺) 0%, var(--紺中) 100%)",
      display: "flex",
      flexDirection: "column",
      borderRight: "1px solid rgba(255,255,255,0.06)",
      zIndex: 10,
    }}>

      {/* ロゴ */}
      <div style={{
        padding: "22px 20px 18px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <img src="/kuras_hd_logo_png2.png" alt="Kuras" style={{ height: "32px", width: "auto", objectFit: "contain" }} />
        </div>
      </div>

      {/* フェーズバッジ */}
      <div style={{ padding: "12px 16px" }}>
        <div style={{
          background: "rgba(0,201,167,0.15)",
          border: "1px solid rgba(0,201,167,0.3)",
          borderRadius: 6, padding: "5px 10px",
          color: "var(--緑)", fontSize: 11, fontWeight: 600,
          display: "flex", alignItems: "center", gap: 5,
        }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--緑)" }} />
          フェーズ① 稼働中
        </div>
      </div>

      {/* ナビゲーション */}
      <nav style={{ flex: 1, padding: "4px 10px", display: "flex", flexDirection: "column", gap: 2 }}>
        <div style={{
          color: "rgba(255,255,255,0.28)", fontSize: 10, fontWeight: 600,
          letterSpacing: "0.1em", padding: "8px 8px 4px", textTransform: "uppercase",
        }}>
          メニュー
        </div>

        {ナビメニュー.map((項目, i) => (
          <button
            key={i}
            onClick={() => set選択中(i)}
            className="ナビアイテム"
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "9px 10px", borderRadius: 8,
              background: 選択中 === i ? "rgba(0,201,167,0.12)" : "transparent",
              borderRight: 選択中 === i ? "3px solid var(--緑)" : "3px solid transparent",
              border: "none", cursor: "pointer", width: "100%", textAlign: "left",
              color: 選択中 === i ? "var(--緑)" : "rgba(255,255,255,0.5)",
              fontWeight: 選択中 === i ? 600 : 400,
              fontSize: 13,
              fontFamily: "'Noto Sans JP', sans-serif",
            }}
          >
            <項目.アイコン size={15} style={{ flexShrink: 0 }} />
            <span style={{ flex: 1 }}>{項目.ラベル}</span>
            {選択中 === i && <ChevronRight size={12} />}
          </button>
        ))}
      </nav>

      {/* ユーザー情報 */}
      <div style={{ padding: "14px 12px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <button style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "8px 10px", borderRadius: 8, width: "100%",
          background: "transparent", border: "none", cursor: "pointer",
          color: "rgba(255,255,255,0.35)", fontSize: 12,
          fontFamily: "'Noto Sans JP', sans-serif",
        }}>
          <Settings size={14} />
          <span>システム設定</span>
        </button>
        <div style={{
          marginTop: 10, padding: "10px",
          borderRadius: 8, background: "rgba(255,255,255,0.05)",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <div style={{
            width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
            background: "linear-gradient(135deg, var(--青明), var(--緑))",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontSize: 12, fontWeight: 700,
          }}>営</div>
          <div>
            <div style={{ color: "rgba(255,255,255,0.75)", fontSize: 12, fontWeight: 500 }}>営業担当</div>
            <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 10 }}>社内システム</div>
          </div>
        </div>
      </div>
    </div>
  );
}
