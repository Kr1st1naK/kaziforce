import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { EngineStatusProvider } from "@/components/EngineStatus";
import { SessionProvider } from "@/components/SessionProvider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "KaziForce",
  description: "Job matching for Kenyan trades.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body>
        <SessionProvider>
          <EngineStatusProvider>{children}</EngineStatusProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
