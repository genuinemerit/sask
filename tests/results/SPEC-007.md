# SPEC-007 Test Results — Body kinematics

**Date:** 2026-06-04
**Status:** PASS

## Test run

```text
42 passed in 0.09s
```

All 42 tests pass. Full pre-commit check exits 0.

## Coverage summary

| Area | Tests |
|---|---|
| Config loading (bodies + gavor) | 3 |
| Sidereal and Gavor fractions | 5 |
| Moon synodic fraction | 3 |
| Planet synodic fraction | 2 |
| Moon illuminated fraction | 3 |
| Planet illuminated fraction (law-of-cosines) | 4 |
| Visibility scalar and threshold | 6 |
| Eclipse predicate (node + syzygy gating) | 6 |
| Zehembra vs high-inclination eclipse rate | 1 |
| Apparent size and brightness | 4 |
| BodyState completeness and ranges | 4 |
| all_body_states (15 bodies, name order) | 2 |
| is_visible consistency | 1 |
| Layer purity (no web-layer import) | 1 |

## Acceptance checklist

- [x] All body state is a deterministic, pure function of pulse and frozen config
- [x] Phase, visibility, and eclipse follow the synodic and latitude geometry in DD-0002
- [x] Eclipses are rare for most moons and more frequent for Zehembra per frozen inclinations
- [x] Outputs are typed message units (BodyState); no calendar or watch terms appear
- [x] Planet illuminated fraction uses law-of-cosines phase angle (correct for inner planets)
- [x] bodies.py has no web-layer import
