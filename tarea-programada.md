# Cómo programar la búsqueda con Claude

Yo la tengo como tarea programada en la app de Claude (Code), que corre todos los días a las 8 (`0 8 * * *`). Al principio corría también a las 20, pero como busca los avisos de las últimas 24 horas, una pasada por día alcanza y gasta la mitad. Este es el texto de la tarea. Reemplazá la ruta y el ID del Sheet por los tuyos.

```text
Tarea: agregar avisos de trabajo nuevos al Google Sheet de seguimiento.

1. Corré con Bash, sin cambiar nada del script:
   cd "<ruta a esta carpeta>" && python3 buscar_avisos.py
   Tarda entre 1 y 3 minutos (usá un timeout de 400000 ms).

2. Leé nuevas_filas.json. Es una lista de filas con 25 valores, en el orden de las
   columnas A a Y del Sheet. Si está vacía, terminá diciendo que no hubo avisos nuevos.

3. Si hay filas, agregalas con el conector de Google Sheets (append_values):
   - spreadsheetId: <ID de tu Sheet>
   - range: Avisos!A1
   - values: las filas tal cual vienen en el archivo.
   Si una celda de texto empieza con "+" o "=", anteponele una comilla simple (').
   Después verificá con get_values que se hayan agregado.

4. Terminá con un resumen corto: cuántas filas agregaste y los 3 mejores avisos.

Reglas: no borres ni edites filas existentes, no envíes mensajes y no te postules
a ningún aviso. Si el script falla, informalo sin inventar datos.
```

## El Sheet

La primera fila de la pestaña "Avisos" tiene que tener estos encabezados, en este orden:

Puntaje (1 a 10) · Prioridad · Estado · Mi observación · Puesto · Empresa · Área · Nivel · Ubicación · Km aprox. desde (tu origen) · Modalidad · Publicado · Días publicado · Postulantes · Lo que cumplís · Lo que te falta · A verificar · Link del aviso · Contacto en el aviso · Perfil del contacto · Opiniones de la empresa · Fecha de postulación · Próximo paso · Notas · Agregado el

Tené en cuenta que la tarea corre solo con la compu prendida y la app de Claude abierta.
