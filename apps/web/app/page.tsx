"use client";

/**
 * The landing page: what the system does, which trades it understands, how it works, and the ways in.
 *
 * It says only what the system does, and nothing about how well. No counts, no rates, no ratings, no
 * "verified" or "trusted", no search, and no worker named or shown: a worker's name and number are for a
 * client who has posted a job, and only with the worker's consent. The trade list is the vocabulary the
 * system really has (data/vocabulary/aliases.csv, the accepted terms in the knowledge graph), as plain
 * text and not a menu.
 *
 * The page is built to docs/testing results/landing page (screen.png). Everything it links to is an
 * existing route: /create-account?role=…, /sign-in, and anchors on this page. The startup notice is the
 * app's own, so a visitor who clicks through while the model is loading has been told why it is slow.
 */

import Link from "next/link";
import { StartupNotice } from "@/components/AppShell";
import { useRedirectIfSignedIn } from "@/components/SessionProvider";
import styles from "./landing.module.css";

/** The accepted, knowledge-graph terms for each trade the system understands today. */
const TRADES = [
  { term: "fundi wa umeme", trade: "electrician" },
  { term: "fundi bomba", trade: "plumber" },
  { term: "fundi wa mbao", trade: "carpenter" },
  { term: "mwashi", trade: "bricklayer" },
  { term: "fundi wa magari", trade: "vehicle technician" },
  { term: "fundi wa simu", trade: "mobile phone repair technician" },
  { term: "fundi wa nguo", trade: "tailor" },
  { term: "kinyozi", trade: "barber" },
  { term: "msusi", trade: "hairdresser" },
  { term: "mama fua", trade: "laundry worker" },
  { term: "mpishi", trade: "cook" },
];

const WORKER_URL = "/create-account?role=worker";
const CLIENT_URL = "/create-account?role=client";

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

const Arrow = () => (
  <Icon>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
);

const Check = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12.5l2.5 2.5L16 9.5" />
  </svg>
);

export default function Page() {
  useRedirectIfSignedIn();

  return (
    <div className={styles.landing}>
      <header className={styles.top}>
        <div className={`${styles.shell} ${styles.topInner}`}>
          <span className={styles.brand}>KaziForce</span>
          <nav className={styles.topNav} aria-label="Account">
            <Link className={styles.topLink} href="/sign-in">
              Sign in
            </Link>
            <a className={`button ${styles.topButton}`} href="#start">
              Get started
            </a>
          </nav>
        </div>
      </header>

      <StartupNotice />

      <main>
        <section className={styles.hero} aria-labelledby="headline">
          <div className={styles.shell}>
            <h1 id="headline" className={styles.heading}>
              Work that fits your hands.
              <span className={styles.headingBlue}> Said in your own words.</span>
            </h1>
            <p className={styles.lead}>
              KaziForce understands how tradespeople describe their work and matches them with the jobs that need those
              skills. Type in English or Kiswahili.
            </p>

            <div id="start" className={styles.entries}>
              <div className={styles.entry}>
                <p className={`${styles.eyebrow} ${styles.eyebrowOrange}`}>Kwa mafundi</p>
                <h2 className={styles.entryHeading}>Looking for work?</h2>
                <p className={styles.entryBody}>
                  Describe your work in your own words and see the jobs that need those skills, with the reasons for
                  each.
                </p>
                <Link className={`button ${styles.entryButton}`} href={WORKER_URL}>
                  I&apos;m looking for work <Arrow />
                </Link>
              </div>

              <div className={styles.entry}>
                <p className={`${styles.eyebrow} ${styles.eyebrowBlue}`}>Kwa wateja</p>
                <h2 className={styles.entryHeading}>Need a fundi?</h2>
                <p className={styles.entryBody}>
                  Describe the job in everyday terms and see how we read it, and the workers in that trade. You can call
                  the ones who have agreed to be contacted.
                </p>
                <Link className={`button ${styles.entryButton} ${styles.entryButtonBlue}`} href={CLIENT_URL}>
                  I need a fundi <Arrow />
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className={styles.trades} aria-labelledby="trades-heading">
          <div className={styles.shell}>
            <p className={styles.eyebrow}>What we understand</p>
            <h2 id="trades-heading" className={styles.sectionHeading}>
              Trades we understand today
            </h2>
            <p className={styles.sectionLead}>
              Write the trade your own way. These are the terms we know; a word we don&apos;t know is kept exactly as you
              wrote it.
            </p>
            <ul className={styles.chips} aria-label="Trades and the terms we know for them">
              {TRADES.map(({ term, trade }) => (
                <li key={term} className={styles.chip}>
                  <span className={styles.chipTerm}>{term}</span>
                  <span className={styles.chipTrade}>{trade}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="how-it-works" className={styles.how} aria-labelledby="how-heading">
          <div className={styles.shell}>
            <p className={`${styles.eyebrow} ${styles.eyebrowOrange} ${styles.centred}`}>Straightforward and clear</p>
            <h2 id="how-heading" className={`${styles.sectionHeading} ${styles.centred}`}>
              How KaziForce works in 3 steps
            </h2>
            <ol className={styles.steps}>
              <li className={styles.step}>
                <span className={styles.stepNumber} aria-hidden="true">
                  1
                </span>
                <h3 className={styles.stepHeading}>Say what you do</h3>
                <p className={styles.stepBody}>
                  Write in plain words, for example <em>fundi wa umeme</em> or <em>fundi bomba</em>. No forms and no trade
                  codes.
                </p>
                <p className={styles.example}>
                  <span className={styles.exampleLabel}>Example</span>
                  &ldquo;Niko na experience ya kuweka tiles na piping miaka 6.&rdquo;
                </p>
              </li>
              <li className={styles.step}>
                <span className={styles.stepNumber} aria-hidden="true">
                  2
                </span>
                <h3 className={styles.stepHeading}>We work out your trade</h3>
                <p className={styles.stepBody}>
                  We read your words, find the trade they describe, and look for jobs that need those skills.
                </p>
                <p className={styles.example}>
                  <span className={styles.exampleLabel}>Example</span>
                  <span className="mono">fundi wa umeme</span> → electrician
                </p>
              </li>
              <li className={styles.step}>
                <span className={styles.stepNumber} aria-hidden="true">
                  3
                </span>
                <h3 className={styles.stepHeading}>See jobs, and why</h3>
                <p className={styles.stepBody}>
                  Each job comes with the reasons it was matched, in plain words. A client sees how their posting was
                  read.
                </p>
              </li>
            </ol>
          </div>
        </section>

        <section className={styles.audiences} aria-label="For tradespeople and for clients">
          <div className={`${styles.shell} ${styles.audienceGrid}`}>
            <div className={styles.audience}>
              <span className={`${styles.pill} ${styles.pillOrange}`}>For tradespeople</span>
              <h2 className={styles.audienceHeading}>Describe your work your way.</h2>
              <p className={styles.audienceLead}>
                You know your trade. Write it the way you say it, and we do the matching.
              </p>
              <ul className={styles.points}>
                <li>
                  <span className={styles.checkOrange}>
                    <Check />
                  </span>
                  <span>
                    <strong>Your own words:</strong> English or Kiswahili, as you would say it.
                  </span>
                </li>
                <li>
                  <span className={styles.checkOrange}>
                    <Check />
                  </span>
                  <span>
                    <strong>Reasons shown:</strong> every job says why it was matched to you.
                  </span>
                </li>
                <li>
                  <span className={styles.checkOrange}>
                    <Check />
                  </span>
                  <span>
                    <strong>You choose who sees you:</strong> your name and number are shown to clients only if you agree,
                    and you can take that back.
                  </span>
                </li>
              </ul>
              <Link className={`button ${styles.panelButton}`} href={WORKER_URL}>
                Create a worker account
              </Link>
            </div>

            <div className={styles.audience}>
              <span className={`${styles.pill} ${styles.pillBlue}`}>For clients</span>
              <h2 className={styles.audienceHeading}>Post the job in everyday words.</h2>
              <p className={styles.audienceLead}>
                Say what needs doing the way you would to a neighbour. We work out which trade it needs.
              </p>
              <ul className={styles.points}>
                <li>
                  <span className={styles.checkBlue}>
                    <Check />
                  </span>
                  <span>
                    <strong>Everyday terms:</strong> no need to know the trade&apos;s name.
                  </span>
                </li>
                <li>
                  <span className={styles.checkBlue}>
                    <Check />
                  </span>
                  <span>
                    <strong>See how it was read:</strong> the trade and the skills we understood.
                  </span>
                </li>
                <li>
                  <span className={styles.checkBlue}>
                    <Check />
                  </span>
                  <span>
                    <strong>Call workers who agree:</strong> those who have chosen to be contacted show their name and
                    number. The workers listed are a sample of the trade, not a ranking.
                  </span>
                </li>
              </ul>
              <Link className={`button ${styles.panelButton} ${styles.entryButtonBlue}`} href={CLIENT_URL}>
                Create a client account
              </Link>
            </div>
          </div>
        </section>

        <section className={styles.band} aria-labelledby="band-heading">
          <div className={styles.shell}>
            <div className={styles.bandInner}>
              <div>
                <p className={styles.bandEyebrow}>Welcome back</p>
                <h2 id="band-heading" className={styles.bandHeading}>
                  Already have an account?
                </h2>
                <p className={styles.bandBody}>Sign in with your phone number and your 4-digit PIN.</p>
              </div>
              <div className={styles.bandActions}>
                <Link className={`button ${styles.bandPrimary}`} href="/sign-in">
                  Sign in to your account
                </Link>
                <a className={`button ${styles.bandSecondary}`} href="#how-it-works">
                  How it works
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.shell}>KaziForce © 2026</div>
      </footer>
    </div>
  );
}
