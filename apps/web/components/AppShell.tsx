"use client";

/**
 * The frame every signed-in screen sits in: the header with role-aware
 * navigation, the startup notice, and the footer.
 *
 * The notice appears whenever the API is still loading its model and answering
 * 503, with the wording from the design.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEngineStatus } from "./EngineStatus";
import { useSession } from "./SessionProvider";
import styles from "./AppShell.module.css";

const NAV = {
  worker: [
    { href: "/worker/matches", label: "My matches" },
    { href: "/worker/profile", label: "My profile" },
  ],
  // A client has an account and postings, not a profile.
  client: [
    { href: "/client/post", label: "Post a job" },
    { href: "/client/postings", label: "My postings" },
  ],
} as const;

export function StartupNotice() {
  const { ready, unreachable, recheck } = useEngineStatus();
  if (ready) return null;
  return (
    <div className={styles.notice} role="status" aria-live="polite">
      <span className={styles.noticeIcon} aria-hidden="true">
        &#9432;
      </span>
      {unreachable ? (
        <span>
          Cannot reach the matching service.{" "}
          <button type="button" className="link" onClick={recheck}>
            Check again
          </button>
        </span>
      ) : (
        <span>Preparing the matching service. This takes about half a minute.</span>
      )}
    </div>
  );
}

function AccountMenu() {
  const { session, signOut } = useSession();
  if (!session) return null;
  return (
    <button
      type="button"
      className={styles.avatar}
      onClick={() => void signOut()}
      title={`Signed in as ${session.account.phone}. Sign out.`}
      aria-label={`Signed in as ${session.account.phone}. Sign out.`}
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-5 0-9 2.5-9 5.5V22h18v-2.5c0-3-4-5.5-9-5.5Z" />
      </svg>
    </button>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { session } = useSession();
  const pathname = usePathname();
  const items = session ? NAV[session.account.role] : [];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={`shell ${styles.headerInner}`}>
          <span className={styles.brand}>KaziForce</span>
          <nav className={styles.nav}>
            {items.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? styles.navActive : styles.navLink}
                  aria-current={active ? "page" : undefined}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <AccountMenu />
        </div>
      </header>

      <StartupNotice />

      <main className={styles.main}>
        <div className="shell">{children}</div>
      </main>

      <footer className={styles.footer}>
        <div className="shell">KaziForce © 2026</div>
      </footer>
    </div>
  );
}
