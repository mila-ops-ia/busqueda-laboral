# Búsqueda laboral automática 🔎

Un script que todos los días busca avisos nuevos en LinkedIn, los puntúa según mi perfil y los suma a un Google Sheet donde sigo mis postulaciones.

## Por qué lo armé

Buscar trabajo me estaba llevando horas: abrir avisos, leer requisitos y anotar en una planilla cuáles valían la pena. Es el mismo problema que vi muchas veces en operaciones: una tarea manual que se repite todos los días. Así que hice lo que me gusta hacer: entender el proceso y automatizarlo.

## Qué hace

1. **Busca** en el listado público de LinkedIn los avisos de las últimas 24 horas en mi zona, con las palabras clave que configuré (logística, procesos, supply chain, SAP, entre otras).
2. **Filtra** los que no son de mi área, como ventas, puestos junior o desarrollo de software, y los que ya revisó en pasadas anteriores. También descarta los que quedan fuera de mi zona (en mi caso, zona norte): si el aviso solo dice "Buenos Aires", busca en el texto dónde es, y si no lo aclara lo deja con "Ubicación exacta" para verificar. Los remotos pasan siempre.
3. **Lee cada aviso y le pone un puntaje del 1 al 10.** Suma por lo que coincide con mi experiencia (SAP, KPIs, operadores 3PL, mejora de procesos, IA) y resta por lo que me falta o no me conviene (inglés avanzado, título de Ingeniería, puestos de planta, distancia).
4. **Mira el rubro de la empresa.** Suma si es farmacéutica o de salud, fintech o banca, o una multinacional, que es donde ya trabajé, y lo anota primero en "lo que cumplo".
5. **Arma una fila por aviso** con el puntaje, la prioridad, lo que cumplo, lo que me falta, los km aproximados, la modalidad, la cantidad de postulantes, el link y el contacto si figura.
6. **Claude agrega las filas** al Sheet con el conector de Google Sheets, todos los días a las 8.

## Cómo está hecho

- **Python, sin librerías externas.** Usa solo la biblioteca estándar.
- **Configurable:** la zona, las localidades permitidas, las palabras clave, el puntaje mínimo y la tabla de distancias están en `config.json`.
- **Sin repetidos:** guarda en `vistos.json` los avisos que ya revisó.
- **Programado con una tarea de Claude.** En [tarea-programada.md](tarea-programada.md) está el texto que uso.

## Cómo usarlo

1. Copiá `config.ejemplo.json` como `config.json` y poné tu zona, tus palabras clave y tus distancias.
2. Corré `python3 buscar_avisos.py`.
3. Revisá `nuevas_filas.json`, o programá la tarea para que las filas lleguen solas a tu Sheet.

Para adaptar el puntaje a otro perfil, editá las reglas de la función `puntuar` en `buscar_avisos.py`.

## Lo que aprendí

- **El puntaje automático ordena, pero no reemplaza leer el aviso.** Al principio se colaban puestos de testing de software porque decían "automatización". Fui ajustando los filtros con cada pasada.
- **Probé primero con n8n.** El flujo quedó armado, pero me trabé al conectar Google, y además la prueba gratuita tenía fecha de vencimiento. La versión local es más simple y gratis. Lo malo es que corre solo con la compu prendida.
- **Menos es más.** De más de 1.200 avisos de la zona, unos 100 encajaban de verdad. Ese filtro es lo que más tiempo me ahorra.

## Aviso

Usa el listado público de avisos de LinkedIn, sin iniciar sesión, para uso personal y con pausas entre pedidos. LinkedIn puede cambiar ese listado o limitarlo en cualquier momento.
