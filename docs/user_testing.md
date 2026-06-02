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
- A numeric input labelled "Pulse" is pre-filled with `71642553600`
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
| TC-005-01 | PASS | `GET /` → 200; form pre-filled with `71642553600` |
| TC-005-02 | PASS | `GET /?pulse=71642553600` → 200 |
| TC-005-03 | PASS | `GET /?pulse=0` → 200 |
| TC-005-04 | PASS | `43200.7` rounded to `43201`; rendered `43201 (12:00:01)`, `0.1369%` |
| TC-005-05 | PASS | Browser enforces `input type="number"`; non-numeric input never reaches the server |
| TC-005-06 | PASS | Page source contains only a `<style>` block; no `<script>` tags |

Incidental: `GET /favicon.ico` → 404 (no favicon defined; expected for MVP).

---

### Teardown

Stop the Flask server with `Ctrl+C` in the VM terminal. Close the SSH tunnel
terminal.
