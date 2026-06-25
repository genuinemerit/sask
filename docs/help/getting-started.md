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
stars, and any near-term celestial events. For example, fetching the sky
scene for the story's "now" pulse looks like this in a Python REPL:

```python
from sask.config_loader import load_config
from sask.calendar.scene import get_sky_scene
from pathlib import Path

cfg = load_config(Path("config"))
scene = get_sky_scene(cfg.timeline.story_now_pulse, cfg)
```

See the **Ephemeris** page to generate a time-series of sky scenes over a
date range instead of a single moment.
