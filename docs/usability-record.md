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

Sixteen findings have come out of the sessions (U-7 to U-9 added after the first six, U-10 to U-16 from Round 2). "Seen by" gives what `Testing.md` supports and what the author has since stated. Where neither says who met a thing, it says **not recorded**.

| # | Finding | Seen by | Kind | Status |
|---|---|---|---|---|
| U-1 | No way back from the sign-in and create-account pages to the landing page | P1 (the note "add back navigation to the landing page" is written at the end of Case 1) and the author | navigation gap in the interface | **Fixed in `4e9f635`**: a "Back to the home page" link on both pages |
| U-2 | A button reading "Signing in…" / "Creating your account…" / "Saving…" with nothing submitted, fields disabled (sign-in, create account, edit profile) | the author, on a phone (Safari) | defect in the interface | **Fixed in `4e9f635`**: cause found and reproduced; see `docs/test-record.md` |
| U-3 | The message "Cannot reach API at /api. Is it running?" for one tester | reported to the author by a tester while creating a job posting; **likely P2; to confirm** | connectivity message and recovery. The original cause was the **tunnel dropping** (see `tunnel.log`), which is **outside the app** | **Fixed in `660a184`, for the wording and the recovery only**: the message now reads "We couldn't reach the service. Check your connection and try again.", and the forms that submit show a "Try again" button. The dropped connection itself is not something the app can prevent. Nothing is retried automatically |
| U-4 | "See more keywords that matched" did not work | P3 (Dia, laptop) | unclear affordance, not a broken control: the only such text was "+N more" on a match card, plain text that did nothing in any browser | **Fixed in `660a184`**: "+N more" is now a link to that match's "Why this job?" page, keyboard reachable, 44 px tall |
| U-5 | The match score does not follow pay: P3's strongest match (job 1) paid much less than the daily rate; P3 would pick the two highest-paying jobs | P3 | a question about what the score means, not an interface defect | **Open, not changed**: the score is the matching and scoring path, which this phase does not touch |
| U-6 | "looking for a mechanic for a car" is not matched to a trade ("We couldn't match this to a trade we know") | P2 | vocabulary coverage in the knowledge graph | **Open, not changed**: enrichment is not touched in this phase; P2 recorded no difficulty ("Was there anything you didn't understand? No") |
| U-7 | Clients could not list the skills a job needs; most know only that they need a plumber or an electrician ("it was a bit of a problem for someone to create an account as a client and list the possible skills needed for a certain job", as reported by the author) | [CONFIRM: who ran the test, device, date] | the form asked for something clients could not supply; and what they could type (skills in their own words) matched nothing | **Fixed, pending retest, in `b313756`**: the form asks "What do you need done?" first, then a short title, and skills are optional; the result screen says plainly when none were listed. The ranking effect of a posting with no skills is accepted and documented (`docs/limitations.md`, items 41 and 42) |
| U-8 | The availability field on the job form did not make sense for a client: "When is it needed?" reads as a date, but the field holds a working pattern (Full-time, Part-time, Weekends) that is compared with a worker's availability | [CONFIRM: tester, device, date] | wording of a field | **Fixed, pending retest, in `3975f71`**: the label reads "What working pattern does the job need?", the empty choice "No fixed pattern", with a hint that it is compared with when each worker is available. The stored values are unchanged and there is no date field |
| U-9 | Clients could not open the workers shown in the trade list; most of those workers come from the evaluation dataset and have no name or contact details | [CONFIRM: tester, device, date] | expectation against the data: only a worker who named themselves and consented can be opened | **Fixed, pending retest, in `3975f71`**: a sentence under the heading says which workers can be opened and which cannot; an openable card looks openable (whole card a link, "Open profile" cue, visible focus, tall target); plain cards stay plain. Which workers appear, their number and their order are unchanged. The demo seed now has two consenting workers each in the carpenter, electrician and cook trades. See `docs/limitations.md` item 32 |
| U-10 | The button on the client post page read "Posting…" when a second job was being posted after "Post another job" ("when posting another job the button was 'posting….'") | R2-C1 | defect: the same cause as U-2 (a busy flag set by a successful submit and never cleared, on a page Next keeps mounted) | **Fixed, pending retest, in `580dfac`** |
| U-11 | No details of the job on the matches list ("have descriptions about the job. It's fine to have match but have the details about the job too"); Round 1's P1 had said "a worker might want to click the title of the job for more information" | R2-W1; also P1 (Round 1) | usability gap: the screens showed a title, place, pay and score but not what the job is | **Fixed, pending retest, in `fc731e9`**: an excerpt on each card and the full description on "Why this job?" |
| U-12 | "Fundi wa stima" not recognised ("fundi was stima should work as fundi was umeme") | R2-W1 | limitation, by design: the term is withheld from the knowledge graph as the evaluation's held-out term | **Not fixed.** `docs/limitations.md`; known and expected (the pack says so) |
| U-13 | Jobs chosen by pay and distance ("job 4 cause it pays more. Job 2 because it's close to home and pays more than the rate"); Round 1's P3 chose by pay too | R2-W1; also P3 (Round 1) | extends U-5: workers read pay and place first, and the match score does not follow them | **Open, not changed** (scoring) |
| U-14 | Clients' own jobs outside the vocabulary: "looking for a mechanic for a car" (Round 1, P2), "Fix an analogue radio" (R2-C1), "Roof repairer" (R2-C2): each got "We couldn't match this to a trade we know" | P2 (Round 1), R2-C1, R2-C2 | limitation: the system knows ten trades; extends U-6 | **Not fixed.** `docs/limitations.md` |
| U-15 | If the app fails to match, offer a dropdown to select the job ("if the app fails to match you can have a dropdown to select the job description") | R2-C2 | future work | **Not built.** A picker of trades would bring back the category field that was removed from postings (FR-02, DR-02) because it equals the relevance label; recorded in `docs/limitations.md` |
| U-16 | A Swahili interface ("have the UI translate to Swahili") | R2-W1 | future work | **Not built.** `docs/limitations.md` |

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

---

## Worker sessions, and the U-7 retest

**No feedback was received for the Round 1 worker sessions.** Nothing about them is recorded here. Round 2 has one worker session (R2-W1, below).

**U-7 retest result (skills optional on the job form):** [CONFIRM: who retested, device, date, and what happened].

---

# Round 2

Copied from `docs/context/Testing-Round 2.md`, as written. Nothing is corrected or interpreted. **Codes:** R2-W1 = T1 (worker), R2-C1 = T2 (client), R2-C2 = T3 (client). **Not recorded for any of the three** (so "[CONFIRM]" until the author supplies them): live or recorded; step times; hesitations; hints and their words; the Single Ease Question score; task success; the commit under test; the date and time; whether the session was moderated. (The Round 2 plan, `handoff/32-usability-pack-round2.md`, was live and moderated, but whether each session was is not written down.)

## R2-W1 (T1): worker

| Field | As recorded |
|---|---|
| Card | phone number 700 000 105, PIN 4821 (card D) |
| First name | Baraka |
| Last name | **Tester**. *The card says "Testa".* Entered as "Tester", and recorded so; whether the participant or the author typed it, and whether it was a slip, is [CONFIRM] |
| Device, browser | laptop, Chrome |
| Step times, hesitations, hints, SEQ, task success, live or recorded, commit | not recorded [CONFIRM] |

**Comments made (verbatim):** fundi was stima should work as fundi was umeme.

**Which job would you have chosen? (verbatim):** job 4 cause it pays more. Job 2 because it's close to home and pays more than the rate.

**Was anything not understandable? (verbatim):** yes have descriptions about the job. It's fine to have match but have the details about the job too.

**Future work (verbatim):** have the UI translate to Swahili

## R2-C1 (T2): client

| Field | As recorded |
|---|---|
| Card | phone number 700 000 202, PIN 4821 (card F) |
| Device, browser | phone, Chrome |
| Step times, hesitations, hints, SEQ, task success, live or recorded, commit | not recorded [CONFIRM] |

**Comments made (verbatim):** when posting another job the button was "posting…."

**Screenshot ("View screenshot sent"):** described, not committed (a phone screenshot's status bar shows personal details). It shows the "Your job has been posted." screen on a phone in Chrome for the job **"Fix an analogue radio"**: "We couldn't match this to a trade we know. Your posting is live and will still be matched on its wording.", then the sentence that no skills were listed and that the trade was read from the description, and the "Post another job" link at the foot. The stuck button itself is not in the picture.

**Was anything not understandable? (verbatim):** No

## R2-C2 (T3): client

| Field | As recorded |
|---|---|
| Card | phone number 700 000 203, PIN 4821 (card G) |
| Device, browser | phone, Chrome |
| Step times, hesitations, hints, SEQ, task success, live or recorded, commit | not recorded [CONFIRM] |

**Comments made (verbatim):** it's easy. If the app fails to match you can have a dropdown to select the job description

**Screenshot ("View screenshot"):** described, not committed. It shows the same screen for the job **"Roof repairer"** with "We couldn't match this to a trade we know…", and the sentence "We match on the skills you listed above, and nothing else. We didn't recognise "Patch roof leaks", so we kept it exactly as you wrote it." (so this client had listed one skill, "Patch roof leaks").

**Was anything not understandable? (verbatim):** No everything

*Note on the wording "No everything": copied as written; whether it means "no, nothing" is not interpreted here.*

