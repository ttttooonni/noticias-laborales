# Noticias Laborales — PWA estática

Motor de noticias para GitHub Pages.

## Fuentes automatizadas en esta versión

- BOE — canal de convenios colectivos.
- BOE — legislación de Trabajo y empleo.
- BOE — legislación de Seguridad Social.
- BOC — sección III, Otras resoluciones.
- Gobierno de Canarias — feed de Turismo y Empleo.

Estas fuentes ofrecen RSS oficiales. El BOE publica canales RSS temáticos, incluidos convenios colectivos y legislación de Trabajo y empleo; el BOC ofrece feeds por sección; y el Gobierno de Canarias ofrece RSS por consejería, incluida Turismo y Empleo. El Poder Judicial también dispone de RSS para Noticias Judiciales y TSJ Canarias, pero sus endpoints concretos se dejan desactivados hasta validarlos en ejecución para no introducir enlaces frágiles.

## Fuentes preparadas pero desactivadas

- Seguridad Social: la web oficial confirma canales RSS, pero hay que seleccionar los endpoints concretos.
- Poder Judicial / TSJ Canarias / Tribunal Supremo: el CGPJ confirma RSS específicos; se activarán tras validar sus URLs.
- UGT y UGT Canarias: se mantienen como fuentes editoriales prioritarias, pero se activarán con extractores HTML específicos y pruebas de estructura.

## Criterio

1. Fuente primaria antes que prensa.
2. Dedupl icación por URL.
3. Ventana de 14 días.
4. Máximo 250 noticias.
5. Clasificación automática por palabras clave.
6. Las sentencias se identifican separadamente.
7. La fuente original siempre se conserva.

## GitHub Pages

Settings → Pages → Deploy from branch → `main` → `/ (root)`.

## Automatización

GitHub Actions ejecuta el colector cada hora. GitHub advierte que los trabajos programados pueden retrasarse en momentos de alta carga, por lo que “cada hora” debe entenderse como una frecuencia objetivo, no como una garantía al minuto.

La PWA también comprueba `noticias.json` cada 60 minutos cuando permanece abierta.
