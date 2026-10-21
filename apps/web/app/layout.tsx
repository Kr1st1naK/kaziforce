import type { Metadata } from "next";
import Link from "next/link";
import { EngineBanner, EngineStatusProvider } from "@/components/EngineStatus";
import "./globals.css";
import styles from "./layout.module.css";

export const metadata: Metadata = {
  title: "KaziForce",
  description: "Explainable knowledge graph-enhanced matching for informal gig work in Kenya",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <EngineStatusProvider>
          <header className={styles.header}>
            <Link className={styles.brand} href="/">
              KaziForce
            </Link>
            <nav className={styles.nav}>
              <Link href="/worker">Find work</Link>
              <Link href="/jobs/new">Post a job</Link>
            </nav>
          </header>
          <main>
            <EngineBanner />
            {children}
          </main>
        </EngineStatusProvider>
      </body>
    </html>
  );
}
