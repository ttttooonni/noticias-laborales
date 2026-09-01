# Noticias Laborales — PWA estática

Motor de noticias para GitHub Pages, con redacción editorial que **no se pierde** en cada pasada horaria.

## Qué hay ahora

1. **Identidad por URL canónica**, no por slug a mano. El BOE usa `BOE-A-YYYY-N`.
2. **`data/editorial.json`** guarda a quién afecta / qué significa / posición UGT / `pin`. El RSS no lo pisa.
3. **Ítems pineados** (sentencias, logros de UGT) no caducan a los 14 días.
4. **Service worker versionado**: `stamp_sw.py` cambia el nombre de caché cuando cambia el HTML/JS/CSS, y en `activate` se borran las cachés viejas.
5. **Última hora** es las últimas 24 h, no una categoría vacía.
6. **UGT Canarias** entra por su RSS Joomla (`?format=feed&type=rss`). UGT estatal se intenta descubrir desde el HTML.
7. **Clasificación** sin la trampa de «turismo» (nombre de la consejería). Hostelería solo con palabras del sector. Las Palmas es filtro propio.

## Fuentes automatizadas

- BOE — convenios colectivos, Trabajo y empleo, Seguridad Social.
- BOC — otras resoluciones (solo si el texto es laboral de verdad).
- Gobierno de Canarias — Turismo y Empleo (filtrado: no pasa cualquier nota de turismo).
- UGT Canarias — RSS oficial.
- UGT — HTML con descubrimiento de feed.

## Criterio

1. Fuente primaria antes que prensa.
2. Deduplicación por URL canónica.
3. Ventana de 14 días, salvo `pin` / `keep_until`.
4. Máximo 250 noticias.
5. El texto editorial no se pisa con el resumen del RSS.
6. La fuente original siempre se conserva; los enlaces tienen que ser `http(s)`.

## GitHub Pages

Settings → Pages → Deploy from branch → `main` → `/ (root)`.

## Automatización

GitHub Actions ejecuta el colector cada hora (`workflow_dispatch` también). El job no cancela un push a medias.

Para enriquecer una noticia: edita `data/editorial.json` con la URL canónica como clave. No toques `noticias.json` a mano.
