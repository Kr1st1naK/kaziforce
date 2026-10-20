import Link from "next/link";
import styles from "./page.module.css";

export default function Page() {
  return (
    <div>
      <h1>Find work, or find a worker</h1>
      <p className="note">
        KaziForce matches informal trade workers to jobs, and explains every match. It understands Kenyan trade
        terms: describe yourself as a <em>fundi wa umeme</em> and it knows to look for electrical work.
      </p>

      <div className={styles.choices}>
        <section className={styles.choice}>
          <h2 className={styles.choiceTitle}>I am looking for work</h2>
          <p className={styles.choiceBody}>
            Describe yourself in your own words, in English or Kiswahili. You will get a ranked list of jobs, each
            with the reason it was matched.
          </p>
          <Link className="button button-primary" href="/worker">
            Create your profile
          </Link>
        </section>

        <section className={styles.choice}>
          <h2 className={styles.choiceTitle}>I am posting a job</h2>
          <p className={styles.choiceBody}>
            Post the work you need done. You will see how the system understood your posting and how many registered
            workers match it.
          </p>
          <Link className="button" href="/jobs/new">
            Post a job
          </Link>
        </section>
      </div>

      <p className={styles.facts}>
        A capstone prototype. Profiles and postings in this demo are synthetic, and no personal details are asked for
        or stored.
      </p>
    </div>
  );
}
