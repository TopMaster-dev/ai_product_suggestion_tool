import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kuras - 商品提案AIシステム",
  description: "フェーズ① 社内チャットボット",
};

export default function ルートレイアウト({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
