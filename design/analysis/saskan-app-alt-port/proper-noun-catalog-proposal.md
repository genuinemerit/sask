# Proper-Noun (Invented-Term) Catalog — Proposal for Review (SPEC-036)

**STOP-AND-REVIEW GATE.** This is a proposal only — nothing here has been
written to `config/i18n/*.toml` yet. Per DD-0022/SPEC-036, respelling is a
human-arbitrated decision; this document proposes, it does not decide.
Default posture (per DD-0022's `invariance_presence_not_absence` and
`proper_noun_respelling` principles): every invented term is **INVARIANT**
(identical spelling in es-ES) unless the source spelling would genuinely
mislead the intended Spanish pronunciation. Most respelling is deliberately
deferred per-term, not resolved up front — so this proposal flags only the
handful of terms with a clear, defensible phonetic-mismatch case, modeled
directly on DD-0022's own worked example (Fatune → Fatún).

## Scope note: lore-calendar vocabulary now included

Per your decision, the `/sky` lore overlay (era/Round/phase calendar dates,
watch/shur/keyt time — `src/sask/calendar/lore.py`) is in scope this round,
extending the tag-substitution mechanism rather than inventing a new one.
This adds ~90 terms beyond the body/star/house/comet catalog that would
otherwise be the whole list. `lore.py`'s `render_lore_date`/`render_lore_time`
currently take no `locale` parameter and read one hardcoded English
`format_full`/`format_str` per calendar — implementation will thread an
explicit `locale` argument (mirroring exactly how `season.py`/`translator.py`
already do this — no ambient global state, engine-purity preserved) and make
the format template itself a locale-specific tag (Spanish word order may
differ from English, not just word-for-word substitution) alongside the
vocabulary-word tags below.

## Proposed tag-naming convention (mechanical, not a review item)

- Bodies (moons/planets): `body.<name>` — e.g. `body.endor`. Matches
  DD-0022's own worked example `body.fatune`.
- The star (sun): `body.fatune`.
- Fixed stars: `star.<name>` — e.g. `star.ilyrun`.
- Comets: `comet.<name>` — e.g. `comet.oloryn`.
- Per-calendar lore vocabulary, namespaced by calendar id: `lore.<calendar_id>.era_name`,
  `lore.<calendar_id>.age.<n>`, `lore.<calendar_id>.festival_name`,
  `lore.<calendar_id>.month.<n>`, `lore.<calendar_id>.day.<n>`,
  `lore.<calendar_id>.turn_word`, `lore.<calendar_id>.round_word`,
  `lore.<calendar_id>.moon_word`, `lore.<calendar_id>.week_word`,
  `lore.<calendar_id>.format_full`.
- Shared watch names (`lore_time.toml`): `lore.time.watch.<n>`.
- Quarter/phase terms (e.g. "the Dark", "First Quarter") are **plain English
  descriptive phrases, not invented vocabulary** — they go through ordinary
  sentence/label translation, not this proper-noun catalog.

---

## 1. Bodies — 8 moons + 7 planets (all proposed INVARIANT)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| body.endor | Endor | Endor |
| body.sella | Sella | Sella |
| body.lelako | Lelako | Lelako |
| body.jembor | Jembor | Jembor |
| body.calumbra | Calumbra | Calumbra |
| body.zehembra | Zehembra | Zehembra |
| body.shunna | Shunna | Shunna |
| body.kanka | Kanka | Kanka |
| body.aesthra | Aesthra | Aesthra |
| body.lethra | Lethra | Lethra |
| body.beyarus | Beyarus | Beyarus |
| body.dramond | Dramond | Dramond |
| body.thurnak | Thurnak | Thurnak |
| body.zelven | Zelven | Zelven |
| body.kreetha | Kreetha | Kreetha |

**Flagged for your read-aloud check:** none in this group meet the
silent-final-e bar Fatune sets, though several carry an English "th" digraph
(Aesthra, Lethra, Thurnak) with no exact Spanish equivalent — not flagged as
misleading (no clear single "intended" sound is asserted for these), but
worth a native-speaker pass if you want to double check.

## 2. The star — 1 term (RESPELLING ALREADY DECIDED by DD-0022 itself)

| Tag | en-US | es-ES |
|---|---|---|
| body.fatune | Fatune | **Fatún** |

This is DD-0022's own worked example (fa-TOON in English via silent final e;
"Fatún" directs the intended two-syllable fa-TUN reading in Spanish). Not a
new proposal — just needs to actually be added to the catalog, since it
isn't there yet.

## 3. Fixed stars — 16 (all proposed INVARIANT)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| star.ilyrun | Ilyrun | Ilyrun |
| star.kresh | Kresh | Kresh |
| star.marnok | Marnok | Marnok |
| star.sethera | Sethera | Sethera |
| star.thalona | Thalona | Thalona |
| star.tursin | Tursin | Tursin |
| star.velkora | Velkora | Velkora |
| star.mirrest | Mirrest | Mirrest |
| star.zomel | Zomel | Zomel |
| star.saurnak | Saurnak | Saurnak |
| star.krenna | Krenna | Krenna |
| star.ethranel | Ethranel | Ethranel |
| star.henmae | Henmae | Henmae |
| star.aghur | Aghur | Aghur |
| star.boreth | Boreth | Boreth |
| star.droven | Droven | Droven |

`star.krenna` is also embedded in the house name "The Loom of Krenna" (an
ordinary translatable phrase, not a catalog entry itself — see §7).

## 4. Comets — 3 (all proposed INVARIANT)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| comet.oloryn | Oloryn | Oloryn |
| comet.sevrith | Sevrith | Sevrith |
| comet.kelvarn | Kelvarn | Kelvarn |

## 5. Lore-calendar vocabulary — proposed, mostly INVARIANT, 4 flagged candidates

### 5a. Fatunik solar (`fatunik_solar`)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.fatunik_solar.era_name | the Reckoning of Fatune | la Cuenta de Fatún *(ordinary translation; embeds body.fatune)* |
| lore.fatunik_solar.turn_word | Year | Año |
| lore.fatunik_solar.age.1 | the Age of Embers | la Era de las Brasas |
| lore.fatunik_solar.age.2 | the Age of the Open Hand | la Era de la Mano Abierta |
| lore.fatunik_solar.age.3 | the Bright Age | la Era Brillante |
| lore.fatunik_solar.festival_name | Gleaming | Gleaming |
| lore.fatunik_solar.week_word | kell | kell |
| lore.fatunik_solar.month.1..12 | Solenne, Maradd, Harvenn, Ombren, Frenna, Vossul, Halveth, Iskren, Tarnel, Verel, Blomwen, Aurech | same, **except month.1 "Solenne" — see flagged candidates** |
| lore.fatunik_solar.day.1..5 | Sune, Aweth, Morrin, Velden, Hesk | same |

### 5b. Terpin solar (`terpin_solar`)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.terpin_solar.era_name | the Long Count of Terpa | el Largo Cómputo de Terpa *(ordinary translation)* |
| lore.terpin_solar.turn_word | Year | Año |
| lore.terpin_solar.age.1 | the First Watching | la Primera Vigilia |
| lore.terpin_solar.age.2 | the Age of Stone | la Era de Piedra |
| lore.terpin_solar.age.3 | the Deepening | el Ahondamiento |
| lore.terpin_solar.festival_name | Brennald | Brennald |
| lore.terpin_solar.week_word | deshan | deshan |
| lore.terpin_solar.month.1..12 | Omarra, Tessith, Belunna, Sorvath, Numael, Hovath, Methsa, Yumber, Korreth, Vannath, Esoph, Tulmarr | same, **except month.11 "Esoph" — see flagged candidates** |
| lore.terpin_solar.day.1..10 | Adda, Bessen, Corwen, Dovan, Emarn, Fells, Gessa, Hurneth, Issal, Lonn | same |

### 5c. Terpin lunar (`terpin_lunar`) — shares era_name/ages/turn_word with terpin_solar

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.terpin_lunar.moon_word | the Mean Moon | la Luna Media *(ordinary translation)* |
| lore.terpin_lunar.month.1..12 | Praal, Suneth, Olreth, Mehven, Corsa, Druin, Lasseth, Ombrul, Tevan, Nurra, Esseth, Volmarr | same |

### 5d. Untamed / Sella (`untamed`)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.untamed.round_word | Reave | **flagged, see below** |
| lore.untamed.turn_word | Range | **flagged, see below** |
| lore.untamed.moon_word | Selha | Selha |
| lore.untamed.month.1..12 | Varro, Dakka, Skell, Brunt, Olvar, Threx, Maug, Sarn, Vekk, Drumm, Hask, Volkar | same |

### 5e. Warren / Shunna (`warren`)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.warren.round_word | Wend | Wend |
| lore.warren.turn_word | Litter | Litter *(ordinary English word used as invented-feeling term; consider whether this should be translated as "Camada" instead — flagging as a judgment call, not a phonetic one)* |
| lore.warren.moon_word | Shunsa | Shunsa |
| lore.warren.month.1..21 | Tum, Fenn, Lilla, Pripp, Sennel, Mossa, Dell, Brackel, Hopsel, Clovel, Nibb, Sprigg, Bramm, Quill, Furze, Loma, Vetch, Sedda, Gorra, Pell, Mirn | same, **except month.15 "Furze" — see flagged candidates** |

### 5f. Hearth / Jembor (`hearth`)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.hearth.moon_word | Old Jem | Viejo Jem *(ordinary translation of "Old" + invariant "Jem")* |

### 5g. Shared time units (`lore_time.toml`)

| Tag | en-US | es-ES (proposed) |
|---|---|---|
| lore.time.watch.1..6 | First, Second, Third, Fourth, Fifth, Sixth | Primero, Segundo, Tercero, Cuarto, Quinto, Sexto *(ordinary translation, not invented)* |

`shur`/`keyt`/`satava`/`wayt` (the lore time-unit words embedded literally in
`format = "{watch} Watch . shur {shur} : keyt {keyt}"`) are invented common
nouns, not proper nouns, but need the same catalog treatment since they're
baked into the format string. Proposed: `lore.time.unit.shur = "shur"`,
`lore.time.unit.keyt = "keyt"` (same for satava/wayt if ever rendered),
**all proposed INVARIANT**.

---

## Flagged candidates — the actual decisions I'm asking you to make

Six terms, by direct analogy to Fatune's own documented reasoning (a source
spelling whose English silent-e/digraph convention would produce a
meaningfully different Spanish reading than intended):

| Term | Where used | English reading | Spanish reading if unchanged | Proposed respelling | Rationale |
|---|---|---|---|---|---|
| **Solenne** | Fatunik month 1 | so-LEN (silent e, 2 syl) | so-LEN-neh (3 syl, final e voiced) | *(needs your ear — maybe "Solén"?)* | Same silent-final-e pattern as Fatune |
| **Esoph** | Terpin solar month 11 | ee-SOF ("ph" = /f/) | Spanish has no "ph" digraph; likely read letter-by-letter or guessed | *(maybe "Esof"?)* | Spanish orthography never uses "ph" |
| **Reave** | Untamed round_word (appears in EVERY Untamed-calendar lore date) | REEV (silent e, 1 syl) | reh-AH-veh (3 syl) | *(needs your ear — maybe "Riv" or "Reiv"?)* | Silent-e + "ea" vowel digraph, high-frequency term |
| **Range** | Untamed turn_word (appears in EVERY Untamed-calendar lore date) | RAYNJ (silent e; soft "g") | Spanish "ge" = harsh /x/ sound — nothing like the intended soft-g | *(needs your ear — maybe "Reinch" or something else entirely?)* | Same "ge"-before-e trap as Fatune's "e"-ending, but arguably worse (wrong consonant sound, not just extra syllable); this is also the highest-frequency term of the six since it's the turn_word |
| **Litter** | Warren turn_word | ordinary English word ("a litter of rabbits" — thematically apt, not really invented vocabulary) | reads fine phonetically either way | *(judgment call, not phonetic — translate to "Camada" or keep as "Litter"?)* | Not a pronunciation issue — a translate-vs-keep-as-flavor-word call |
| **Furze** | Warren month 15 | FURZ (silent e) | FUR-zeh (2 syl) | *(needs your ear — maybe "Furz"?)* | Same silent-final-e pattern as Fatune |

Everything else (~135 terms) is proposed as **invariant** (identical
spelling, both locales) by default, per DD-0022's own stated norm that most
respelling stays deferred and per-term.

## What I need from you before the page builder runs

1. Confirm or override the invariant default for the bulk list (§1–§5, minus
   the six flagged terms) — a blanket "yes, invariant is fine" is enough
   unless something jumps out.
2. Decide each of the six flagged candidates: accept a respelling (yours or
   mine), or explicitly keep invariant.
3. Confirm the tag-naming convention above (or adjust it) — this determines
   catalog structure before I write it into `config/i18n/{en-US,es-ES}.toml`.
