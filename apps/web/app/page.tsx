"use client";

/**
 * The landing page: what the system does, shown with one example, and the two ways in.
 *
 * It says only what the system does and nothing about how well. No figures, no
 * quotations, no images: the one picture is the path from what a worker writes, to the
 * trade the system reads it as, to the jobs that need those skills. The warmth here
 * (canvas, accent, heading face, spacing) is scoped to this page in landing.module.css;
 * the application screens keep the palette they were photographed in.
 *
 * The startup notice is the same one the application shows. The engine status comes from
 * the provider in the root layout, so the page needs no more than the notice itself: a
 * visitor who clicks through while the model is still loading has been told why it is slow.
 */

import { Nunito_Sans } from "next/font/google";
import Link from "next/link";
import { StartupNotice } from "@/components/AppShell";
import { useRedirectIfSignedIn } from "@/components/SessionProvider";
import styles from "./landing.module.css";

const headingFont = Nunito_Sans({ subsets: ["latin"], variable: "--font-heading", display: "swap" });

const STEPS = [
  { label: "A worker writes", body: <q className={styles.written}>fundi wa umeme</q> },
  { label: "The system understands", body: <span className={styles.trade}>Electrician</span> },
  { label: "And finds", body: <span className={styles.jobs}>Jobs that need those skills</span> },
];

const HOW_IT_WORKS = [
  "Describe your work in your own words",
  "We work out your trade",
  "See matching jobs with the reasons for each",
];

export default function Page() {
  useRedirectIfSignedIn();

  return (
    <div className={`${styles.landing} ${headingFont.variable}`}>
      <header className={styles.top}>
        <div className={styles.topInner}>
          <span className={styles.brand}>KaziForce</span>
          <Link className={styles.signIn} href="/sign-in">
            Sign in
          </Link>
        </div>
      </header>

      <StartupNotice />

      <main className={styles.main}>
        <section className={styles.hero}>
          <h1 className={styles.heading}>Find work that fits, in your own words</h1>
          <p className={styles.lead}>
            KaziForce understands how tradespeople describe their work and matches them with the jobs that need those
            skills.
          </p>

          <ol className={styles.path} aria-label="An example">
            {STEPS.map((step, index) => (
              <li key={step.label} className={styles.step}>
                <span className={styles.stepLabel}>{step.label}</span>
                <span className={styles.stepBody}>{step.body}</span>
                {index < STEPS.length - 1 && (
                  <span className={styles.arrow} aria-hidden="true">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>

          <div className={styles.entries}>
            <Link className={`button ${styles.entry}`} href="/create-account?role=worker">
              I&apos;m looking for work
            </Link>
            <Link className={`button ${styles.entry} ${styles.entrySecond}`} href="/create-account?role=client">
              I need a fundi
            </Link>
          </div>
        </section>

        <section className={styles.how} aria-labelledby="how-it-works">
          <h2 id="how-it-works" className={styles.howHeading}>
            How it works
          </h2>
          <ol className={styles.howRow}>
            {HOW_IT_WORKS.map((text, index) => (
              <li key={text} className={styles.howItem}>
                <span className={styles.howNumber} aria-hidden="true">
                  {index + 1}
                </span>
                {text}
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer className={styles.footer}>
        KaziForce is a final-year project at Strathmore University. It is not a live service.
      </footer>
    </div>
  );
}
