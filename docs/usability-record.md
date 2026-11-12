# Usability record: first sessions

This is a transcription of `docs/context/Testing.md`, as written, plus facts the author has since confirmed (marked "stated by the author" or "as reported by the author"). Nothing is corrected, tidied or interpreted. Where a fact was not written down it says **not recorded**; nothing has been filled in from memory or inference.

**What this is.** Three participant sessions (P1, P2, P3) and one check by the author. The cases give identity-card details (a made-up name, number and PIN). Case 4 is **not** a participant session (see below).

**Format of all sessions (stated by the author):** **unmoderated.** Participants worked alone and screen-recorded themselves; none was live. **Moderator hints: none possible (unmoderated); to confirm from recordings.**

**Time (stated by the author):** a time written as "6:44" means **6 minutes 44 seconds**. Every time below is minutes:seconds.

**Fields that were not recorded for any case:** step times, hesitations and the commit under test. They appear as "not recorded" in each case. What participants were told about being recorded is **not recorded**. The recordings are to be deleted after analysis; **deletion date: not yet** (not deleted).

| Code | Case in `Testing.md` | Role | Kind of session |
|---|---|---|---|
| P1 | Case 1 | worker | participant |
| P2 | Case 2 | client | participant |
| P3 | Case 3 | worker | participant |
| Author check | Case 4 | worker | **the author's own test, with details that differ from the cards; not a participant session** |

> **Note on the times.** Case 1 (P1) and Case 3 (P3) **both record "6:44"**. They are copied here exactly as written (P1's is written "6: 44", with a space). Neither has been changed. Both are 6 minutes 44 seconds as written. **Confirmed as written by the author; check against the recordings.**

---

## P1 (Case 1): worker, electrician

| Field | As recorded |
|---|---|
| Task | Create an electrician's profile |
| Credentials on the card | First name: Juma · Last name: Testa · Phone: +254 700 000 101 · Pin: 4821 |
| Device | laptop |
| Browser | Safari |
| Time | 6: 44 as written (6 minutes 44 seconds; see the note on times above) |
| Step times | not recorded |
| Hesitations | not recorded |
| Moderator hints | none possible (unmoderated); to confirm from recordings |
| Commit under test | not recorded |
| Format | unmoderated; worked alone; screen-recorded by the participant; not live |

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

**Tips.** These are the participant's own remarks about their experience (tips the author got from the tester). They are **not moderator hints**; the session was unmoderated.

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
| Time | 4:10 (4 minutes 10 seconds) |
| Step times | not recorded |
| Hesitations | not recorded |
| Moderator hints | none possible (unmoderated); to confirm from recordings |
| Commit under test | not recorded |
| Format | unmoderated; worked alone; screen-recorded by the participant; not live |

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
| Time | 6:44 as written (6 minutes 44 seconds; see the note on times above) |
| Step times | not recorded |
| Hesitations | not recorded |
| Moderator hints | none possible (unmoderated); to confirm from recordings |
| Commit under test | not recorded |
| Format | unmoderated; worked alone; screen-recorded by the participant; not live |

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
| Time | 5:10 (5 minutes 10 seconds) |
| Step times | not recorded |
| Hesitations | not recorded |
| Moderator hints | none possible (unmoderated); to confirm from recordings |
| Commit under test | not recorded |
| Format | the author's own check, done alone, so unmoderated; whether it was screen-recorded: not recorded |

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

Six findings came out of the sessions. "Seen by" gives what `Testing.md` supports and what the author has since stated. Where neither says who met a thing, it says **not recorded**.

| # | Finding | Seen by | Kind | Status |
|---|---|---|---|---|
| U-1 | No way back from the sign-in and create-account pages to the landing page | P1 (the note "add back navigation to the landing page" is written at the end of Case 1) and the author | navigation gap in the interface | **Fixed in `4e9f635`**: a "Back to the home page" link on both pages |
| U-2 | A button reading "Signing in…" / "Creating your account…" / "Saving…" with nothing submitted, fields disabled (sign-in, create account, edit profile) | the author, on a phone (Safari) | defect in the interface | **Fixed in `4e9f635`**: cause found and reproduced; see `docs/test-record.md` |
| U-3 | The message "Cannot reach API at /api. Is it running?" for one tester | reported to the author by a tester while creating a job posting; **likely P2; to confirm** | connectivity message and recovery. The original cause was the **tunnel dropping** (see `tunnel.log`), which is **outside the app** | **Fixed in `660a184`, for the wording and the recovery only**: the message now reads "We couldn't reach the service. Check your connection and try again.", and the forms that submit show a "Try again" button. The dropped connection itself is not something the app can prevent. Nothing is retried automatically |
| U-4 | "See more keywords that matched" did not work | P3 (Dia, laptop) | unclear affordance, not a broken control: the only such text was "+N more" on a match card, plain text that did nothing in any browser | **Fixed in `660a184`**: "+N more" is now a link to that match's "Why this job?" page, keyboard reachable, 44 px tall |
| U-5 | The match score does not follow pay: P3's strongest match (job 1) paid much less than the daily rate; P3 would pick the two highest-paying jobs | P3 | a question about what the score means, not an interface defect | **Open, not changed**: the score is the matching and scoring path, which this phase does not touch |
| U-6 | "looking for a mechanic for a car" is not matched to a trade ("We couldn't match this to a trade we know") | P2 | vocabulary coverage in the knowledge graph | **Open, not changed**: enrichment is not touched in this phase; P2 recorded no difficulty ("Was there anything you didn't understand? No") |

---

## Observations from the server log, as reported by the author

These are the author's statements. `api.log` records **when** a request was made, not **who** made it, so the log alone does not identify anyone.

| What the log shows | Time (EAT) | As reported by the author | Cause |
|---|---|---|---|
| Two sign-in attempts refused (HTTP 401) | 21:40 | made by P1 | **to check from the recording** |
| One account creation refused as a duplicate phone number (HTTP 409) | 22:28 | made by P1 | **to check from the recording** |

No cause is stated here for either.

---

## To fill from the recordings

Left empty on purpose. Nothing below has been filled in from memory or inference.

### P1
- Step times: 
- Hesitations: 
- Errors (including the two wrong-PIN sign-ins and the duplicate-phone attempt above): 

### P2
- Step times: 
- Hesitations: 
- Errors (including the "Cannot reach the API" message, if it was P2): 

### P3
- Step times: 
- Hesitations: 
- Errors: 

---

## Recordings

What participants were told about being recorded: **not recorded**. The recordings are to be **deleted after analysis**; deletion date: **not yet** (they have not been deleted).
