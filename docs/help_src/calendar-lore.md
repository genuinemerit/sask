# Calendar lore: how Saskan cultures keep time

{place.saskantinon} doesn't have one calendar — it has six, and none of them agree
with each other. Two are **solar** calendars, kept by the two great
civil cultures ({culture.fatunik} and {culture.terpin}), anchored to the seasons the way our
own calendars are. Four more are **lunar** calendars, each kept by a
smaller culture that counts its years by watching a single moon instead
of the sun. This page is a guide to all six, plus the smaller units of
time — watches, weeks, ages, and the occasional leap — that dress up a
date in each culture's own voice.

[TOC]

## Solar vs. lunar, in plain terms

A **solar** calendar's "month" has nothing to do with the moon — its
year is simply divided into twelve named stretches, with a short extra
"festival" month tucked in to keep the count tidy. Its length is fixed
to the true solar year, the same one that drives the seasons.

A **lunar** calendar's "month" is one real lunar cycle — new moon to new
moon — for whichever moon that culture has adopted as its own
timekeeper. Because every moon in the Saskan sky orbits at its own pace,
each lunar calendar's month (and therefore its year) runs at a different
length, and none of the four lunar calendars line up with each other, or
with the solar year, without periodic correction.

## The two solar calendars

### {culture.fatunik} — {lore.fatunik_solar.era_name}

{culture.fatunik} is the dominant culture's calendar. Its year has twelve named
months of thirty days each ({lore.fatunik_solar.month.n1}, {lore.fatunik_solar.month.n2}, {lore.fatunik_solar.month.n3}, {lore.fatunik_solar.month.n4}, {lore.fatunik_solar.month.n5},
{lore.fatunik_solar.month.n6}, {lore.fatunik_solar.month.n7}, {lore.fatunik_solar.month.n8}, {lore.fatunik_solar.month.n9}, {lore.fatunik_solar.month.n10}, {lore.fatunik_solar.month.n11}, {lore.fatunik_solar.month.n12}), plus a short
intercalary month called **{lore.fatunik_solar.festival_name}** that opens the year. Days fall
into five-day weeks called a **{lore.fatunik_solar.week_word}**, with each day individually named
({lore.fatunik_solar.day.n1}, {lore.fatunik_solar.day.n2}, {lore.fatunik_solar.day.n3}, {lore.fatunik_solar.day.n4}, {lore.fatunik_solar.day.n5}). The {culture.fatunik} day begins at sunrise.

Years aren't just numbered — they're placed within a named **Age**.
Three Ages are recorded so far: {lore.fatunik_solar.age.n1}, {lore.fatunik_solar.age.n2}, and
currently {lore.fatunik_solar.age.n3}. A full {culture.fatunik} date reads like this
(a real date, for the story's present moment):

```text
Velden, the 6th kell of Tarnel, Year 1782 of the Bright Age
```

**Leap rule:** every fourth year, {lore.fatunik_solar.festival_name} grows from five days to six
to keep pace with the true solar year — except on a century year, which
skips the extra day, except again on every fourth century, which
restores it. (Saskan readers will recognize this as the same shape of
rule our own world uses for leap years, just renamed for {lore.fatunik_solar.era_name}.)

### {culture.terpin} — {lore.terpin_solar.era_name}

{culture.terpin} is an older culture (long-lived sentient tortoises) with its own
solar calendar, structured the same way as {culture.fatunik}'s — twelve thirty-day
months ({lore.terpin_solar.month.n1}, {lore.terpin_solar.month.n2}, {lore.terpin_solar.month.n3}, {lore.terpin_solar.month.n4}, {lore.terpin_solar.month.n5}, {lore.terpin_solar.month.n6},
{lore.terpin_solar.month.n7}, {lore.terpin_solar.month.n8}, {lore.terpin_solar.month.n9}, {lore.terpin_solar.month.n10}, {lore.terpin_solar.month.n11}, {lore.terpin_solar.month.n12}) plus an intercalary month
called **{lore.terpin_solar.festival_name}** — but counted differently. Weeks are ten days long,
called a **{lore.terpin_solar.week_word}** ({lore.terpin_solar.day.n1}, {lore.terpin_solar.day.n2}, {lore.terpin_solar.day.n3}, {lore.terpin_solar.day.n4}, {lore.terpin_solar.day.n5}, {lore.terpin_solar.day.n6},
{lore.terpin_solar.day.n7}, {lore.terpin_solar.day.n8}, {lore.terpin_solar.day.n9}, {lore.terpin_solar.day.n10}), and the day begins at midnight rather than
sunrise. {culture.terpin} also reckons its years by Age ({lore.terpin_solar.age.n1}, {lore.terpin_solar.age.n2},
and currently {lore.terpin_solar.age.n3}). A real {culture.terpin} date for the
same moment as above:

```text
Bessen, the 1st deshan of Omarra, Year 2271 of the Deepening
```

**Leap rule:** instead of a one-day adjustment every few years, {culture.terpin}
makes one big correction at long intervals. Every 132nd year, {lore.terpin_solar.festival_name}
swells from five days to thirty-seven — a **Long Year** — and {culture.terpin}s
call that whole 132-year span a **Shell**. Once every 4620 years (35
Shells), the correction is a touch smaller (thirty-six days instead of
thirty-seven — a **Super-Long Year**) rather than the usual Long Year. A
{culture.terpin} date is often cited together with its Shell, e.g. "Shell 7, Turn
47."

## The four lunar calendars

Beyond the two solar cultures, four more peoples — mostly smaller,
animal-totem "sint" cultures — keep their own calendars by a single
moon. Each has adopted a different moon as central to its own count, and
the four don't structurally agree with each other, let alone with the
solar calendars:

- **Untamed** and **Warren** reckon in cycles that reset: a long **Round**
  (called a {lore.untamed.round_word} for Untamed, a {lore.warren.round_word} for Warren)
  that periodically starts over to stay roughly aligned with the true year, with a turn
  number counted within the current Round.
- **Hearth** keeps no years, turns, or months at all — just an
  ever-rising count of how many times its moon has completed a full
  cycle since the count began.
- **Terpin Lunar** is the odd one out: rather than resetting, it shares
  {culture.terpin}'s own continuous, Age-based year count — the same Ages as
  {culture.terpin}'s solar calendar above.

> One interpretive note: each lunar calendar's "week" config gives its
> moon a slightly different name from the one used everywhere else in
> the app ({body.sella}/"{lore.untamed.moon_word}", {body.shunna}/"{lore.warren.moon_word}", {body.jembor}/"{lore.hearth.moon_word}"). The
> per-moon lore notes in the body config support these as deliberate
> cultural nicknames — {body.sella} is noted as "sacred to rabbits," {body.jembor} as
> "linked to solar omens and lore of fate," consistent with each
> culture's own name for its moon — but this page is treating that as
> an inference, not a confirmed design fact. Flag it if that's wrong.

### {calendar.untamed_name}

Kept by the Untamed — a rabbit-wolf-sint alliance — around the moon
**{body.sella}** ("{lore.untamed.moon_word}" in their own speech, the newest of the lunar
calendars and the brightest moon in the sky). A year ("{lore.untamed.turn_word}") is twelve
of {body.sella}'s cycles, with months named {lore.untamed.month.n1}, {lore.untamed.month.n2}, {lore.untamed.month.n3}, {lore.untamed.month.n4}, {lore.untamed.month.n5},
{lore.untamed.month.n6}, {lore.untamed.month.n7}, {lore.untamed.month.n8}, {lore.untamed.month.n9}, {lore.untamed.month.n10}, {lore.untamed.month.n11}, {lore.untamed.month.n12}. There's no fixed week;
instead each day falls into one of four named lunar phases ({lore.untamed.quarter.n1},
{lore.untamed.quarter.n2}, {lore.untamed.quarter.n3}, {lore.untamed.quarter.n4}). A real Untamed date for the same
moment as above:

```text
the Rising, day 14 of Threx, Range 49 of the Reave 19
```

### {calendar.warren_name}

Kept by the Rabbit-sints around the moon **{body.shunna}** ("{lore.warren.moon_word}", a brisk,
fertile moon whose 21-month year runs close enough to a solar year that
it drifts only slowly). Months: {lore.warren.month.n1}, {lore.warren.month.n2}, {lore.warren.month.n3}, {lore.warren.month.n4}, {lore.warren.month.n5}, {lore.warren.month.n6},
{lore.warren.month.n7}, {lore.warren.month.n8}, {lore.warren.month.n9}, {lore.warren.month.n10}, {lore.warren.month.n11}, {lore.warren.month.n12}, {lore.warren.month.n13}, {lore.warren.month.n14}, {lore.warren.month.n15}, {lore.warren.month.n16},
{lore.warren.month.n17}, {lore.warren.month.n18}, {lore.warren.month.n19}, {lore.warren.month.n20}, {lore.warren.month.n21} — twenty-one in all, a year ("{lore.warren.turn_word}")
longer than any other calendar's. Phases: {lore.warren.quarter.n1}, {lore.warren.quarter.n2},
{lore.warren.quarter.n3}, {lore.warren.quarter.n4}. A real Warren date for the same moment as above:

```text
the Dark, day 4 of Hopsel, Litter 24 of the Wend 18
```

### {calendar.hearth_name}

Kept by the Dog-sints around the moon **{body.jembor}** ("{lore.hearth.moon_word}," linked in
their lore to omens and fate). The simplest calendar of all: no months,
no turns, no Age, not even a week — just which of three visible phases
the moon is in ({lore.hearth.phase.n1}, {lore.hearth.phase.n2}, {lore.hearth.phase.n3}) and an ever-rising count of how
many times {lore.hearth.moon_word} has completed a full "turning." A real Hearth date
for the same moment as above:

```text
the full, the 29th day of Old Jem's 10204th turning
```

### {calendar.terpin_lunar_name}

Kept by the {culture.terpin} culture alongside their solar calendar, but tracking
an imaginary moon they call **{lore.terpin_lunar.moon_word}** — the mathematical average of all eight real
moons' cycles, "an idealized moon belonging to none." Twelve months
({lore.terpin_lunar.month.n1}, {lore.terpin_lunar.month.n2}, {lore.terpin_lunar.month.n3}, {lore.terpin_lunar.month.n4}, {lore.terpin_lunar.month.n5}, {lore.terpin_lunar.month.n6}, {lore.terpin_lunar.month.n7}, {lore.terpin_lunar.month.n8}, {lore.terpin_lunar.month.n9},
{lore.terpin_lunar.month.n10}, {lore.terpin_lunar.month.n11}, {lore.terpin_lunar.month.n12}), four computed quarters ({lore.terpin_lunar.quarter.n1} through {lore.terpin_lunar.quarter.n4} —
computed rather than observed, since no real moon moves this
way), and — uniquely among the lunar calendars — the same continuous
Age-based year count as {culture.terpin}'s solar calendar. A real Terpin Lunar
date for the same moment as above:

```text
Fourth Quarter, day 28 of Praal, Year 2176 of the Deepening
```

## Telling time within a day

Below the day, Saskan lore divides time into progressively finer units:
a **watch** (six per day, about four hours each), a **{lore.time.unit.shur}** (twelve per
day, about two hours), a **{lore.time.unit.satava}** (a finer scholarly/ritual unit, sixty
per day), a **{lore.time.unit.keyt}** (ten per shur, about twelve minutes), and a
**{lore.time.unit.wayt}** (a quarter-keyt, the finest named unit). Watches are named
rather than numbered ({lore.time.watch.n1} Watch through {lore.time.watch.n6} Watch), and the
displayed format strings the three most commonly used together, e.g.
(both real, for the same moment used throughout this page):

```text
Fatunik: First Watch . shur 2 : keyt 10
Terpin:  Third Watch . shur 5 : keyt 10
```

The two cultures don't even start their clocks at the same moment:
{culture.fatunik}'s day begins at sunrise, {culture.terpin}'s at midnight — so the same
instant can fall in a different watch for each, exactly as shown above.

## Quick-reference glossary

| Term | Culture | Meaning |
| --- | --- | --- |
| Turn | {culture.fatunik}, {culture.terpin} (both) | A civil year, in any calendar that counts years |
| Age | {culture.fatunik}, {culture.terpin} solar, {culture.terpin} Lunar | A named span of years, used in place of a resetting count |
| {lore.fatunik_solar.week_word} | {culture.fatunik} | A 5-day week |
| {lore.terpin_solar.week_word} | {culture.terpin} (solar) | A 10-day week |
| {lore.fatunik_solar.festival_name} / {lore.terpin_solar.festival_name} | {culture.fatunik} / {culture.terpin} | The short intercalary month that opens the year |
| Shell | {culture.terpin} | A 132-year span, always ending in a Long Year |
| Long Year / Super-Long Year | {culture.terpin} | A year whose festival month is stretched to re-align with the seasons |
| Round | Untamed, Warren (generic term) | A resetting long-cycle for a lunar calendar |
| {lore.untamed.round_word} | Untamed | {calendar.untamed_name}'s name for its Round |
| {lore.warren.round_word} | Warren | {calendar.warren_name}'s name for its Round |
| {lore.untamed.turn_word} | Untamed | {calendar.untamed_name}'s word for a turn (year) |
| {lore.warren.turn_word} | Warren | {calendar.warren_name}'s word for a turn (year) |
| turning | Hearth | One full cycle of Hearth's moon; Hearth has no turns or years, only a rising count of these |
| watch | both cultures | 1/6 of a day, about 4 hours |
| {lore.time.unit.shur} | both cultures | 1/12 of a day, about 2 hours |
| {lore.time.unit.satava} | both cultures | A finer scholarly/ritual unit, 1/60 of a day |
| {lore.time.unit.keyt} | both cultures | 1/10 of a shur, about 12 minutes |
| {lore.time.unit.wayt} | both cultures | 1/4 of a keyt, the finest named unit |
