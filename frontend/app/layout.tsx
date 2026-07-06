import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Planejamento Previdenciario",
  description: "Mini SaaS interno para planejamento previdenciario"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
