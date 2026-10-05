# Vocabulary report: alias table, ESCO mapping and dictionary evidence

Sprint 2, Task A (S2-3/S2-4 groundwork). Prepared 2026-10-05 on branch `sprint-2/vocabulary`.
Nothing here is final: every alias is `pending_review` or `rejected`, `kg_included` is `undecided`
everywhere, and the area shortlist (§7) awaits author approval.

## 1. What was checked

| Check | Source | Result files |
|---|---|---|
| Area → ESCO occupation | Local ESCO subset (`data/raw/esco/`, downloaded 2026-09-30) | `data/vocabulary/area_esco_map.csv` |
| Lexical validity of every alias and its components | kaikki.org Swahili extract of Wiktionary, file dated 2026-10-03 (21,306 entries; see `data/raw/kaikki/README.md`) | `data/vocabulary/dictionary_evidence.csv`, dictionary columns of `aliases.csv` |
| Absence of not-found terms; occupations category | Wiktionary API, 3 requests, 1.1 s apart, descriptive User-Agent | This report |
| Second-source checks | bab.la, MobiTUKI: not consulted automatically (§6) | `data/vocabulary/manual_dictionary_checks.csv` |

**Not checked:** usage in real job ads or speech (no usage survey; Glosbe and listing sites were
not used), speaker validation, and Sheng. Dictionary presence shows a word is valid Swahili, not
that the phrase is used by Kenyan workers.

**Reused code.** `kaziforce_api.data.loaders` provides `load_esco_data()` (dict of the four ESCO
DataFrames, with a clear error if files are missing), `ESCO_DIR`/`VOCABULARY_DIR` and
`KAZIFORCE_DATA_DIR` resolution. Both new scripts use these. Not reused: `normalize_skill()` keeps
`-+/#.` and does not handle apostrophes or Swahili variants, and the KG package must not import
from `apps/`, so `kaziforce_kg.vocabulary` has its own standard-library normaliser and CSV loader.
No existing helper splits `altLabels` (newline-separated); the mapping script does that itself.

## 2. README changes

`data/vocabulary/README.md`: the HTML comment is now well-formed (`<!-- ... -->`, on its own
paragraph) and the Validation line is the agreed wording. The previous sentence "Dictionary
agreement shows that a term is valid Swahili, not that it is in common informal use" was dropped
with it; the same caveat is kept in §1 above. The commit also includes the author's revised
candidate table, which was uncommitted in the working tree.

## 3. Alias table (`data/vocabulary/aliases.csv`)

40 rows: 36 `pending_review`, 4 `rejected`. Registers: 19 trade_name, 14 descriptive,
3 english_label, plus the 4 rejected rows (register `rejected`).

**Author decisions applied:** mchoraji, mtambuzaji, msuluhishi and "vifaa / umeme repairer" are
rejected with reasons; mpaka rangi, fundi rangi and fundi seremala are pending; welder,
fundi wa kuchomelea and fundi wa chuma are pending and marked UNVERIFIED; rows 13, 14, 17(b, c),
19 and 20 are descriptive; plumber and carpenter are english_label.

**My interpretations (please confirm):**

- **README cells were split on "/", "and" and "or", keeping fragments literally.** Three
  fragments are not person nouns: `vifaa vya kielektroniki` (row 9: possibly meant
  "fundi wa vifaa vya kielektroniki"), `utoaji` (row 19) and `matengenezo ya jumla` (row 20).
  Each is flagged in `notes`.
- **Registers I proposed where you gave none:** fundi wa vifaa vya nyumbani, vifaa vya
  kielektroniki and mfanyakazi wa kufulia → descriptive; fundi wa kuchomelea and fundi wa chuma →
  trade_name.
- **`courier` (row 19) is descriptive per your rule, though it reads as an english_label.**
- **mtambuzaji and msuluhishi have no area_id**, because no area was recorded for them.
- **`carpenter` is not in the current README table.** I added it from your decision list.
- **`sense_ok` is `unclear` on all pending rows**, because sense and register are yours to
  judge. It is `no` only where your decision gave a sense reason (mchoraji, msuluhishi).
- **`esco_uri` is filled only where the area has exactly one match on a preferred label:**
  carpenter, bricklayer and domestic cleaner. Every other area waits for your choice in
  `area_esco_map.csv` (`selected` column).

## 4. ESCO mapping

Rule: an occupation matches when an area name equals its preferred label or an alternative
label (case-insensitive, hyphens read as spaces). Keyword-only hits are kept as `related` rows
(82 rows) for context and are not matches. Full list: `area_esco_map.csv`.

| # | Area | Exact matches | Status | Note |
|---|---|---|---|---|
| 1 | Electrician | electrician 7411.1 (pref); domestic electrician 7411.1.1.1, industrial electrician 7411.1.1.2, electrical mechanic 7412.3 (alt) | several | one preferred-label match |
| 2 | Plumber | plumber 7126.8 (pref); pipe welder 7212.3.3 (alt) | several | one preferred-label match |
| 3 | Carpenter | carpenter 7115.1 (pref) | one | clean |
| 4 | Mason / bricklayer | bricklayer 7112.1 (pref) | one | clean; "mason" matches nothing |
| 5 | Painter | — | none | related: construction painter 7131.1 |
| 6 | Welder | welder 7212.3 (pref); laser beam welder 7212.3.2 (alt) | several | one preferred-label match |
| 7 | Motor-vehicle mechanic | vehicle technician 7231.10 (alt) | one | alt label only; **same occupation as area 8** |
| 8 | Motorcycle mechanic | vehicle technician 7231.10 (alt) | one | alt label only; same as area 7 |
| 9 | Appliance / electronics repairer | consumer electronics repair technician 7421.3 (alt) | one | household appliances repair technician 7412.5 only related |
| 10 | Mobile-phone repairer | mobile phone repair technician 7422.3.1 (alt) | one | alt label, but clearly the right occupation |
| 11 | Tailor / dressmaker | tailor 7531.5, dressmaker 7531.2 (both pref) | several | each lists the other as an alt label |
| 12 | Hairdresser / barber | hairdresser 5141.1, barber 5141.1.1 (both pref) | several | |
| 13 | Beauty worker | — | none | related: beauty salon attendant 5142.2, aesthetician 5142.1, … |
| 14 | Domestic cleaner | domestic cleaner 9111.1 (pref) | one | clean |
| 15 | Laundry worker | laundry worker 8157.1 (pref); laundry ironer 8157.1.1 (alt) | several | one preferred-label match |
| 16 | Cook / catering worker | cook 5120.1 (pref); industrial cook 5120.1.4 (alt "catering worker") | several | one preferred-label match |
| 17 | Gardener / grounds worker | garden labourer 9214.1 (alt "gardener") | one | alt only; groundsman 6113.1, landscape gardener 6113.6 related |
| 18 | Driver | hearse driver 8322.3 (alt "driver") | one | **alt match is semantically wrong**; taxi driver 8322.7, private chauffeur 8322.6, delivery driver 8322.2 related |
| 19 | Delivery / courier worker | — | none | related: motorcycle delivery person 8321.1, delivery driver 8322.2 |
| 20 | General construction / maintenance worker | — | none | related: building construction worker 9313.1, house builder 7111.1 |

Summary: 0 matches for 5, 13, 19, 20; one match for 3, 4, 7, 8, 9, 10, 14, 17, 18 (only 3, 4
and 14 via a preferred label); several for 1, 2, 6, 11, 12, 15, 16.

## 5. Dictionary evidence

| dictionary_check | Rows |
|---|---|
| found_exact | 10: fundi bomba, mwashi, kinyozi, mama fua, mpishi, mtunza bustani, dereva, utoaji; rejected mchoraji, msuluhishi |
| found_components | 24 |
| not_found | 2: fundi wa kuchomelea (kuchomelea/chomelea absent from kaikki *and* live Wiktionary), mtambuzaji |
| not_checked | 4 English labels: plumber, carpenter, welder, courier |

Only three multi-word aliases are headwords in their own right: **fundi bomba** and
**mtunza bustani** (both occupation-tagged) and **mama fua** (not tagged, but its sense is
occupational). Every `fundi wa X` phrase is compositional: fundi ("craftsman", occupation-tagged)
plus a found noun.

**Hits whose sense is not an occupation or trade:**

| Alias | Hit | Issue |
|---|---|---|
| mpaka rangi | head *mpaka* | Homograph: border / until. The agent reading from verb *paka* (apply, smear) is plausible but not attested as a phrase |
| mama fua | head *mama* | Mother; the phrase entry carries the trade sense |
| mama fua | phrase | Sense covers cleaning *and* laundry, so it may also fit area 14 |
| vifaa vya kielektroniki | head *vifaa* | Plural of "device/equipment"; no person noun |
| utoaji | headword | Activity noun (issuing/delivery), not a worker |
| matengenezo ya jumla | head *matengenezo* | Activity noun (maintenance/repair); *jumla* also means wholesale |
| mfanyikazi wa uwasilishaji | complement | *uwasilishaji* = submission/presentation, not parcel delivery |
| mchoraji (rejected) | headword | Has a painter sense (not occupation-tagged) besides artist; only "engraver" is tagged. Your rejection stands; the painter sense is noted |
| msuluhishi (rejected) | headword | Arbitrator, which confirms your reason |

Minor complement senses (no flag; listed in `notes`): *stima* is mainly "steamer", with the
electricity sense given as a variant of *stimu*; *mbao* = planks, but also slang for a
twenty-shilling coin; *chuma* = iron, but also slang for girlfriend; *shamba* = farm/field.

### Swahili entries in the "Occupations" category

272 headwords (290 senses) in the snapshot. The live category has 277; the 5 added since are
hedimasta, mpokezi, mvimbaji, mwalimu mkuu and mwezekaji (not inspected). Gloss-keyword matching
to the 20 areas, with false positives removed (mwanahabari and ripota "reporter", mtumishi wa umma
"public servant"):

| # | Already in aliases.csv | Not listed (report only, not added) |
|---|---|---|
| 2 | fundi bomba | — |
| 3 | (seremala via fundi seremala) | **seremala** on its own |
| 4 | mwashi | — |
| 5 | (mchoraji, rejected) | — |
| 6 | — | mhunzi (blacksmith: adjacent trade, not welder) |
| 7 | — | **makanika** (mechanic) |
| 11 | — | **mshonaji**, **mshoni** (tailor, sewer) |
| 12 | kinyozi | **msusi** (hairdresser/braider); msuka, msukaji (braider) |
| 14 | — | mfagiaji (sweeper), topasi, mwosha (cleaner/washer), mtumishi (servant), yaya (nanny) |
| 15 | — | **dobi** (laundryman/washerwoman), topasi, mwosha |
| 16 | mpishi | **mpikaji** (cook), mpishi mkuu (chef), mwokaji (baker) |
| 17 | mtunza bustani | — |
| 18 | dereva | **mwendeshaji** (driver), dereva wa basi (bus driver) |
| 19 | — | mjumbe (messenger), msafirishaji (transporter), mchukuzi, mpagazi, hamali, mbebaji (porter/carrier) |
| 20 | — | kuli (labourer/dockworker), mkandarasi, kontrakta, mwanakandarasi (contractor), mnyapara, mkadamu (foreman) |

None of areas 1, 8, 9, 10 or 13 has an occupation-tagged entry. **Bold** marks the strongest
unlisted candidates: an occupation-tagged headword whose English gloss names the area itself.

## 6. Second sources: access decisions and manual-check list

- **bab.la:** robots.txt allows dictionary paths, but the site returned **HTTP 403** to an
  identified non-browser client, and its terms page could not be read. Treated as not permitted.
- **MobiTUKI (swahili-dictionary.com):** robots.txt disallows only `/static/pages/*`, but the site
  publishes **no terms of use**. Its content is © TUKI (University of Dar es Salaam) and the site
  says it is not affiliated with TUKI, so nobody there can grant reuse. Lookups also run
  client-side, so a page fetch would not return entries. Treated as not permitted.

No lookups were made on either site. `data/vocabulary/manual_dictionary_checks.csv` lists
68 terms (14 at priority 1), each with a bab.la and a MobiTUKI URL, plus blank `babla_result`,
`mobituki_result` and `checked_on` columns for you to fill. **The URL patterns are inferred and
were not tested**, since testing them would be a lookup: bab.la `…/dictionary/swahili-english/<word>`
(spaces → hyphens) and MobiTUKI `…/swahili-english/<word>` (spaces → underscores). If a link
fails, search the term from the site's home page. Priority 1:

| Term | Why |
|---|---|
| kuchomelea, chomelea, fundi wa kuchomelea | Not in kaikki or live Wiktionary |
| mpaka rangi | Phrase absent; *mpaka* hits border/until |
| fundi rangi, fundi wa chuma, fundi seremala, fundi wa stima | Phrases absent |
| stima | Electricity sense only listed as a variant of *stimu* |
| mama fua | Cleaning vs laundry sense |
| uwasilishaji | Submission sense, not parcel delivery |
| mfanyikazi | Variant spelling |
| mtambuzaji, mchoraji | Rejected: confirm the reasons with a second source |

## 7. Shortlist proposal (not final)

Criteria: clean ESCO mapping, at least one trade_name alias, essential skills distinct from but
overlapping with neighbouring areas. Evidence-backed = pending trade_name with `found_exact` or
`found_components`. Overlap = essential-skill Jaccard against the other proposed areas (using
the preferred-label match where one exists, otherwise all exact matches).

**Proposed 10:**

| # | Area | ESCO mapping | Trade names with evidence | Held-out candidate | Notes |
|---|---|---|---|---|---|
| 1 | Electrician | ambiguous: one preferred match (7411.1) | 2 | **fundi wa stima** (keep fundi wa umeme in KG) | Normalisation does not merge umeme/stima, so no leak. Overlaps mason (J 0.08) |
| 2 | Plumber | ambiguous: one preferred match (7126.8) | 1 | — | Overlaps mason (J 0.30) |
| 3 | Carpenter | clean (7115.1) | 2 | **fundi seremala** (keep fundi wa mbao in KG) | Overlaps mason (J 0.36) |
| 4 | Mason / bricklayer | clean (7112.1) | 1 | — | Hub of the construction cluster |
| 7 | Motor-vehicle mechanic | ambiguous: alt-only (7231.10) | 1 | — | Take 7 *or* 8, not both (same ESCO occupation). Small overlap with 10 and 12 |
| 10 | Mobile-phone repairer | ambiguous: alt-only (7422.3.1), label clearly right | 1 | — | Overlaps 1, 7, 12, 15 slightly |
| 11 | Tailor / dressmaker | ambiguous: two preferred matches | 1 | — | Overlaps laundry (J 0.07). Map to one or both? |
| 12 | Hairdresser / barber | ambiguous: two preferred matches | 1 | — | Overlaps 6 areas slightly. kinyozi fits barber more than hairdresser |
| 15 | Laundry worker | ambiguous: one preferred match (8157.1) | 1 | — | mama fua also has a cleaning sense |
| 16 | Cook / catering worker | ambiguous: one preferred match (5120.1) | 1 | — | Weak overlap: 0 shared skills with the other nine, 1 with domestic cleaner |

**Options for slots 11–12** (each misses one criterion):

| # | Area | What it lacks | What it adds |
|---|---|---|---|
| 14 | Domestic cleaner | No trade_name alias (only descriptive) | Clean ESCO; overlaps 7 proposed areas, and gives cook a neighbour |
| 17 | Gardener | No skill overlap with any area; ESCO needs a choice | Strong evidence (mtunza bustani is a headword) |
| 18 | Driver | No skill overlap; the single alt match (hearse driver) is wrong | dereva is a strong headword |
| 6 | Welder | Only trade name (fundi wa chuma) is UNVERIFIED; kuchomelea not found | Overlaps 6 proposed areas |

Excluded: 5, 13, 19, 20 (no ESCO match), 9 (no trade_name), 8 (duplicates 7).

**Risk for the core experiment:** only areas 1 and 3 qualify for a held-out term, which gives
two held-out aliases in total. The sprint plan's S2-4 target (≥5 terms per area, ≥50 in total)
is far off at 36 pending rows. The unlisted dictionary candidates in §5 (e.g. makanika,
mshonaji, msusi, dobi, mpikaji, mwendeshaji) would add second trade names to areas 7, 11, 12,
15, 16 and 18 if you decide to add them.

## 8. Normalisation, loader and tests

`kaziforce_kg.vocabulary.normalize_alias()`:

- **Basic cleaning:** NFKC, casefold, trim, collapse whitespace.
- **Punctuation:** removed; apostrophes are deleted rather than turned into spaces
  (ng'ombe → ngombe).
- **Equivalences:** drops the optional "wa" and maps mafundi→fundi, stimu→stima and
  mfanyikazi→mfanyakazi, on whole tokens only.
- **Synonyms are not merged** (fundi wa umeme ≠ fundi wa stima).

`load_kg_vocabulary()` returns only `status=accepted` and `kg_included=yes` rows. It raises if a
`kg_included=no` alias normalises to an included one. It currently returns nothing, because
nothing is accepted.

`tests/test_vocabulary.py` (29 tests) covers:

- **Normalisation:** positive and negative cases.
- **Loader:** the accepted-and-included filter; held-out aliases never appear in its output;
  an equivalence leak is rejected.
- **Data integrity:** enumerated values; accepted rows must name a validator; rejected rows
  keep a reason; gloss notes are at most five words; no duplicate aliases within an area; area
  IDs and ESCO URIs are consistent with `area_esco_map.csv`; no alias maps to two occupations
  unless its areas are `multiple`; no `kg_included=no`/`yes` equivalence.

Full suite: 40 passed; ruff clean. The tests read only committed files, so CI does not need the
raw data.

## 9. Open issues

1. **ESCO choices** for every area marked several or alt-only (`selected` column), especially
   Driver (hearse driver is wrong) and 7 vs 8.
2. **Shortlist approval** (§7), and whether to add the unlisted dictionary candidates.
3. **Held-out terms:** confirm fundi wa stima and fundi seremala, or choose others; then set
   `kg_included`.
4. **Areas for mtambuzaji and msuluhishi.**
5. **Intended forms** for `vifaa vya kielektroniki`, `utoaji` and `matengenezo ya jumla`, and
   the register of `courier`.
6. **mama fua:** laundry only, or also domestic cleaner (which would make it ambiguous)?
7. **Schema mismatch with S2-4:** the sprint plan names a single "register (Swahili/Sheng/English)"
   column; aliases.csv separates `language` and `register` and has no Sheng value. Update the
   sprint plan or add `sheng`.
8. **Manual second-source checks** (§6), then the S2-5 validation log and `vocab-v1` tag.
9. **Synthetic generator not touched**, as instructed. It still uses `fundi wa mabomba` and `house
   cleaner`, which are no longer in the table, and must be regenerated from the frozen
   vocabulary (S2-6).

## 10. Reproduce

    python scripts/map_vocabulary_areas.py --print-summary   # needs data/raw/esco/
    python scripts/check_vocabulary_dictionary.py --occupations  # needs data/raw/kaikki/
    pytest tests/test_vocabulary.py
