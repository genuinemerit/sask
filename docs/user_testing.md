# User Acceptance Testing

## SPEC-005 — Flask UI thin vertical slice

### Setup

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open. The tunnel forwards `localhost:5000` on the Ubuntu
host to `localhost:5000` on the VM.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask-calendar
PYTHONPATH=src .venv/bin/flask --app sask.web run
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host and navigate to:**

```text
http://localhost:5000/
```

---

### Test cases

#### TC-005-01 — Landing page loads with no query parameter

**Action:** Navigate to `http://localhost:5000/` with no `?pulse=` parameter.

**Pass criteria:**

- HTTP 200; page title contains "Saskan Calendar — Pulse Lookup".
- A numeric input labelled "Pulse" is pre-filled with `104548096103`
  (the `story_now_pulse` from `config/timeline.toml`).
- No result table is rendered.
- No error message is shown.

---

#### TC-005-02 — Query with pulse = 0 (Astro epoch, midnight)

**Action:** Enter `0` in the Pulse field and click **Query**, or navigate to
`http://localhost:5000/?pulse=0`.

**Pass criteria:**

| Field | Expected value |
|---|---|
| Pulse | 0 |
| Astro Day | 1 |
| Day Pulse Offset | 0 (00:00:00 Astro time) |
| Orbital Position | 0.0000% of AstroYear |

---

#### TC-005-03 — Query with pulse = 43200 (Day 1, noon)

**Action:** Enter `43200` and click **Query**.

**Pass criteria:**

| Field | Expected value |
|---|---|
| Pulse | 43200 |
| Astro Day | 1 |
| Day Pulse Offset | 43200 (12:00:00 Astro time) |
| Orbital Position | 0.1369% of AstroYear |

---

#### TC-005-04 — Float pulse is rounded to nearest integer

**Action:** Enter `43200.7` and click **Query**.

**Pass criteria:**

- No error is shown.
- Pulse field displays `43201`.
- Day Pulse Offset displays `43201` (12:00:01 Astro time).

---

#### TC-005-05 — Non-numeric input yields a user-visible error

**Action:** Enter `abc` in the Pulse field and click **Query**.

**Pass criteria:**

- HTTP 200 (no 500 error page).
- An inline error message appears, e.g. *"Invalid pulse value: 'abc'"*.
- No result table is rendered.

---

#### TC-005-06 — Page source contains no JavaScript

**Action:** With any valid result rendered, view the page source
(Ctrl+U or browser DevTools → Sources).

**Pass criteria:**

- No `<script>` tag appears anywhere in the HTML source.
- No `javascript:` URIs appear in any attribute.

---

### Results — 2026-06-02

Tested on `sask-dev` via SSH tunnel. All cases pass.
See: /tests/results/user_tests/SPEC-005_user_test_results.odt for screenshots.

| TC | Result | Notes |
|---|---|---|
| TC-005-01 | PASS | `GET /` → 200; form pre-filled with `104548096103` |
| TC-005-02 | PASS | `GET /?pulse=104548096103` → 200 |
| TC-005-03 | PASS | `GET /?pulse=0` → 200 |
| TC-005-04 | PASS | `43200.7` rounded to `43201`; rendered `43201 (12:00:01)`, `0.1369%` |
| TC-005-05 | PASS | Browser enforces `input type="number"`; non-numeric input never reaches the server |
| TC-005-06 | PASS | Page source contains only a `<style>` block; no `<script>` tags |

Incidental: `GET /favicon.ico` → 404 (no favicon defined; expected for MVP).

---

### Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.

---

## SPEC-003 + SPEC-004 — Calendar conversions and seasonal context

SPEC-003 and SPEC-004 are engine-only; no UI surface exists yet. UAT is
conducted interactively in a Python REPL on the VM.

### REPL setup

**1. SSH into the VM and start a Python session:**

```bash
cd ~/Code/sask-calendar
PYTHONPATH=src .venv/bin/python3
```

**2. Import and configure in the REPL:**

```python
from pathlib import Path
from sask.config_loader import load_config
from sask.message import CalendarDate
from sask.pulse import (
    astro_to_fatunik, fatunik_to_pulse, fatunik_turns_to_pulse_range,
    astro_to_terpin, terpin_to_pulse,
    terpin_shell_of_turn, terpin_turn_within_shell,
)
from sask.season import season_info

cfg = load_config(Path("config"))
SNP = cfg.timeline.story_now_pulse   # 104548096103
```

---

### REPL test cases

#### TC-003-01 — story_now_pulse converts to Fatunik Turn ~1782

**Action:**

```python
astro_to_fatunik(SNP, cfg)
```

**Pass criteria:** Returns `CalendarDate(calendar_id='fatunik', year=1782, month=10, day=29)`.

- Fatunik epoch starts at Astro year 1531 (summer solstice). Astro year 3313
  minus 1531.25 = ~1782 Fatunik turns elapsed.
- Month 10, Day 29 reflects the exact leap-adjusted calendar arithmetic.

---

#### TC-003-02 — story_now_pulse converts to Terpin Year ~2271

**Action:**

```python
astro_to_terpin(SNP, cfg)
```

**Pass criteria:** Returns `CalendarDate(calendar_id='terpin', year=2271, month=2, day=2)`.

- Terpin epoch starts at Astro year 1043 (spring equinox). Astro year 3313
  minus 1043 = ~2270 Terpin turns elapsed; the leap arithmetic resolves to T2271.

---

#### TC-003-03 — Terpin Shell notation for story_now year

**Action:**

```python
terpin_shell_of_turn(2271)
terpin_turn_within_shell(2271)
```

**Pass criteria:**

- `terpin_shell_of_turn(2271)` → `18`
- `terpin_turn_within_shell(2271)` → `27`

The story_now Terpin date is Shell 18, Turn 27 within that Shell (17 completed
Shells × 132 turns = 2244 turns; 2271 − 2244 = 27). These helper functions are
purely arithmetic and are unaffected by the epoch setting.

---

#### TC-003-04 — Fatunik date round-trips correctly

**Action:**

```python
date = CalendarDate("fatunik", 1782, 10, 29)
astro_to_fatunik(fatunik_to_pulse(date, cfg), cfg)
```

**Pass criteria:** Returns the original `date` unchanged:
`CalendarDate(calendar_id='fatunik', year=1782, month=10, day=29)`.

---

#### TC-003-05 — Ages helper: Fatunik Turns 1780–1800 span story_now

**Action:**

```python
start, end = fatunik_turns_to_pulse_range(1780, 1800, cfg)
print(start, end)
print(start <= SNP <= end)
```

**Pass criteria:**

- `start` = `104461336800` (sunrise of Fatunik T1780 M1 D1)
- `end` = `105124024799` (last pulse of Fatunik T1800 M13 D30)
- `start <= SNP <= end` prints `True` (story_now is in turn 1782, inside
  the range).

---

#### TC-004-01 — story_now is in Blazing (summer), no near event

**Action:**

```python
info = season_info(SNP, cfg)
print(info.season_id, info.near_event_id)
```

**Pass criteria:**

- `info.season_id` = `'stillness'` (story_now is at the very end of winter,
  orbital position ≈ 0.9999 — the last pulse of the AstroYear before spring)
- `info.near_event_id` = `'spring_equinox'`
- `info.near_event_name` = `'Green Day'` (story_now is within tolerance of
  the equinox: the last night of winter, verging on Green Day)

---

#### TC-004-02 — Astro epoch (pulse 0) is spring equinox, Greening

**Action:**

```python
info = season_info(0, cfg)
print(info.season_id, info.near_event_id, info.near_event_name)
```

**Pass criteria:**

- `info.season_id` = `'greening'`
- `info.near_event_id` = `'spring_equinox'`
- `info.near_event_name` = `'Green Day'`

---

#### TC-004-03 — Summer solstice pulse is near Blaze Day

**Action:**

```python
import math
solstice = math.ceil(0.25 * cfg.time_constants.astro_year_pulses)
info = season_info(solstice, cfg)
print(info.season_id, info.near_event_id, info.near_event_name)
```

**Pass criteria:**

- `info.season_id` = `'blazing'`
- `info.near_event_id` = `'summer_solstice'`
- `info.near_event_name` = `'Blaze Day'`

---

### REPL results — 2026-06-02

Tested on `sask-dev` via Python REPL. All cases pass.

| TC | Result | Notes |
|---|---|---|
| TC-003-01 | PASS | `CalendarDate(calendar_id='fatunik', year=1782, month=10, day=29)` |
| TC-003-02 | PASS | `CalendarDate(calendar_id='terpin', year=2271, month=2, day=2)` |
| TC-003-03 | PASS | `terpin_shell_of_turn(2271)` → `18`; `terpin_turn_within_shell(2271)` → `27` |
| TC-003-04 | PASS | Round-trip returns original date unchanged |
| TC-003-05 | PASS | `start=104461336800`, `end=105124024799`; `start <= SNP <= end` → `True` |
| TC-004-01 | PASS | `season_id='stillness'`, `near_event_id='spring_equinox'`, name `'Green Day'` |
| TC-004-02 | PASS | `season_id='greening'`, `near_event_id='spring_equinox'`, name `'Green Day'` |
| TC-004-03 | PASS | `season_id='blazing'`, `near_event_id='summer_solstice'`, name `'Blaze Day'` |

---

### REPL teardown

Exit the Python REPL with `exit()` or `Ctrl+D`.

---

## SPEC-009 — Web UX: lunar and planetary sky for a given pulse

SPEC-009 adds two new browser pages — **/moons** and **/planets** — to the
existing Flask UI. Each page takes a pulse as input (via pulse number, Astro
day, or Fatunik date) and renders a table of sky data for all eight moons or
all seven planets at that instant: phase, illuminated fraction, visibility,
eclipse status, altitude, azimuth, and rise/transit/set pulses.

### SPEC-009 Setup

The setup is identical to SPEC-005. If the Flask server is already running
from that test, skip to step 3.

**1. Open an SSH tunnel from the Ubuntu host:**

```bash
ssh -L 5000:localhost:5000 sask-dev
```

Keep this terminal open.

**2. In the VM session, start the Flask development server:**

```bash
cd ~/Code/sask-calendar
bash tools/start_web.sh
```

Expected output: `Running on http://127.0.0.1:5000`

**3. Open a browser on the Ubuntu host. The three pages under test are:**

```text
http://localhost:5000/
http://localhost:5000/moons
http://localhost:5000/planets
```

**Reference pulses used in the test cases below:**

| Label | Pulse | Meaning |
|---|---|---|
| Epoch | `0` | Astro epoch; spring equinox; pre-epoch for both civil calendars |
| Story now | `104548096103` | Fatunik T1782 M10 D29; Terpin T2271 M2 D2; Stillness season (verging on Green Day) |

---

### SPEC-009 Test cases

#### TC-009-01 — Navigation bar present on all pages

**Action:** Load each of the three pages (`/`, `/moons`, `/planets`) in turn.

**Pass criteria:**

- Every page renders a navigation bar at the top containing three links:
  **Pulse**, **Moons**, and **Planets**.
- Clicking each link navigates to the correct page.
- The root page (`/`) still shows the Pulse Lookup form and result table
  as in TC-005-01 through TC-005-06 (SPEC-009 is strictly additive).

---

#### TC-009-02 — Moons page loads without a pulse query

**Action:** Navigate to `http://localhost:5000/moons` with no query parameters.

**Pass criteria:**

- HTTP 200; page title contains "Saskan Calendar — Moons".
- Three input sections are rendered: **Enter pulse**, **Or Astro day**,
  and **Or Fatunik date**.
- No moon table is rendered.
- No error message is shown.
- No `<script>` tag appears anywhere in the page source.

---

#### TC-009-03 — Moons at epoch (pulse = 0)

**Action:** Navigate to `http://localhost:5000/moons?pulse=0`.

**Pass criteria:**

- The metadata line above the table shows:
  - Pulse `0`
  - Fatunik **T-1531 M10 D29** (pre-epoch: Fatunik calendar starts at Astro year 1531)
  - Terpin **T-1042 M1 D4** (pre-epoch: Terpin calendar starts at Astro year 1043)
  - Fatune **above** horizon (at pulse 0, Fatune transits the meridian at
    altitude **+54.5°** and azimuth **180.0° S** — it is exactly noon for
    the canonical observer)

- The moons table contains exactly **8 rows**, one per moon, in this order:
  Endor, Sella, Lelako, Jembor, Calumbra, Zehembra, Shunna, Kanka.

- **Endor** at pulse 0 (epoch offset 0.477754):
  - Synodic fraction ≈ 0.478 → phase name **Full** (range 0.47–0.53)
  - Illuminated ≈ **99.5%**
  - No eclipse (latitude not near a node at this pulse)

- **Zehembra** at pulse 0 (epoch offset 0.823134):
  - Synodic fraction ≈ 0.823 → phase name **Waning Crescent**
  - Illuminated ≈ **29.3%**
  - Eclipse column shows **—** (near-node check will rarely fire at an
    arbitrary pulse)

- Every row has non-empty entries for Altitude, Azimuth, Rise, Transit,
  and Set. Bodies below the horizon show negative altitude values with no
  row highlighting; bodies above the horizon show positive values.

- Eclipse column header is present on all rows (value is **—** unless an
  eclipse fires).

---

#### TC-009-04 — Moons at story_now_pulse

**Action:** Navigate to `http://localhost:5000/moons?pulse=104548096103`.

**Pass criteria:**

- Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2.
- All 8 moon rows are present.
- Each row shows a phase name (one of: New, Waxing Crescent, First Quarter,
  Waxing Gibbous, Full, Waning Gibbous, Last Quarter, Waning Crescent).
- Illuminated % is consistent with the phase name (Full ≈ 100%, New ≈ 0%).
- Visibility column shows either "Yes" or "No" with a percentage.
- Altitude values are in the range −90° to +90°; azimuth in 0° to 360° with
  a cardinal direction suffix.
- Rise and Set show pulse integers (or "circumpolar" / "never rises" for
  extreme declinations); Transit always shows a pulse integer.

---

#### TC-009-05 — Eclipse row highlighting

**Action:** Scan both the pulse=0 and story_now_pulse moons pages, or try
several different pulse values until an eclipse fires (Zehembra's low
inclination makes it the most frequent candidate).

**Pass criteria:**

- When a moon's Eclipse column shows **Solar**, that row has a warm yellow
  background.
- When it shows **Lunar**, the row has a light blue background.
- Rows with Eclipse = **—** have a plain white background (or a grey-text
  "below horizon" style if altitude is negative).

---

#### TC-009-06 — Moons — Astro day input

**Action:** On the `/moons` page, enter **1** in the "Or Astro day" field
and click **Query**.

**Pass criteria:**

- The page re-renders with `?astro_day=1` in the URL.
- Results are identical to `?pulse=0` (Astro day 1 corresponds to pulse 0).
- All 8 moons are listed; metadata shows Fatunik Y1 M1 D1.

---

#### TC-009-07 — Moons — Fatunik date input

**Action:** In the "Or Fatunik date" section, enter Year **1782**, Month **10**,
Day **29** and click **Query**.

**Pass criteria:**

- The page re-renders with the three Fatunik parameters in the URL.
- Results match `?pulse=104548096103` (Fatunik T1782 M10 D29 = story_now_pulse).
- Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2.
- All 8 moons are listed.

---

#### TC-009-08 — Planets page loads without a pulse query

**Action:** Navigate to `http://localhost:5000/planets` with no query parameters.

**Pass criteria:**

- HTTP 200; page title contains "Saskan Calendar — Planets".
- Three input sections are rendered (same layout as the moons page).
- No planet table is rendered.
- No `<script>` tag in the page source.

---

#### TC-009-09 — Planets at epoch (pulse = 0)

**Action:** Navigate to `http://localhost:5000/planets?pulse=0`.

**Pass criteria:**

- Metadata line shows Pulse 0, Fatunik Y1 M1 D1, Fatune above horizon.

- The planets table contains exactly **7 rows** in this order:
  Aesthra, Lethra, Beyarus, Dramond, Thurnak, Zelven, Kreetha.

- **Beyarus** Color column shows **Brilliant silver-white**.

- **Kreetha** "Through a glass" column contains ring description text
  (e.g. "Rings: Prominent…") and "1 moon(s)".

- **Zelven** "Through a glass" column shows **4 moon(s)**.

- **Aesthra** and **Lethra** (inner planets, semi-major axis 0.387):
  - Visibility shows "No (0.0%)" — inner planets remain near Fatune's
    glare and are typically invisible in this simplified model.
  - Phase varies between crescent and near-full depending on their
    position in the synodic cycle.

- Outer planets (Dramond, Thurnak, Zelven, Kreetha) show illuminated
  fractions generally above 80%, consistent with their near-full geometry
  when viewed from Gavor.

---

#### TC-009-10 — Planets at story_now_pulse

**Action:** Navigate to `http://localhost:5000/planets?pulse=104548096103`.

**Pass criteria:**

- All 7 planet rows are present.
- Each row shows color, phase name, illuminated %, visibility, altitude,
  azimuth, rise/transit/set pulses, relative brightness, and a "Through a
  glass" column with telescopic notes.
- Notes column shows the body's lore description text (e.g. Thurnak:
  "The red wanderer; noticeably bright at opposition…").
- Metadata shows Fatunik T1782 M10 D29 and Terpin T2271 M2 D2.

---

#### TC-009-11 — Planets — Astro day and Fatunik date inputs

**Action (a):** On `/planets`, enter Astro day **1** and query.

**Pass criteria (a):** Same result as `?pulse=0`; 7 planets shown; Fatunik Y1 M1 D1 in metadata.

**Action (b):** On `/planets`, enter Fatunik year **1**, month **1**, day **1** and query.

**Pass criteria (b):** Same result as (a); metadata confirms Y1 M1 D1.

---

#### TC-009-12 — Invalid pulse input on both pages

**Action:** On `/moons`, type **xyz** in the Pulse field and click **Query**.
Repeat on `/planets`.

**Pass criteria:**

- HTTP 200 (no 500 error page) on both pages.
- An inline error message appears (e.g. *"Invalid pulse value: 'xyz'"*).
- No moon or planet table is rendered.

---

#### TC-009-13 — Page source contains no JavaScript

**Action:** With a valid pulse result rendered on `/moons` and `/planets`,
view the HTML source (Ctrl+U or browser DevTools → Sources) for each page.

**Pass criteria:**

- No `<script>` tag appears anywhere in the source.
- No `javascript:` URI appears in any attribute.
- The only embedded code is the `<style>` block in `<head>`.

---

### SPEC-009 Results — (to be completed after testing)

Tested on `sask-dev` via SSH tunnel.

| TC | Result | Notes |
|---|---|---|
| TC-009-01 | | |
| TC-009-02 | | |
| TC-009-03 | | |
| TC-009-04 | | |
| TC-009-05 | | |
| TC-009-06 | | |
| TC-009-07 | | |
| TC-009-08 | | |
| TC-009-09 | | |
| TC-009-10 | | |
| TC-009-11 | | |
| TC-009-12 | | |
| TC-009-13 | | |

---

### SPEC-009 Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.
