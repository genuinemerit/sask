# SPEC-006 Test Results — Frozen orbital initial conditions

**Date:** 2026-06-04
**Status:** PASS

## Test run

```
26 passed in 0.06s
```

All 26 tests pass. Full pre-commit check exits 0.

## Smoke test

Generator run:

```
python3 tools/generate_orbital_conditions.py
Wrote /home/dave/Code/sask-calendar/config/body_data.toml
Seed: 20260604   Bodies: 15

  Endor         offset=0.477754  incl=1.2237°  node=0.013445
  Sella         offset=0.309749  incl=4.4826°  node=0.795970
  Lelako        offset=0.985128  incl=3.2139°  node=0.924525
  Jembor        offset=0.842820  incl=5.4023°  node=0.097357
  Calumbra      offset=0.356108  incl=4.2190°  node=0.538474
  Zehembra      offset=0.823134  incl=1.0000°  node=0.327352
  Shunna        offset=0.190426  incl=2.6303°  node=0.539500
  Kanka         offset=0.522829  incl=6.0173°  node=0.499210
  Aesthra       offset=0.070082  incl=1.7519°  node=0.359105
  Lethra        offset=0.570082  incl=4.7006°  node=0.520275
  Beyarus       offset=0.561749  incl=4.5128°  node=0.191893
  Dramond       offset=0.387337  incl=7.1655°  node=0.472372
  Thurnak       offset=0.663537  incl=4.9823°  node=0.232992
  Zelven        offset=0.792613  incl=7.8856°  node=0.811569
  Kreetha       offset=0.705577  incl=5.2907°  node=0.239690
```

Overrides confirmed:

- Lethra offset (0.570082) = Aesthra offset (0.070082) + 0.5 ✓
- Zehembra inclination = 1.0000° ✓
- Dramond sidereal_period_days = 500 ✓

## Acceptance checklist

- [x] Three config files exist and are internally consistent; template covers every field
- [x] All eight moons and seven planets are complete, validated records
- [x] body_data.toml is reproducible from the recorded seed (20260604)
- [x] Lore overrides hold: Lethra = Aesthra + 0.5, Zehembra inclination low, Dramond 500 days
- [x] observation_data.toml carries obliquity 23.44 and observer latitude 35.47 N
- [x] Generator is a one-time tool; engine reads frozen config and never re-randomises
