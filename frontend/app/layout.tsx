import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Comparador de Calculos Previdenciarios",
  description: "Mini SaaS interno para comparacao deterministica de calculos previdenciarios"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
