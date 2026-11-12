# Usability record: first sessions

This is a transcription of `docs/context/Testing.md`, as written. Nothing is corrected, tidied or interpreted. Where a fact was not written down it says **not recorded**; nothing has been filled in from memory or inference.

**What this is.** Three participant sessions (P1, P2, P3) and one check by the author. The cases give identity-card details (a made-up name, number and PIN). Case 4 is **not** a participant session (see below).

**Fields that were not recorded for any case:** step times, hesitations, hints given, the commit under test, and whether the session was live or recorded. They appear as "not recorded" in each case. `Testing.md` does not say whether the time written beside each case is minutes; the unit is **not recorded**.

| Code | Case in `Testing.md` | Role | Kind of session |
|---|---|---|---|
| P1 | Case 1 | worker | participant |
| P2 | Case 2 | client | participant |
| P3 | Case 3 | worker | participant |
| Author check | Case 4 | worker | **the author's own test, with details that differ from the cards; not a participant session** |

> **Note on the times.** Case 1 (P1) and Case 3 (P3) **both record "6:44"**. They are copied here exactly as written (P1's is written "6: 44", with a space). Neither has been changed. Whether the two sessions really took the same time, or one was copied from the other, is not known.

---

## P1 (Case 1): worker, electrician

| Field | As recorded |
|---|---|
| Task | Create an electrician's profile |
| Credentials on the card | First name: Juma · Last name: Testa · Phone: +254 700 000 101 · Pin: 4821 |
| Device | laptop |
| Browser | Safari |
| Time | 6: 44 (verbatim; see the note on times above) |
| Step times | not recorded |
| Hesitations | not recorded |
| Hints given | not recorded |
| Commit under test | not recorded |
| Live or recorded | not recorded |

**Profile built (verbatim):**

```
Your name
Juma Testa
Shown to clients
Yes: clients who post a job in your trade can see your name and your number, +254 700 000 101.
What you do
I am an electrician.
About you
I have been an electrician for 3 years. I do all kinds of electric work; from light switches to sockets to fixing gadgets. All of it. I've been contracted by Fine Urban Interiors to do electrical work for 4 houses.
Where you work
Nairobi - Embakasi
When you can work
Full-time
Your daily rate
KES 3,000 / day
```

**Tips.** These are tips *I got from the testers about their experience*, not instructions the participant was given:

> Tips: a worker might want to click the title of the job for more information.

**Comment (verbatim):**

> they identified and liked that the profile edits allow for better matching

**Questions (verbatim):**

- i. Which job would you pick and why?
  - Picked the one with the highest match score because it relates mostly to what i can do.
- ii. Was there anything you didn't understand?
  - No.

**Note written at the end of the case (verbatim):**

> ** add back navigation to the landing page

---

## P2 (Case 2): client, job posting

| Field | As recorded |
|---|---|
| Task | Create a job posting |
| Credentials on the card | Phone: +254 700 000 201 · Pin: 4821 |
| Device | laptop |
| Browser | Safari |
| Time | 4:10 |
| Step times | not recorded |
| Hesitations | not recorded |
| Hints given | not recorded |
| Commit under test | not recorded |
| Live or recorded | not recorded |

**Job built (verbatim):**

```
Your job has been posted.

How we understood your posting

CLIENT VERBATIM INPUT
“looking for a mechanic for a car”
↓
We couldn't match this to a trade we know. Your posting is live and will still be matched on its wording.

We read the words of your posting. We match on the skills you listed above, and nothing else. We didn't recognise “wheel balancing”, “engine check”, “tire changing”, “fixing brake lights”, so we kept it exactly as you wrote it.
```

**Tips:** (blank in the record)

**Comment:** (blank in the record)

**Questions (verbatim):**

- i. Was there anything you didn't understand?
  - No

---

## P3 (Case 3): worker, electrician

| Field | As recorded |
|---|---|
| Task | Create an electrician's profile |
| Credentials on the card | First name: Wanjiru · Last name: Testa · Phone: +254 700 000 102 · Pin: 4821 |
| Device | laptop |
| Browser | Dia (a Chromium-based browser) |
| Time | 6:44 (verbatim; see the note on times above) |
| Step times | not recorded |
| Hesitations | not recorded |
| Hints given | not recorded |
| Commit under test | not recorded |
| Live or recorded | not recorded |

**Profile built (verbatim):**

```
Your name
Wanjiru Testa
Shown to clients
Yes: clients who post a job in your trade can see your name and your number, +254 700 000 102.
What you do
Solar panels installation
lighting systems installation
wiring
diagnostics
compliance inspection
electrical repair
electrical maintenance
About you
I am a seasoned electrician with 15+ years of experience in this field. I have a bachelors degree in electrical engineering from jomo kenyatta university of agriculture and technology. My work includes the installation, maintenance and repair of anything to do with electrical systems in homes,offices and industrial complexes. I also help with inspection and ensure strict compliance with laws and regulations set out by county governments and the national government. I am based in Nairobi however I can travel country wide and in special cases within the east african community
Where you work
Nairobi - Westlands
When you can work
Full-time
Your daily rate
KES 3,000 / day
```

**Tips:** (none written)

**Comment (verbatim):**

> what i would improve is the scoring system, some UI functionalities like when i try to see more key words that matched it wouldnt work.

**Questions (verbatim):**

- i. Which job would you pick and why?
  - I would pick job 4 and 7 because these are the two highest paying jobs and considering the experience and knowledge i have they would also be quite simple to do.
- ii. Was there anything you didn't understand?
  - The scoring system for the job matches. My understanding is that it was using the key words I was putting in to pull jobs that match the description, however if i am looking for a job my first priority would be what i am going to be paid by the hour. In my case my most strongest fit (job 1) was a job that pays me a lot less than what my daily rate was

---

## Author check (Case 4): **not a participant session**

This is the author's own test of the app. **Its details differ from the identity cards**: the name, the phone number and the PIN are not the card values, and the name typed in the profile differs from the name on the sheet ("Testa" above, "Tester" in the profile). It must not be counted as a participant, and nothing in it is evidence about what a first-time user does.

| Field | As recorded |
|---|---|
| Task | Create an electrician's profile |
| Credentials as written | First name: Kristina · Last name: Testa · Phone: +254 700 012 300 · Pin: 4545 |
| Device | phone |
| Browser | Safari |
| Time | 5:10 |
| Step times | not recorded |
| Hesitations | not recorded |
| Hints given | not recorded |
| Commit under test | not recorded |
| Live or recorded | not recorded |

**Profile built (verbatim):**

```
Your name
Kristina Tester
Shown to clients
Yes: clients who post a job in your trade can see your name and your number, +254 700 012 300.
What you do
Mimi ni fundi wa umeme. I can do electrical wiring and handles household electrical fixes
About you
I have 10 years in experience.
Where you work
Nairobi - Kasarani
When you can work
Full-time
Your daily rate
KES 2,000 / day
```

**Tips, comments, questions:** none written.

---

## Findings

Six findings came out of the sessions. "Seen by" gives only what `Testing.md` supports. Where the record does not say who met a thing, it says **not recorded**.

| # | Finding | Seen by | Kind | Status |
|---|---|---|---|---|
| U-1 | No way back from the sign-in and create-account pages to the landing page | P1 (the note "add back navigation to the landing page" is written at the end of Case 1; whose note it is, the participant's or the author's, is not recorded) | navigation gap in the interface | **Fixed**: a "Back to the home page" link on both pages |
| U-2 | A button reading "Signing in…" / "Creating your account…" / "Saving…" with nothing submitted, fields disabled (sign-in, create account, edit profile) | not recorded in `Testing.md` | defect in the interface | **Fixed**: cause found and reproduced; see `docs/test-record.md` |
| U-3 | The message "Cannot reach API at /api. Is it running?" for one tester | not recorded in `Testing.md` | connectivity; cause not established | **Open**: the logs show tunnel reconnections during the sessions, which cannot be tied to a participant; whether the message should offer a retry is for the author to decide |
| U-4 | "See more keywords that matched" did not work | P3 (Dia, laptop) | unclear affordance, not a broken control: the only such text is "+N more" on a match card, which is plain text and does nothing in any browser | **Open**: left for the author to decide (make it a link to "Why this job?", or expand in place) |
| U-5 | The match score does not follow pay: P3's strongest match (job 1) paid much less than the daily rate; P3 would pick the two highest-paying jobs | P3 | a question about what the score means, not an interface defect | **Open, not changed**: the score is the matching and scoring path, which this phase does not touch |
| U-6 | "looking for a mechanic for a car" is not matched to a trade ("We couldn't match this to a trade we know") | P2 | vocabulary coverage in the knowledge graph | **Open, not changed**: enrichment is not touched in this phase; P2 recorded no difficulty ("Was there anything you didn't understand? No") |
