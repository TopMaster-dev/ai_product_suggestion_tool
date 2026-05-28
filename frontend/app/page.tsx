"use client";
import { useEffect, useState } from "react";
import サイドバー from "@/components/サイドバー";
import メイン画面 from "@/components/メイン画面";
import チャットパネル from "@/components/チャットパネル";

export default function トップページ() {
  const [チャット開状態, setチャット開状態] = useState(false);
  const [モバイル, setモバイル] = useState(false);

  useEffect(() => {
    const 判定更新 = () => setモバイル(window.innerWidth <= 900);
    判定更新();
    window.addEventListener("resize", 判定更新);
    return () => window.removeEventListener("resize", 判定更新);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: モバイル ? "column" : "row", height: "100vh", overflow: "hidden" }}>

      {/* サイドバー（モバイル時はコンパクトヘッダー） */}
      <サイドバー モバイル={モバイル} />

      {/* メインエリア */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative" }}>

        {/* ダッシュボード */}
        <div style={{
          flex: モバイル ? "1" : (チャット開状態 ? "0 0 50%" : "1"),
          transition: "flex 0.35s cubic-bezier(0.16,1,0.3,1)",
          overflow: "auto",
          minWidth: 0,
          display: モバイル && チャット開状態 ? "none" : "block",
        }}>
          <メイン画面
            チャットを開く={() => setチャット開状態(true)}
            チャット中={チャット開状態}
            モバイル={モバイル}
          />
        </div>

        {/* チャットパネル（PC:右半分 / モバイル:全画面） */}
        {チャット開状態 && (
          <div
            className="パネル表示"
            style={{
              flex: モバイル ? "1" : "0 0 50%",
              borderLeft: モバイル ? "none" : "1px solid var(--境界線)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              position: モバイル ? "absolute" : "relative",
              inset: モバイル ? 0 : undefined,
              zIndex: モバイル ? 30 : 1,
              background: "#fff",
            }}
          >
            <チャットパネル 閉じる={() => setチャット開状態(false)} />
          </div>
        )}
      </div>
    </div>
  );
}
