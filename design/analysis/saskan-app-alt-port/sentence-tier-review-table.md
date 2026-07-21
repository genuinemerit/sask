# SENTENCE/STATEMENT-Tier Translation — Review Table (SPEC-036)

Same format as the LABEL table: edit the "Proposed es-ES" column, return it,
I'll adopt verbatim. This tier covers validation/error sentences
(`routes.py`), the ephemeris instructional paragraph (STATEMENT tier), a
couple of remaining composed-prose fragments, and the two groups of ordinary
translatable phrases correctly deferred from the LABEL tier: house names and
lunar-calendar names.

**Not included here, deliberately** (per the original SPEC-035 content
inventory, still flagged not fixed): several error paths interpolate a raw
Python exception message (`{exc}`) — e.g. "Invalid Fatunik date: {exc}",
`get_sky_series`'s `ValueError` text. I'm translating the surrounding
sask-authored wrapper text only; the interpolated exception text itself
stays English (a pre-existing, separately-flagged issue, not something to
paper over here).

## Validation / error sentences (`routes.py`)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| error.invalid_pulse_value | Invalid pulse value: {value} — enter a number. | Valor de pulso inválido: {value}; introduce un número. |
| error.invalid_astro_day | Invalid Astro day: {value} — enter an integer. | Día Astro inválido: {value}; introduce un entero. |
| error.invalid_fatunik_date | Invalid Fatunik date: {detail} | Fecha Fatunik inválida: {detail} |
| error.invalid_terpin_date | Invalid Terpin date: {detail} | Fecha Terpin inválida: {detail} |
| error.invalid_prefixed_pulse | Invalid {prefix}pulse {value} — enter a number. | {prefix}pulse inválido: {value}; introduce un número. |
| error.invalid_prefixed_astro_day | Invalid {prefix}astro_day {value} — enter an integer. | {prefix}astro_day inválido: {value}; introduce un entero. |
| error.invalid_prefixed_fatunik_date | Invalid {prefix}Fatunik date: {detail} | Fecha {prefix}Fatunik inválida: {detail} |
| error.invalid_prefixed_terpin_date | Invalid {prefix}Terpin date: {detail} | Fecha {prefix}Terpin inválida: {detail} |
| error.start_time_required | Start time is required. | Se requiere la hora de inicio. |
| error.step_required | Step (Astro minutes) is required. | Se requiere el paso (minutos Astro). |
| error.invalid_step_minutes | Invalid step_minutes {value} — enter an integer. | step_minutes inválido: {value}; introduce un entero. |
| error.end_pulse_required | End pulse is required. | Se requiere el pulso de fin. |
| error.duration_required | Duration (Days) is required. | Se requiere la duración (días). |
| error.duration_min | Duration (Days) must be at least 1. | La duración (días) debe ser al menos 1. |
| error.invalid_duration_days | Invalid duration_days {value} — enter an integer. | duration_days inválido: {value}; introduce un entero. |
| error.step_exceeds_duration | Step ({step_min} min) equals or exceeds the total duration ({span_min} min) — reduce Step or increase Duration (Days). | El paso ({step_min} min) iguala o supera la duración total ({span_min} min); reduce el paso o aumenta la duración (días). |
| error.step_exceeds_range_download | step {steps} pulses equals or exceeds range {span} pulses — no intermediate steps would be generated. | el paso de {steps} pulsos iguala o supera el rango de {span} pulsos; no se generarían pasos intermedios. |
| error.no_help_topic | No help topic named "{topic}". | No existe un tema de ayuda llamado "{topic}". |

## Ephemeris instructional paragraph (STATEMENT tier)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| statement.ephemeris_intro | Enter a **start time** using any one input type below. For Astro Day, Fatunik, or Terpin inputs the range length is set by **Duration (Days)** in the Step &amp; Profile section. Use **Pulse** for a precise start and end. Click **Reset** to clear all fields before switching input type. | Introduce una **hora de inicio** usando cualquiera de los tipos de entrada de abajo. Para las entradas de día Astro, Fatunik o Terpin, la duración del rango la fija la **Duración (días)** en la sección Paso y Perfil. Usa **Pulso** para un inicio y fin precisos. Haz clic en **Restablecer** para borrar todos los campos antes de cambiar de tipo de entrada. |

## Remaining composed-prose fragments (sky.html / moons.html / planets.html)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| sentence.horizon_above | above | sobre |
| sentence.horizon_below | bajo | bajo |
| sentence.horizon_suffix | horizon | el horizonte |
| sentence.near_full_together | near-full together — | casi llenas al mismo tiempo — |
| sentence.co_fullness_moon_singular | moon | luna |
| sentence.co_fullness_moon_plural | moons | lunas |
| sentence.next_event_in | in | en |
| sentence.day_singular | day | día |
| sentence.day_plural | days | días |

## House names (14) — ordinary translatable phrases, not proper nouns

| Tag | en-US | Proposed es-ES |
|---|---|---|
| house.watchers_of_stillness | The Watchers of Stillness | Los Vigilantes de la quietud |
| house.chain_of_four | The Chain of Four | La cadena de los cuatro |
| house.ember_gate | The Ember Gate | La puerta de las brasas |
| house.twin_horns | The Twin Horns | Los cuernos gemelos |
| house.hollow_root | The Hollow Root | La raíz hueca |
| house.lantern_grove | The Lantern Grove | La arboleda del farol |
| house.silver_wheel | The Silver Wheel | La rueda de plata |
| house.burning_mirror | The Burning Mirror | El espejo ardiente |
| house.loom_of_krenna | The Loom of Krenna | El telar de Krena |
| house.broken_staff | The Broken Staff | El bastón roto |
| house.thorned_veil | The Thorned Veil | El velo de espinas |
| house.stone_circle | The Stone Circle | El círculo de piedra |
| house.winged_pollinator | The Winged Pollinator | El polinizador alado |
| house.long_sickle | The Long Sickle | La hoz larga |

## Lunar calendar names (4) — ordinary translatable phrases

| Tag | en-US | Proposed es-ES |
|---|---|---|
| calendar.untamed_name | The Untamed Reckoning | El cómputo salvaje |
| calendar.warren_name | The Warren Count | La cuenta de la madriguera |
| calendar.hearth_name | The Hearth Count | La cuenta del hogar |
| calendar.terpin_lunar_name | The Terpin Lunar Count | La cuenta lunar Terpin |
