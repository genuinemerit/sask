# SPEC-009 Test Results — Web UX: lunar and planetary sky

**Date:** 2026-06-04
**Status:** PASS

## Test run

```text
48 passed in 0.18s
```

All 48 tests pass. Full suite 298/298. Pre-commit exits 0.

## Coverage summary

| Area | Tests |
|---|---|
| HTTP smoke (moons/planets, with and without pulse) | 4 |
| Each moon appears by name in the response | 8 |
| Each planet appears by name in the response | 7 |
| Field presence (phase, %, eclipse, altitude, color, brightness, glass) | 7 |
| Input methods (astro day, Fatunik date) | 4 |
| Error handling (invalid pulse → 200 + error message) | 2 |
| No JavaScript in rendered HTML | 2 |
| Calendar date display (Fatunik, Fatune horizon status) | 3 |
| SPEC-005 additive (root still works, pulse form present) | 2 |
| Navigation links between pages | 2 |
| Layer purity (6 engine modules + translator, no Flask import) | 7 |

## Acceptance checklist

- [x] Entering a pulse renders a complete lunar and planetary sky, end to end
- [x] No JavaScript in output; pages are server-rendered Jinja
- [x] Engine consumed only through SPEC-007/008 message units; no engine logic in the web layer
- [x] New views are additive to SPEC-005; times are in pulses, with Fatunik/Terpin dates shown
- [x] Input form accepts pulse, Astro day, and Fatunik date
- [x] Retrograde status deferred (noted in SPEC-009 `out` section)

## Notes

`BodyConfig` was extended with `apparent_color`, `rings`, `visible_moons`,
`rotation_type`, `rotation_period_days`, and `notes` to support the lore
overlay in the planet and moon views. These are descriptive config fields, not
kinematic engine outputs, so the message-unit seam is preserved.
