# Primeros pasos

Cada página de sask está guiada por un **pulso**: un recuento de segundos
desde la época Astro (día Astro 1, medianoche). Introduce un pulso, un día
Astro, o una fecha en uno de los dos calendarios civiles (Fatunik o
Terpin), y los demás campos se completan automáticamente.

## Consultar una fecha

1. Abre la página **Pulso** (la página de inicio del sitio).
2. Introduce un valor en cualquiera de los cuatro campos.
3. Haz clic en **Consultar**.

La tabla de resultados muestra el día Astro, la hora del día y la
posición orbital para ese pulso:

| Campo | Significado |
| --- | --- |
| Día Astro | Número de día desde la época Astro |
| Desfase de Pulso del Día | Segundos transcurridos desde la medianoche local |
| Posición Orbital | Porcentaje recorrido del AñoAstro actual |

## Consultar el cielo

La página **Cielo** compone una escena celeste completa para una fecha
dada: qué lunas y planetas están sobre el horizonte, la estación actual,
las estrellas fijas visibles, y cualquier evento celeste próximo. Al
consultarla para el pulso actual de la historia (`104548096103`, el valor
predeterminado), se produce un resumen nocturno como este (el texto de
ejemplo permanece en inglés: la generación del resumen nocturno aún no
está localizada):

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

Cada frase de ese resumen proviene de un campo real de la página: la
estación, la tabla de fase/color/dirección por luna, la Casa activa, el
recuento de estrellas fijas, y el rastreador de coplenitud son todos
visibles arriba de este resumen al cargar la página tú mismo.

Consulta la página **Efemérides** para generar una serie temporal de
escenas celestes a lo largo de un rango de fechas en vez de un solo
momento.
