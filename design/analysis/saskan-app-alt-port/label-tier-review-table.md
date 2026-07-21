# LABEL-Tier Translation — Review Table (SPEC-036)

Every distinct LABEL-tier string across all 8 templates + translator.py's
lookup tables, deduplicated where the same word means the same thing in
multiple places (e.g. "Moon" table header used in both moons.html and
sky.html gets one tag, used twice). Edit the "Proposed es-ES" column as you
see fit and return it; I'll adopt your edits verbatim, same as the
proper-noun table.

Tag prefix key: `label.*` (buttons/fields/misc), `title.*` (page/section
titles), `th.*` (table headers), `phase.*` (moon-phase names),
`compass.*` (16-point compass), `misc.*` (short standalone phrases).

## Page titles / headings

| Tag | en-US | Proposed es-ES |
|---|---|---|
| title.pulse_page | Saskan Calendar — Pulse Lookup | Calendario Saskan — Consulta de pulso |
| title.moons_page_short | Saskan Calendar — Moons | Calendario Saskan — Lunas |
| title.moons_page_h1 | Saskan Calendar — Moons Sky View | Calendario Saskan — Vista del cielo: Lunas |
| title.planets_page_short | Saskan Calendar — Planets | Calendario Saskan — Planetas |
| title.planets_page_h1 | Saskan Calendar — Planets Sky View | Calendario Saskan — Vista del cielo: Planetas |
| title.sky_page_short | Sky — Saskan Calendar | Cielo — Calendario Saskan |
| title.sky_page_h1 | Sky for a Date | Cielo para una fecha |
| title.ephemeris_page_short | Ephemeris — Saskan Calendar | Efemérides — Calendario Saskan |
| title.ephemeris_page_h1 | Ephemeris Generator | Generador de efemérides |
| title.help_index_short | Saskan Calendar — Help | Calendario Saskan — Ayuda |
| title.help_index_h1 | Help | Ayuda |
| title.help_topic_short | Saskan Calendar — Help: {topic} | Calendario Saskan — Ayuda: {topic} |
| title.help_topic_not_found | Help topic not found | Tema de ayuda no encontrado |

## Form fieldset legends

| Tag | en-US | Proposed es-ES |
|---|---|---|
| label.legend.enter_pulse | Enter pulse | Introducir pulso |
| label.legend.or_astro_day | Or Astro day | O día Astro |
| label.legend.or_fatunik_date | Or Fatunik date | O fecha Fatunik |
| label.legend.or_terpin_date | Or Terpin date | O fecha Terpin |
| label.legend.pulse_start_end | Pulse (explicit start and end) | Pulso (inicio y fin explícitos) |
| label.legend.astro_day_range | Astro Day (start; end set by Duration) | Día Astro (inicio; el fin lo fija la duración) |
| label.legend.fatunik_range | Fatunik Date (start; end set by Duration) | Fecha Fatunik (inicio; el fin lo fija la duración) |
| label.legend.terpin_range | Terpin Date (start; end set by Duration) | Fecha Terpin (inicio; el fin lo fija la duración) |
| label.legend.step_profile | Step and profile | Paso y perfil |

## Field labels

| Tag | en-US | Proposed es-ES |
|---|---|---|
| label.field.pulse | Pulse | Pulso |
| label.field.astro_day | Astro Day | Día Astro |
| label.field.year | Year | Año |
| label.field.month | Month | Mes |
| label.field.day | Day | Día |
| label.field.start | Start | Inicio |
| label.field.end | End | Fin |
| label.field.step_minutes | Step (Astro minutes) | Paso (minutos Astro) |
| label.field.duration_days | Duration (Days) | Duración (días) |
| label.field.profile | Profile | Perfil |
| label.field.duration_hint | ignored when Pulse start and end are used | se ignora cuando se usan inicio y fin de Pulso |

## Buttons / links / select options

| Tag | en-US | Proposed es-ES |
|---|---|---|
| label.button.query | Query | Consultar |
| label.button.generate | Generate | Generar |
| label.button.reset | Reset | Restablecer |
| label.option.scribal | Scribal | Escribano |
| label.option.kinematic | Kinematic | Cinemático |
| label.option.both | Both | Ambos |
| label.link.back_to_help | Back to Help | Volver a ayuda |
| label.link.download_scribal | Download scribal JSON | Descargar JSON de escribano |
| label.link.download_kinematic | Download kinematic JSON | Descargar JSON cinemático |

## Table headers (deduplicated across moons/planets/sky)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| th.moon | Moon | Luna |
| th.planet | Planet | Planeta |
| th.phase | Phase | Fase |
| th.lit | Lit | Iluminación |
| th.albedo | Albedo | Albedo |
| th.visible | Visible | Visible |
| th.eclipse | Eclipse | Eclipse |
| th.altitude | Altitude | Altitud |
| th.azimuth | Azimuth | Azimut |
| th.rise | Rise | Salida |
| th.transit | Transit | Tránsito |
| th.set | Set | Puesta |
| th.notes | Notes | Notas |
| th.color | Color | Color |
| th.brightness | Brightness | Brillo |
| th.calendar | Calendar | Calendario |
| th.long_count | Long Count | Cuenta larga |
| th.short_count | Short Count | Cuenta corta |
| th.turn | Turn | Turno |
| th.lunation | Lunation | Lunación |
| th.direction | Direction | Dirección |
| th.body | Body | Cuerpo |
| th.type | Type | Tipo |
| th.visibility | Visibility | Visibilidad |
| th.star | Star | Estrella |
| th.position | Position | Posición |

## Section headings (sky.html)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| misc.lore_overlay | Lore Overlay | Superposición de tradición local |
| misc.lunar_calendars | Lunar Calendars | Calendarios lunares |
| misc.display_only | (display-only) | (solo visualización) |
| misc.moons_above_horizon | Moons Above the Horizon | Lunas sobre el horizonte |
| misc.no_moons_above | No moons above the horizon at this time. | No hay lunas sobre el horizonte en este momento. |
| misc.co_fullness | Co-fullness | Coplenitud |
| misc.this_day | This day: | Este día: |
| misc.next_event | Next event: | Próximo evento: |
| misc.no_cofullness_event | No co-fullness event this day. | No hay evento de coplenitud este día. |
| misc.below_horizon_all_day | (below the horizon throughout this day) | (bajo el horizonte durante todo este día) |
| misc.wanderers_above_horizon | Wanderers Above the Horizon | Errantes sobre el horizonte |
| misc.no_wanderers_above | No wanderers above the horizon at this time. | No hay errantes sobre el horizonte en este momento. |
| misc.comets_and_spark | Comets &amp; the Spark | Cometas y la Chispa |
| misc.season | Season | Estación |
| misc.fixed_stars_houses | Fixed Stars &amp; Houses of the Equinox | Estrellas fijas y casas del equinoccio |
| misc.active_house | Active house: | Casa activa: |
| misc.circumpolar | Circumpolar: | Circumpolar: |
| misc.no_fixed_stars | No fixed stars visible this season. | No hay estrellas fijas visibles esta estación. |
| misc.night_summary | Night Summary | Resumen nocturno |
| misc.image_prompt | Image Prompt | Instrucción de imagen |
| misc.fatunik_time | Fatunik time | Hora Fatunik |
| misc.terpin_time | Terpin time | Hora Terpin |
| misc.fatunik_solar | Fatunik Solar | Solar Fatunik |
| misc.terpin_solar | Terpin Solar | Solar Terpin |

## Planets "Through a glass" detail row

| Tag | en-US | Proposed es-ES |
|---|---|---|
| misc.through_a_glass | Through a glass: | A través de un catalejo: |
| misc.rings_colon | Rings: | Anillos: |
| misc.moons_visible_suffix | moon(s) visible. | luna(s) visible(s). |
| misc.plain_disc | Appears as a plain disc; no notable features. | Aparece como un disco liso; sin rasgos notables. |
| misc.not_currently_visible | Not currently visible. | No visible actualmente. |
| misc.notes_colon | Notes: | Notas: |

## Ephemeris page specifics

| Tag | en-US | Proposed es-ES |
|---|---|---|
| misc.scribal_preview | Scribal preview | Vista previa de escribano |
| misc.kinematic_preview | Kinematic preview | Vista previa cinemática |
| misc.preview_prefix | Preview: first 5 steps of {n} total | Vista previa: primeros 5 pasos de {n} en total |

## Moon-phase names (translator.py `_phase_name`)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| phase.new | New | Nueva |
| phase.waxing_crescent | Waxing Crescent | Creciente |
| phase.first_quarter | First Quarter | Cuarto creciente |
| phase.waxing_gibbous | Waxing Gibbous | Gibosa creciente |
| phase.full | Full | Llena |
| phase.waning_gibbous | Waning Gibbous | Gibosa menguante |
| phase.last_quarter | Last Quarter | Cuarto menguante |
| phase.waning_crescent | Waning Crescent | Menguante |

## Compass points (translator.py `_CARDINAL`, 16-point)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| compass.n | N | N |
| compass.nne | NNE | NNE |
| compass.ne | NE | NE |
| compass.ene | ENE | ENE |
| compass.e | E | E |
| compass.ese | ESE | ESE |
| compass.se | SE | SE |
| compass.sse | SSE | SSE |
| compass.s | S | S |
| compass.ssw | SSW | SSO |
| compass.sw | SW | SO |
| compass.wsw | WSW | OSO |
| compass.w | W | O |
| compass.wnw | WNW | ONO |
| compass.nw | NW | NO |
| compass.nnw | NNW | NNO |

## Brightness bands (sky.html inline, two places)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| brightness.brilliant | Brilliant | Brillante |
| brightness.bright | Bright | Luminoso |
| brightness.moderate | Moderate | Moderado |
| brightness.faint | Faint | Tenue |
| brightness.dim | Dim | Débil |

## Yes/No (moons/planets visibility column)

| Tag | en-US | Proposed es-ES |
|---|---|---|
| misc.yes | Yes | Sí |
| misc.no | No | No |
