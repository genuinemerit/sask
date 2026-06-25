# Getting started

Every page in sask is driven by a **pulse**: an integer count of seconds
since the Astro epoch (Astro day 1, midnight). Enter a pulse, an Astro
day, or a date in one of the two civil calendars (Fatunik or Terpin), and
the other forms fill in automatically.

## Looking up a date

1. Open the **Pulse** page (the site's home page).
2. Enter a value in any of the four input fields.
3. Click **Query**.

The result table shows the Astro day, time of day, and orbital position
for that pulse:

| Field | Meaning |
| --- | --- |
| Astro Day | Day number since the Astro epoch |
| Day Pulse Offset | Seconds elapsed since local midnight |
| Orbital Position | Percent of the way through the current AstroYear |

## Looking up the sky

The **Sky** page composes a full sky scene for a given date: which moons
and planets are above the horizon, the current season, visible fixed
stars, and any near-term celestial events. Querying it for the story's
current pulse (`104548096103`, the default pre-filled value) produces a
night summary like this:

```text
A night of stillness: deep winter, the sky long and cold. Moons above the
horizon: Endor (Pale gray-blue, first quarter) W mid; Sella (Ashy bronze,
waxing gibbous) S high; Lelako (Bright ivory, first quarter) W mid; Jembor
(Rust-brown, full) SE high; Calumbra (Silvery-gray, waxing gibbous) S high;
Zehembra (Gold-hued white, full) SE mid; Shunna (Ice-blue shimmer, first
quarter) W mid; Kanka (Deep violet-brown, full) SE mid. Wanderers visible:
Dramond (Warm amber, hazy rim) S high. The active House of the Equinox is
The Winged Pollinator. 7 fixed stars are visible, including Ilyrun, Kresh,
Marnok and 4 others. This day, 3 moons are near-full together: Jembor,
Zehembra, Kanka. Next night of co-fullness: 1 day away.
```

Every sentence in that summary comes from a real field on the page: the
season, the per-moon phase/color/direction table, the active House, the
fixed-star count, and the co-fullness tracker are all visible above this
summary when you load the page yourself.

See the **Ephemeris** page to generate a time-series of sky scenes over a
date range instead of a single moment.
