import type { Metadata, Viewport } from "next";
import { Geist_Mono, Instrument_Sans } from "next/font/google";

import "./globals.css";

const instrumentSans = Instrument_Sans({
  variable: "--font-instrument-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Ritmo",
  description:
    "Sua corrida em um só lugar — sync do Garmin, painéis que importam e avaliação de treino com IA.",
};

export const viewport: Viewport = {
  themeColor: "#0B0F12",
  width: "device-width",
  initialScale: 1,
};

// Root layout: só o shell do documento (html/body, fontes, tema).
// O Header dos painéis migrou para o route group (app) e as telas de
// auth usam o layout mínimo do grupo (auth) — feature auth, AUTH-22.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="pt-BR"
      className={`${instrumentSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
