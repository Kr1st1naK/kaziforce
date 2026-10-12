# Vocabulary report: alias table, ESCO mapping, dictionary evidence and review proposals

Sprint 2, Tasks A and A2 (S2-3/S2-4/S2-5 groundwork). Branch `sprint-2/vocabulary`.
First prepared 2026-10-05; updated 2026-10-06 for the author's decisions and the review step.

> **Status 2026-10-06:** the author's decisions have since been applied (files in
> `data/vocabulary/decisions/`): 16 aliases accepted (14 in the KG; fundi wa stima and mshonaji
> held out), 5 rejected, 25 pending, and ESCO selections made for all 10 shortlisted areas.
> The sections below describe the state *before* those decisions.

At the time of writing, nothing was accepted: every alias was `pending_review` or `rejected`,
`kg_included` was `undecided` everywhere and `selected` in `area_esco_map.csv` was empty. All
outcomes below are proposals for the author, who applies decisions with
`scripts/apply_vocabulary_decisions.py` (§9).
The one-line-per-alias view is `docs/vocabulary-review-sheet.md`.

## 1. What was checked

| Check | Source | Result files |
|---|---|---|
| Area → ESCO occupation (subset) | Local ESCO subset (`data/raw/esco/`, downloaded 2026-09-30; 128 occupations) | `data/vocabulary/area_esco_map.csv` |
| ESCO candidates outside the subset | Public ESCO web API `/search`, 14 label queries, ≥1 s apart; subset not changed | `data/vocabulary/esco_search_candidates.csv` |
| Lexical validity of aliases and components | (a) kaikki.org Swahili extract of English Wiktionary, file dated 2026-10-03; (b) Swahili Wiktionary pages, fetched 2026-10-06 via the sw.wiktionary API (2 batched requests, 1.1 s apart) | `data/vocabulary/dictionary_evidence.csv`, dictionary columns of `aliases.csv` |
| Absence checks; occupations category | English Wiktionary API, 3 requests | This report |
| Usage evidence (held-out candidates only) | Web search results (titles and snippets only; no pages opened; listing and classified sites excluded) | `data/vocabulary/usage_evidence.csv` |
| Second sources | bab.la, MobiTUKI: not consulted automatically (§6) | `data/vocabulary/manual_dictionary_checks.csv` |

**Not checked:** speaker validation, a usage survey, Sheng, and any usage evidence beyond the two
held-out candidates. Dictionary presence shows that a word is valid Swahili, not that the phrase
is used by Kenyan workers.

**Reused code.**
- **Reused:** `kaziforce_api.data.loaders` provides `load_esco_data()`, `ESCO_DIR` and
  `VOCABULARY_DIR`, used by `map_vocabulary_areas.py`. `search_esco_occupations.py` reuses
  `get_json()` from `scripts/download_esco.py`.
- **Not reused:** `normalize_skill()` (it keeps `-+/#.` and has no Swahili variants).
  `kaziforce_kg` must not import from `apps/`, so it has its own normaliser and CSV loader.

## 2. Decisions log

| Date | Decision (author) | Where recorded |
|---|---|---|
| 2026-10-05 | mchoraji rejected: **ambiguous (painter/artist)** | `aliases.csv` notes |
| 2026-10-05 | mtambuzaji rejected (not found in any dictionary); msuluhishi rejected (means arbitrator); both belong to **area 6 Welder** | `aliases.csv` |
| 2026-10-05 | "vifaa / umeme repairer" rejected (not a term) | `aliases.csv` |
| 2026-10-05 | mpaka rangi, fundi rangi, fundi seremala added as pending; welder, fundi wa kuchomelea, fundi wa chuma added as UNVERIFIED | `aliases.csv` |
| 2026-10-05 | Registers: rows 13, 14, 17(b, c), 19, 20 descriptive; plumber, carpenter english_label | `aliases.csv` |
| 2026-10-05 | README cells read as in this report (fragments kept literally and flagged) | this report §3 |
| 2026-10-05 | **Shortlist approved:** areas 1, 2, 3, 4, 7, 10, 11, 12, 15, 16; slots 11–12 left empty | `data/vocabulary/README.md`; `shortlisted` in `area_esco_map.csv` |
| 2026-10-05 | Held-out candidates: fundi wa stima (Electrician), fundi seremala (Carpenter), **eligible only with usage evidence** | §7 |
| 2026-10-05 | makanika, mshonaji, msusi, dobi, mpikaji, mwendeshaji added as pending | `aliases.csv` |
| 2026-10-05 | README Validation line keeps "Dictionary agreement shows that a term is valid Swahili, not that it is in common informal use." | `data/vocabulary/README.md` |
| 2026-10-06 (Q&A) | `proposed_sense_ok` is a separate column, copied into `sense_ok` on acceptance; my ESCO proposals go in `proposed` columns and count as resolving ambiguity for "accept, medium"; acceptance is refused for areas without a selected occupation; usage evidence from search results only | §8, §9 |

## 3. Alias table (`data/vocabulary/aliases.csv`)

46 rows: 42 `pending_review` and 4 `rejected`. Registers: 25 trade_name, 14 descriptive,
3 english_label and 4 rejected.

**Columns added in A2:**

- **`proposed_sense_ok`, `proposed_status`, `confidence`, `proposed_reason`:** filled by
  `scripts/propose_vocabulary_status.py`.
- **`decision_date`:** filled by the apply script.

**Interpretations from Task A, confirmed by the author:**

- **README fragments kept literally and flagged:** `vifaa vya kielektroniki`, `utoaji` and
  `matengenezo ya jumla`.
- **Registers I proposed:** fundi wa vifaa vya nyumbani, vifaa vya kielektroniki and
  mfanyakazi wa kufulia (descriptive); fundi wa kuchomelea and fundi wa chuma (trade_name).
- **`courier`:** descriptive, per the author's rule for row 19.

`sense_ok` is still `unclear` on all pending rows: it is the author's column. My evidence-based
value is in `proposed_sense_ok`, and its basis is appended to `notes` as `[sense basis: …]`.

## 4. ESCO mapping

### 4.1 Within the subset

Rule: an occupation matches when an area name equals its preferred label or an alternative
label (case-insensitive, hyphens read as spaces). Keyword-only hits are `related` context rows.
The full list is in `area_esco_map.csv`.

| # | Area | Exact matches (subset) | Status |
|---|---|---|---|
| 1 | Electrician | electrician 7411.1 (pref); domestic electrician, industrial electrician, electrical mechanic (alt) | several |
| 2 | Plumber | plumber 7126.8 (pref); pipe welder 7212.3.3 (alt) | several |
| 3 | Carpenter | carpenter 7115.1 (pref) | one |
| 4 | Mason / bricklayer | bricklayer 7112.1 (pref) | one |
| 5 | Painter | — | none |
| 6 | Welder | welder 7212.3 (pref); laser beam welder (alt) | several |
| 7 | Motor-vehicle mechanic | vehicle technician 7231.10 (alt) | one (same as area 8) |
| 8 | Motorcycle mechanic | vehicle technician 7231.10 (alt) | one (same as area 7) |
| 9 | Appliance / electronics repairer | consumer electronics repair technician 7421.3 (alt) | one |
| 10 | Mobile-phone repairer | mobile phone repair technician 7422.3.1 (alt) | one |
| 11 | Tailor / dressmaker | tailor 7531.5, dressmaker 7531.2 (both pref) | several |
| 12 | Hairdresser / barber | hairdresser 5141.1, barber 5141.1.1 (both pref) | several |
| 13 | Beauty worker | — | none |
| 14 | Domestic cleaner | domestic cleaner 9111.1 (pref) | one |
| 15 | Laundry worker | laundry worker 8157.1 (pref); laundry ironer (alt) | several |
| 16 | Cook / catering worker | cook 5120.1 (pref); industrial cook (alt) | several |
| 17 | Gardener / grounds worker | garden labourer 9214.1 (alt) | one |
| 18 | Driver | hearse driver 8322.3 (alt "driver"; semantically wrong) | one |
| 19 | Delivery / courier worker | — | none |
| 20 | General construction / maintenance worker | — | none |

### 4.2 Full ESCO API search (Task 1)

The public ESCO API was searched by label for the five weak areas. These are the most relevant
candidates; all 102 result rows, with ranks and URIs, are in `esco_search_candidates.csv`.
"In subset" means the occupation is already among the 128 local occupations. **The subset was
not changed.**

| Area | Candidate | ISCO | In subset | URI | Query |
|---|---|---|---|---|---|
| 5 Painter | construction painter | 7131.1 | yes | http://data.europa.eu/esco/occupation/15620506-fb5d-49cd-87a2-1c9047fb406a | painter, house painter, decorator |
| 5 Painter | paperhanger | 7131.2 | yes | http://data.europa.eu/esco/occupation/a2abd144-2a36-45ea-919c-1fcc6ebc5d45 | decorator |
| 5 Painter | transport equipment painter | 7132.3 | no | http://data.europa.eu/esco/occupation/a784b063-89cf-441b-9624-deed9dbdeae6 | painter |
| 5 Painter | decorative painter | 7316.1 | no | http://data.europa.eu/esco/occupation/41a51397-089d-459d-9b7e-f1cdee5ad6bb | painter |
| 5 Painter | artistic painter | 2651.1 | no | http://data.europa.eu/esco/occupation/374d925a-107b-4c99-bc8b-75483441f062 | painter |
| 13 Beauty | aesthetician (hit: "beautician") | 5142.1 | yes | http://data.europa.eu/esco/occupation/a1e1a788-2352-4172-8fcf-1f985a6968b0 | beautician |
| 13 Beauty | beauty salon attendant | 5142.2 | yes | http://data.europa.eu/esco/occupation/d3fd0898-51f7-42a3-8f44-09408fc796f6 | beauty |
| 13 Beauty | pedicurist | 5142.8 | yes | http://data.europa.eu/esco/occupation/489b9a38-89a2-425c-95b9-79cec66379e1 | beauty |
| 13 Beauty | hair removal technician | 5142.3 | yes | http://data.europa.eu/esco/occupation/72413d91-f212-4ad6-bf95-8b78a37c041a | beauty |
| 18 Driver | taxi driver | 8322.7 | yes | http://data.europa.eu/esco/occupation/6f7c1e84-8162-4c20-a575-b57ff624eef5 | driver, chauffeur |
| 18 Driver | private chauffeur | 8322.6 | yes | http://data.europa.eu/esco/occupation/e75305db-9011-4ee0-ab62-8d41a98f807e | chauffeur |
| 18 Driver | hearse driver | 8322.3 | yes | http://data.europa.eu/esco/occupation/af513bd8-4340-4452-aa30-05a073ecc49a | driver |
| 18 Driver | bus driver | 8331.1 | no | http://data.europa.eu/esco/occupation/00cee175-1376-43fb-9f02-ba3d7a910a58 | driver |
| 18 Driver | cargo vehicle driver | 8332.2 | no | http://data.europa.eu/esco/occupation/45037d43-a8f5-4f46-b332-b2935bc305f4 | driver, courier |
| 19 Courier | motorcycle delivery person | 8321.1 | yes | http://data.europa.eu/esco/occupation/b5f6bb2c-0602-484d-a87f-9cac33f83010 | courier, delivery |
| 19 Courier | delivery driver | 8322.2 | yes | http://data.europa.eu/esco/occupation/0c408028-c48f-4df8-ba5d-c3d3be15f5a2 | delivery |
| 19 Courier | bicycle courier | 9331.1 | no | http://data.europa.eu/esco/occupation/3a959644-beed-4afc-8e57-d5068ae6a43e | courier, messenger |
| 19 Courier | postman/postwoman | 4412.2 | no | http://data.europa.eu/esco/occupation/7ed2e153-8da8-4c0d-b4c5-3402c623f34b | courier, delivery, messenger |
| 20 Construction | building construction worker | 9313.1 | yes | http://data.europa.eu/esco/occupation/fb7e2f4f-1545-42f1-972e-94082e49c6dc | construction labourer, construction worker |
| 20 Construction | handyman | 9622.1 | no | http://data.europa.eu/esco/occupation/f4a25243-b06a-42a9-9c69-246853df63ad | building maintenance, handyman |
| 20 Construction | civil engineering worker | 9312.1 | no | http://data.europa.eu/esco/occupation/47300afa-5496-484c-8f65-14247a98b2b8 | construction worker |
| 20 Construction | construction scaffolder | 7119.1 | no | http://data.europa.eu/esco/occupation/18fa8080-3156-429a-bbd7-b3ef559b6721 | construction labourer |
| 20 Construction | building cleaner | 9112.2 | no | http://data.europa.eu/esco/occupation/303a1e34-cb16-4054-b323-81e5eec17397 | building maintenance |

**Reading:**

- **Painter, Beauty and Driver already have good in-subset candidates:** construction
  painter; aesthetician or beauty salon attendant; taxi driver or private chauffeur. They are
  "none" in §4.1 only because the area names don't equal an ESCO label.
- **Courier is partly covered:** motorcycle delivery person 8321.1 is in the subset.
- **General construction / maintenance is not covered:** its best fit, **handyman 9622.1**,
  is outside the subset (ISCO 9622 was not downloaded).

These five areas are not shortlisted, so none of this blocks the current work.

### 4.3 Proposed ESCO occupation per shortlisted area (Task 2)

These are written to `proposed = yes` with a `proposed_reason` in `area_esco_map.csv`;
`selected` is left empty. Re-running `map_vocabulary_areas.py` keeps `shortlisted`, `proposed`,
`proposed_reason` and `selected`.

| Area | Proposed | Reason |
|---|---|---|
| 1 Electrician | electrician 7411.1 | Only preferred-label match; the others are specialisations or alt-label hits |
| 2 Plumber | plumber 7126.8 | Preferred-label match; pipe welder matched only through a stray alt label |
| 3 Carpenter | carpenter 7115.1 | Only match, on the preferred label |
| 4 Mason / bricklayer | bricklayer 7112.1 | Only match; the subset has no separate mason occupation |
| 7 Motor-vehicle mechanic | vehicle technician 7231.10 | Only match; its alt label is "motor vehicle mechanic", which fits makanika and fundi wa magari |
| 10 Mobile-phone repairer | mobile phone repair technician 7422.3.1 | Only match; its alt label is the area name |
| 11 Tailor / dressmaker | tailor 7531.5 | fundi wa nguo and mshonaji make general garments; dressmaker is the narrower occupation |
| 12 Hairdresser / barber | barber 5141.1.1 **and** hairdresser 5141.1 | Two occupations, mapped per alias: kinyozi → barber, msusi → hairdresser |
| 15 Laundry worker | laundry worker 8157.1 | Preferred-label match; laundry ironer matched only through an alt label |
| 16 Cook / catering worker | cook 5120.1 | Preferred-label match; industrial cook matched only through the alt label "catering worker" |

## 5. Dictionary evidence

### 5.1 Sources and combined rule (Task 3)

Each alias, its full phrase and each content word are looked up in both sources.
`dictionary_evidence.csv` has one row per (alias, component, source).

- **kaikki_en:** headword, or an inflected or alternative form of one (mabomba → bomba,
  kufulia → fulia).
- **sw_wiktionary:** a page with a Swahili section (`{{sw}}`, `{{-|sw}}`, `{{--|sw}}` or a
  "Kiswahili" header), or a page for a ku- verb's stem. Pages that are English words
  (courier, repairer) or other languages (wa: Yoruba, la: Kinyarwanda) do not count.
- **Combined:** `found_exact` if the phrase is a headword in either source; `found_components`
  if every content word is found in at least one source; `not_found` otherwise; `not_checked`
  for English labels.

| dictionary_check | Rows (46) |
|---|---|
| found_exact | 17: fundi bomba, fundi wa nguo, mwashi, kinyozi, mama fua, mpishi, mtunza bustani, dereva, utoaji, makanika, mshonaji, msusi, dobi, mpikaji, mwendeshaji; rejected mchoraji, msuluhishi |
| found_components | 24 |
| not_found | 1: mtambuzaji |
| not_checked | 4: plumber, carpenter, welder, courier |

### 5.2 What the Swahili Wiktionary changed

| Alias / word | Change |
|---|---|
| fundi wa nguo | New **whole-phrase entry** (tailor): found_components → found_exact |
| fundi wa kuchomelea | *kuchomelea* has a short sw page (welding), so not_found → found_components. The page is low quality; treat it as weak evidence |
| stima | sw page lists it as a **Kenyan synonym of umeme**, which supports fundi wa stima |
| mfanyikazi | sw page translates the variant as **maid** (domestic helper), unlike mfanyakazi (worker). This affects 6 descriptive aliases |
| uwasilishaji | sw adds **delivery** to presentation/submission |
| utoaji | sw gives money **withdrawal**; kaikki gives issuing/delivery. Neither is a worker |
| mchoraji | sw gives **artist** only, which is consistent with "ambiguous (painter/artist)" |
| dobi | sw translates it as dry cleaner (kaikki: launderer) |
| mwendeshaji | sw: operator or driver of a vehicle, machine or organisation; a generic agent noun |

### 5.3 Hits whose sense is not a trade (from Task A, still valid)

| Alias | Issue |
|---|---|
| mpaka rangi | Head *mpaka* = border/until; the phrase has no entry |
| mama fua | Head *mama* = mother; the phrase entry covers cleaning **and** laundry |
| vifaa vya kielektroniki | *vifaa* = devices; there is no person noun |
| matengenezo ya jumla | Activity noun; *jumla* can also mean wholesale |
| msuluhishi (rejected) | Arbitrator / adjudicator |

### 5.4 Swahili "Occupations" entries (Task A, report only)

272 occupation-tagged headwords in the kaikki snapshot (277 in the live category). Of the strong
unlisted candidates reported in Task A, the author added makanika, mshonaji, msusi, dobi,
mpikaji and mwendeshaji. Still unlisted: seremala on its own, mshoni, msuka/msukaji (braider),
mhunzi (blacksmith), mfagiaji, topasi, mwosha, mpishi mkuu, mwokaji, dereva wa basi, mjumbe,
msafirishaji, porters (mchukuzi, mpagazi, hamali, mbebaji), kuli and contractors (mkandarasi,
kontrakta).

## 6. Second sources: access decisions and manual-check list

- **bab.la:** returned HTTP 403 to an identified script, and its terms could not be read.
  Not used.
- **MobiTUKI:** publishes no terms of use; its content is © TUKI and the site is not affiliated
  with TUKI. Not used.

No lookups were made on either site. `manual_dictionary_checks.csv` now lists **74 terms**
(14 priority 1), including the 6 aliases added on 2026-10-05, with untested inferred URLs and
blank result columns. kuchomelea is priority 1 because it appears only in sw.wiktionary.

## 7. Shortlist and held-out candidates

**Shortlist (approved):** 1 Electrician, 2 Plumber, 3 Carpenter, 4 Mason / bricklayer,
7 Motor-vehicle mechanic, 10 Mobile-phone repairer, 11 Tailor / dressmaker, 12 Hairdresser /
barber, 15 Laundry worker, 16 Cook / catering worker. Slots 11–12 are empty.

**Usage evidence (Task 5).** Method:

- **Queries:** `"fundi wa stima" Kenya`, `"fundi seremala"`, and two news/video variants.
- **Exclusions:** classified and listing sites (jiji, pigiame, olx, kupatana), Glosbe and
  Facebook.
- **Counting rule:** a result counts only if its **title** contains the exact term. The search
  tool's prose summaries were not treated as snippets, and no page was opened.
- **What is recorded:** alias, URL, page title and access date only.

| Alias | Evidence (title) | URL | Quality |
|---|---|---|---|
| fundi wa stima | "Fundi Wa Stima" (TikTok topic page) | https://www.tiktok.com/discover/fundi-wa-stima | Topic index page; social media |
| fundi wa stima | "Fundi Wa Stima Feki" (YouTube video) | https://www.youtube.com/watch?v=mf0Zcy-o0tg | Video; origin not stated |
| fundi seremala | "Fundi seremala asimulia alivyomuokoa mtoto aliyeibwa kanisani Dar" | https://www.mwananchi.co.tz/mw/habari/kitaifa/fundi-seremala-asimulia-alivyomuokoa-mtoto-aliyeibwa-kanisani-dar-2932548 | News; **Tanzanian** |
| fundi seremala | JamiiForums thread with the term in its title | https://www.jamiiforums.com/threads/mnaosema-yesu-ni-mungu-msisahau-kuwa-yesu-alikuwa-fundi-seremala-ili-kujipatia-riziki-yake.1671272/page-8 | Forum; **Tanzanian** |

Not counted: a Taifa Leo (Kenya) article that the search summary linked to an electrician, but
whose title does not contain the term; a Tanzanian job-board post and a single-business map
entry for fundi seremala.

**Eligibility:** both candidates meet the agreed bar (≥1 usage URL), so both are **eligible**.
The evidence is thin, though:

- **fundi wa stima:** social-media titles only.
- **fundi seremala:** Tanzanian sources only, with no Kenyan usage found.

`kg_included` is still `undecided`; holding them out is the author's call.

## 8. Proposal rules (Task 4)

Implemented in `scripts/propose_vocabulary_status.py` (pure `propose()` function, tested in
`tests/test_propose_vocabulary_status.py`).

**`proposed_sense_ok`** is judged only from a dictionary entry for the *whole* alias (the
phrase, or the word for a single-word alias) in either source:

- **yes:** an English gloss names the area's occupation (`AREA_OCCUPATION`, e.g. area 12:
  barber, hairdresser, braider).
- **no:** the entry exists and has glosses, but none names that occupation.
- **unclear:** there is no whole-alias entry, or the entry has no English gloss.

**Effective sense** = `sense_ok` if the author has set yes/no; otherwise `proposed_sense_ok`.

Rules, applied in order (first match wins):

1. **recommend_reject (high):** already rejected by author decision; or not found and no
   component found; or effective sense = no.
2. **needs_human**, if any of these holds:
   - the register is not trade_name (descriptive, english_label);
   - the area is not shortlisted;
   - the alias has no single ESCO occupation (the area has no selected or proposed occupation,
     or several and the alias's glosses don't pick one);
   - the whole-alias glosses also name another area's occupation (ambiguous across areas,
     e.g. mama fua: laundry and cleaning).
3. **recommend_accept (high):** trade_name, found_exact, and effective sense = yes.
4. **recommend_accept (medium):** trade_name, all components found, and every complement's
   glosses fit the area's domain words (`AREA_DOMAIN`, e.g. area 1: "electric"), with ESCO
   resolved.
5. **needs_human:** everything else.

**Notes:**

- **ESCO dependence:** where ESCO is resolved only by my proposal (§4.3), the accept reason says
  "Claude's proposal; needs your confirmation". Every current accept proposal is in this
  position, because `selected` is empty.
- **Confidence values:** `high` for all rejects, blank for needs_human.
- **Evidence shown:** each review-sheet line gives my gloss note (≤5 words, my own words; no
  dictionary text is copied into committed files) and the dictionary entry URLs.

**Outcome (46 aliases):**

| Group | Count | Aliases |
|---|---|---|
| Accept, high | 10 | fundi bomba, mwashi, makanika, fundi wa nguo, mshonaji, kinyozi, msusi, dobi, mpishi, mpikaji |
| Accept, medium | 6 | fundi wa umeme, fundi wa stima, fundi wa mbao, fundi seremala, fundi wa magari, fundi wa simu |
| Needs judgement | 25 | 13 descriptive rows (all but utoaji) and 3 English-label rows; mama fua (cross-area); trade names outside the shortlist: mpaka rangi, fundi rangi (5), fundi wa kuchomelea, fundi wa chuma (6), fundi wa pikipiki (8), mtunza bustani (17), dereva, mwendeshaji (18) |
| Reject | 5 | mchoraji, mtambuzaji, msuluhishi, vifaa / umeme repairer (author decisions); utoaji (sense: no worker reading) |

Every shortlisted area has at least one accept proposal. Areas 1 and 3 have two medium trade
names each, one of which is the held-out candidate.

## 9. Applying decisions (Task 7)

`scripts/apply_vocabulary_decisions.py --decisions FILE [--validated-by author] [--date YYYY-MM-DD]`
(template: `data/vocabulary/decisions_template.csv`). **It has not been run on the real data.**

```
scope,area_id,alias,decision,esco_uri,notes
area,2,,approve_proposed,,
alias,2,fundi bomba,accepted,,
area,12,,approve_proposed,,
alias,12,kinyozi,accepted,http://data.europa.eu/esco/occupation/4e0c14d6-b170-40f1-bcdc-703c0b92109b,
alias,19,utoaji,rejected,,Activity noun
```

- **Area rows run first and replace the area's selection.** `approve_proposed` copies
  `proposed` → `selected`; `select` with an `esco_uri` picks one candidate.
- **Alias rows** set `status`, `validated_by` and `decision_date`.
- **`accepted`:**
  - copies `proposed_sense_ok` → `sense_ok`;
  - sets `esco_uri`/`esco_label` from the area's selected occupation;
  - is **refused** if the area has no selected occupation, or has several and the row names
    none of them.
- **`rejected`:** sets register to `rejected` (the old register is kept in notes) and needs a
  reason.
- **Safety:** every row is validated before anything is written, so any error leaves both
  files unchanged. Rows are never added or deleted.

## 10. Normalisation, loader and tests

`kaziforce_kg.vocabulary.normalize_alias()` applies NFKC, casefolding, punctuation removal
(apostrophes deleted) and whitespace collapsing. It drops the optional "wa" and maps
mafundi→fundi, stimu→stima and mfanyikazi→mfanyakazi on whole tokens. Synonyms are not merged.

`load_kg_vocabulary()` returns only `status=accepted` and `kg_included=yes` rows, and refuses a
held-out alias that normalises to an included one.

**Tests: 75 pass, and ruff is clean.**

- **`test_vocabulary.py`:**
  - normalisation;
  - loader filtering and held-out leak checks;
  - aliases.csv integrity;
  - shortlist and proposals in the area map;
  - regeneration keeps manual columns;
  - usage evidence has no contact details and stays in sync with aliases.csv.
- **`test_dictionary_check.py`:** sw.wiktionary parsing and the combined check.
- **`test_propose_vocabulary_status.py`:** one case per rule, precedence, and per-alias ESCO
  disambiguation.
- **`test_apply_vocabulary_decisions.py`:** runs on temporary copies only.

The tests read only committed files and fixtures, so CI does not need the raw caches.

## 11. Open issues

1. **Review the sheet** and write a decisions file. The ESCO choices (§4.3) come first, because
   acceptance depends on them.
2. **Held-out decision.** Both candidates are eligible on thin evidence (§7). Decide whether
   Tanzanian-only evidence is enough for fundi seremala; then set `kg_included`. The apply
   script does not set `kg_included`, so edit it by hand or extend the script.
3. **Sprint-plan targets are still far off.** S2-4 asks for ≥5 terms per area and ≥50 in total;
   the 10 shortlisted areas have 20 pending aliases, of which 16 are accept proposals. A KG
   built from only the accept proposals would cover each area with 1–2 trade names.
4. **Usage evidence covers only the two held-out candidates.** Every other alias is backed by
   dictionaries only.
5. **The 6 `mfanyikazi` aliases** may carry a "maid" reading in Kenyan usage (§5.2).
6. **Manual second-source checks** (§6), then the S2-5 validation log and the `vocab-v1` tag.
7. **Schema mismatch with S2-4:** the sprint plan has a single register column with a Sheng
   value; `aliases.csv` separates `language` and `register` and has no `sheng`.
8. **The synthetic generator was not touched.** It still uses old terms and must be regenerated
   from the frozen vocabulary (S2-6).

## 12. Reproduce

    python scripts/map_vocabulary_areas.py --print-summary        # needs data/raw/esco/
    python scripts/search_esco_occupations.py                     # ESCO web API, ~14 requests
    python scripts/fetch_sw_wiktionary.py                         # sw.wiktionary API, 2 requests
    python scripts/check_vocabulary_dictionary.py                 # needs both dictionary caches
    python scripts/propose_vocabulary_status.py --sheet           # rewrites proposals + review sheet
    pytest
