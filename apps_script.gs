/**
 * Receptor de avisos para el Sheet "Avisos zona norte 80 km - seguimiento de postulaciones".
 *
 * El script de Python (buscar_avisos.py) le manda las filas nuevas por POST y este código
 * las agrega al final de la pestaña "Avisos". Así la carga diaria no necesita a Claude
 * y no consume tokens.
 *
 * Instalación (una sola vez): proyecto nuevo en script.new, pegá este archivo.
 *   2. Configuración del proyecto (engranaje) → Propiedades de la secuencia de comandos →
 *      agregá la propiedad TOKEN con una clave larga (la misma que va en config.json como "sheet_token").
 *   3. Implementar → Nueva implementación → Tipo: Aplicación web.
 *      Ejecutar como: Yo. Quién tiene acceso: Cualquier usuario.
 *      Autorizá los permisos y copiá la URL (termina en /exec) en config.json como "sheet_webhook".
 *
 * Seguridad: sin el TOKEN correcto no se agrega nada. El código solo agrega filas al final
 * de "Avisos"; no lee, no borra ni edita filas existentes.
 */
function doPost(e) {
  var salida = function (obj) {
    return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
  };
  try {
    var datos = JSON.parse(e.postData.contents);
    var token = PropertiesService.getScriptProperties().getProperty('TOKEN');
    if (!token || datos.token !== token) return salida({ ok: false, error: 'token' });

    var filas = datos.filas || [];
    if (!filas.length) return salida({ ok: true, agregadas: 0 });
    if (filas.some(function (f) { return f.length !== 26; })) return salida({ ok: false, error: 'columnas' });

    var lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try {
      var hoja = SpreadsheetApp.openById('1-E5Zg_-PqUa9y5HKA3Msi8ETacByXT-bQcImcbwXJYQ').getSheetByName('Avisos');
      var primera = hoja.getLastRow() + 1;
      hoja.getRange(primera, 1, filas.length, 26).setValues(filas);
      SpreadsheetApp.flush();
      return salida({ ok: true, agregadas: filas.length, primera_fila: primera });
    } finally {
      lock.releaseLock();
    }
  } catch (err) {
    return salida({ ok: false, error: String(err) });
  }
}
