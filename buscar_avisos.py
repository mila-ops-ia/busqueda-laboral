#!/usr/bin/env python3
"""Busca avisos nuevos en LinkedIn (últimas 24 h) y los puntúa según un perfil de operaciones y procesos.

Uso: python3 buscar_avisos.py
  Lee config.json (zona, palabras clave, distancias) y vistos.json (links ya evaluados).
  Escribe nuevas_filas.json con las filas que superan el puntaje mínimo, en el orden de
  columnas del Sheet. Después suma a vistos.json
  todos los avisos evaluados en esta pasada.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from html import unescape

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CARPETA = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(CARPETA, "config.json"), encoding="utf-8"))
LOCATION = CONFIG["ubicacion"]
DISTANCIA = CONFIG.get("distancia_millas", 50)
KEYWORDS = CONFIG["palabras_clave"]
PUNTAJE_MINIMO = CONFIG.get("puntaje_minimo", 6)
MAX_NUEVOS = CONFIG.get("max_avisos_por_pasada", 80)
ORIGEN = CONFIG.get("origen_distancias", "tu casa")
KM = CONFIG.get("distancias_km", {})
ZONA = [z.lower() for z in CONFIG.get("zona_permitida", [])]
FUERA_TXT = CONFIG.get("texto_fuera_de_zona", [])
RUTA_ULTIMA = os.path.join(CARPETA, "ultima_pasada.txt")


def ventana_segundos():
    """Busca desde la última pasada que terminó bien (máximo 7 días), para no perder avisos si un día no corrió."""
    try:
        ultima = datetime.fromisoformat(open(RUTA_ULTIMA, encoding="utf-8").read().strip())
        seg = int((datetime.now() - ultima).total_seconds()) + 3 * 3600
    except (OSError, ValueError):
        seg = 86400
    return max(86400, min(seg, 7 * 86400))


VENTANA_SEG = ventana_segundos()

COLUMNAS = [
    "Puntaje (1 a 10)", "Prioridad", "Estado", "Mi observación", "Puesto", "Empresa", "Área", "Nivel", "Ubicación",
    "Km aprox. desde " + ORIGEN, "Modalidad", "Publicado", "Días publicado", "Postulantes",
    "Lo que cumplís", "Lo que te falta", "Filtro duro", "A verificar", "Link del aviso", "Contacto en el aviso",
    "Perfil del contacto", "Opiniones de la empresa", "Fecha de postulación", "Próximo paso", "Notas",
    "Agregado el",
]

INCLUIR = re.compile(r"(log[ií]st|operaci|operations|\bops\b|supply|cadena de (abast|sumin)|proceso|process|mejora continua|continuous improvement|planific|planning|planner|s&op|abastec|procurement|compras|invent|stock|distribu|transform|automatiz|automation|excelencia|excellence|\bsap\b|almac|dep[oó]sito|warehouse|comex|comercio exterior|fulfil|order|pedidos|customer (ops|operations)|calidad|quality|pmo|project manager|proyecto|business analyst|transporte|transport|demand|demanda|back ?office|facturaci)")
EXCLUIR = re.compile(r"(chofer|conductor|operari[oa]|repositor|vendedor|cajer|pe[oó]n|soldador|mec[aá]nic|electricista|electromec|autoelevador|clarkista|picker|preparador|pasant|trainee|intern\b|internship|desarroll|developer|programador|m[eé]dic|enfermer|docente|profesor|mozo|cociner|vigilad|telemarket|call center|ventas|sales|ejecutiv[oa] comercial|contador|abogad|recursos humanos|rrhh|\bhr\b|recruit|marketing|dise[ñn]ador|designer|editor|artist|social|medios|media planner|cadete|maestranza|limpieza|empaque|embalaje|armador|ayudante|eventual|baulerista|auxiliar|asistente|assistant|operador|operadora|\bjr\b|junior|administrativ|recepcionista|promotor|repartidor|preventista|data entry|soporte t[eé]cnico|help ?desk|t[eé]cnic|full stack|frontend|backend|tester|testing|devops|cloud|\bsre\b|financial planning|financier|cr[eé]dito|corrosi|cl[ií]nic|associate|\bqa\b|quality assurance|automation engineer|appium|selenium|gastron[oó]m|mantenimiento|perforaci)")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9"})
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if getattr(e, "code", None) == 429:
                time.sleep(15)
            else:
                time.sleep(3)
    return ""


def limpiar(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = re.sub(r"</(p|li|h\d)>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


def tomar(texto, patron):
    m = re.search(patron, texto, re.S)
    return limpiar(m.group(1)) if m else ""


def km_de(ubicacion, desc):
    u = (ubicacion or "").lower()
    for k, v in KM.items():
        if k in u:
            return v
    d = " " + (desc or "")[:3000].lower()
    best = None
    for k, v in KM.items():
        if " " + k in d and (best is None or v < best):
            best = v
    return best


def zona_de(ubicacion, desc):
    """Dice si el aviso está en la zona permitida: "dentro", "fuera" o "sin dato".

    Primero mira la ubicación del aviso. Si es genérica (por ejemplo "Buenos Aires"),
    busca en el texto menciones de la zona permitida o de zonas que no interesan.
    Sin zona_permitida en config.json, no filtra.
    """
    if not ZONA:
        return "dentro"
    u = (ubicacion or "").lower()
    if any(z in u for z in ZONA):
        return "dentro"
    if any(k in u for k in KM) or any(re.search(p, u) for p in FUERA_TXT):
        return "fuera"
    d = " " + (desc or "")[:4000].lower()
    if any(re.search(r"\b" + re.escape(z) + r"\b", d) for z in ZONA):
        return "dentro"
    if any(re.search(p, d) for p in FUERA_TXT):
        return "fuera"
    return "sin dato"


def buscar(links):
    vistos, avisos, claves = set(), [], set()
    for kw in KEYWORDS:
        for start in (0, 10):
            url = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords="
                   + urllib.parse.quote(kw) + "&location=" + urllib.parse.quote(LOCATION)
                   + "&distance=" + str(DISTANCIA) + "&f_TPR=r" + str(VENTANA_SEG) + "&start=" + str(start))
            html = get(url)
            time.sleep(0.8)
            trozos = html.split('data-entity-urn="')[1:]
            for t in trozos:
                m = re.search(r"jobPosting:(\d+)", t)
                if not m or m.group(1) in vistos:
                    continue
                jid = m.group(1)
                vistos.add(jid)
                titulo = tomar(t, r"base-search-card__title[^>]*>(.*?)</h3>")
                empresa = tomar(t, r"base-search-card__subtitle[^>]*>(.*?)</h4>")
                ubic = tomar(t, r"job-search-card__location[^>]*>(.*?)</span>")
                fm = re.search(r'datetime="([^"]+)"', t)
                link = "https://www.linkedin.com/jobs/view/" + jid
                tl = titulo.lower()
                if not titulo or link in links or (titulo + "|" + empresa).lower() in claves:
                    continue
                if not INCLUIR.search(tl) or EXCLUIR.search(tl):
                    continue
                claves.add((titulo + "|" + empresa).lower())
                avisos.append({"id": jid, "titulo": titulo, "empresa": empresa, "ubicacion": ubic,
                               "fecha": fm.group(1) if fm else "", "link": link})
            if len(trozos) < 10:
                break
    return avisos[:MAX_NUEVOS]


EMPRESAS_RUBRO = {
    "farma o salud": r"johnson ?& ?johnson|j&j|kenvue|merz|bayer|roche|novartis|pfizer|sanofi|astrazeneca|abbott|abbvie|allergan|baxter|bag[oó]|roemmers|gador|elea|raffo|casasco|biog[eé]nesis|medtronic|b\. ?braun|fresenius|gsk|glaxo|\bmsd\b|boehringer|takeda|novo nordisk|galderma|siemens healthineers|becton|\bbd\b|stryker|droguer|scienza|osde|swiss medical|laboratorio|pharma|farma|biotec|health|salud|medical|m[eé]dic",
    "fintech o banca": r"itti|ueno|mercado pago|mercadopago|ual[aá]|naranja x|galicia|santander|bbva|macro|icbc|hsbc|brubank|\bmodo\b|prisma|payway|fiserv|visa|mastercard|lemon|\bbelo\b|personal pay|\bprex\b|fintech|banco|\bbank\b|pagos|payments",
    "multinacional": r"unilever|procter|p&g|nestl[eé]|danone|coca[- ]cola|pepsico|mondelez|kimberly|\b3m\b|siemens|\bdhl\b|kuehne|\bdsv\b|maersk|schneider|accenture|deloitte|\bpwc\b|\bey\b|kpmg|loreal|l'or[eé]al|natura|amazon|mercadolibre|mercado libre|cervecer[ií]a|quilmes|ab ?inbev|heineken|arcor|bimbo|cargill|bunge|syngenta|basf|dow\b|whirlpool|samsung|lg\b|philips|bosch",
}
DESC_RUBRO = {
    "farma o salud": r"industria farmac[eé]utica|laboratorio farmac[eé]utico|empresa farmac[eé]utica|productos farmac[eé]uticos|dispositivos m[eé]dicos|sector salud|industria de la salud|healthcare|life sciences|insumos m[eé]dicos",
    "fintech o banca": r"\bfintech\b|entidad financiera|entidad bancaria|sector bancario|billetera virtual|billetera digital",
    "multinacional": r"multinacional|l[ií]der mundial|l[ií]der global|presencia en m[aá]s de \d+ pa[ií]ses|global company|compañ[ií]a global|empresa global",
}
PESO_RUBRO = {"farma o salud": 0.8, "fintech o banca": 0.8, "multinacional": 0.4}


def rubro_de(empresa, texto):
    """Devuelve los rubros afines a la experiencia de Mila que se ven en la empresa o en el aviso."""
    emp = empresa.lower()
    encontrados = []
    for rubro in PESO_RUBRO:
        if re.search(EMPRESAS_RUBRO[rubro], emp) or re.search(DESC_RUBRO[rubro], texto):
            encontrados.append(rubro)
    return encontrados


def puntuar(j, html):
    desc = tomar(html, r"show-more-less-html__markup[^>]*>(.*?)</div>")[:6000]
    appl = tomar(html, r"num-applicants__caption[^>]*>(.*?)</(?:span|figcaption)>")
    poster = tomar(html, r"base-main-card__title[^>]*>(.*?)</h3>")
    poster_sub = tomar(html, r"base-main-card__subtitle[^>]*>(.*?)</h4>")
    pm = re.search(r'base-main-card__full-link[^>]*href="([^"?]+)', html)
    poster_url = pm.group(1) if pm else ""
    t = j["titulo"].lower()
    x = (desc + " " + j["titulo"]).lower()
    pros, cons, ver = [], [], []
    s, P, area, nivel = 3.5, 0.0, "Otro", "Analista"

    if re.search(r"proceso|process|mejora continua|continuous|transforma|excelencia|excellence|automatiz|automation|innovaci", t):
        s, area = 6, "Procesos / mejora continua"
    elif re.search(r"log[ií]st|distribu|supply|cadena|almac|dep[oó]sito|warehouse|abastec|invent|stock|planific|planner|planning|s&op|transporte|transport|comex|comercio exterior|demand|ultima milla|última milla|crossdock", t):
        s, area = 5, "Logística / supply chain"
    elif re.search(r"operaci|operations|\bops\b|fulfil|order|pedidos|customer", t):
        s, area = 5, "Operaciones"
    elif re.search(r"calidad|quality|pmo|project|proyecto|business analyst|datos|data|\bbi\b|facturaci", t):
        s, area = 4, "Calidad / proyectos / datos"

    if re.search(r"director|head of|\bvp\b|vice", t):
        s -= 1.5; nivel = "Dirección"; cons.append("Dirección: por encima de tu recorrido")
    elif re.search(r"gerente|manager", t):
        nivel = "Gerencia"; cons.append("Nivel gerencial: salto respecto de tu último puesto")
    elif re.search(r"jefe|jefa|lead|l[ií]der|responsable|team ?leader", t):
        s += 0.6; nivel = "Jefatura / líder"
    elif re.search(r"coordinador|coordinadora|coordinator|supervisor|supervisora|encargad", t):
        s += 0.6; nivel = "Coordinación / supervisión"
    elif re.search(r"\bsr\b|senior|semi ?senior|ssr|especialista|specialist|consultor|ingenier", t):
        s += 0.5; nivel = "Analista Sr / especialista"
    elif re.search(r"analista|analyst", t):
        s -= 0.8; cons.append("Puede estar por debajo de tu nivel")

    def suma(patron, p, txt):
        nonlocal P
        if re.search(patron, x):
            P += p; pros.append(txt)

    suma(r"\bsap\b", 0.8, "SAP")
    suma(r"power bi|looker|tablero|dashboard|quicksight|tableau", 0.5, "Tableros BI")
    suma(r"kpi|indicador", 0.5, "KPIs")
    suma(r"3pl|4pl|operador log[ií]stico|operadores log[ií]sticos|tercerizad", 0.6, "Operadores 3PL")
    suma(r"procedimiento|\bsop|instructivo|manual", 0.4, "Procedimientos")
    suma(r"mejora continua|as-is|to-be|bpmn|relevamiento|relevar|mapeo|lean|kaizen|reingenier", 0.6, "Mejora de procesos")
    suma(r"inteligencia artificial|\bia\b|\bai\b|gemini|chatgpt|claude|copilot|automatiz|automation|rpa", 1, "IA y automatización")
    suma(r"jira|salesforce|crm", 0.4, "Jira y Salesforce")
    suma(r"\bwms\b|\btms\b|warehouse management", 0.4, "WMS")
    suma(r"cadena de fr[ií]o|farma|medicament|laboratorio|insumos m[eé]dicos", 0.5, "Farma / cadena de frío")
    suma(r"inventario|stock|recuento|conciliaci", 0.4, "Inventarios")
    suma(r"liderar|liderazgo|equipo a cargo|personal a cargo|gesti[oó]n de equipo", 0.4, "Liderazgo")
    suma(r"scrum|kanban|[aá]gil|agile", 0.3, "Ágil")
    suma(r"factura|order to cash|o2c|cobranza|nota de cr[eé]dito", 0.3, "Facturación")
    suma(r"stakeholder|transversal|cross|interdisciplin|multifuncional", 0.3, "Trabajo con otras áreas")
    s += min(P, 3)

    # Rubro de la empresa: suma si se parece a donde ya trabajó (farma, salud, fintech o banca, multinacional)
    rubros = rubro_de(j["empresa"], x)
    if rubros:
        s += min(1.0, sum(PESO_RUBRO[r] for r in rubros))
        pros.insert(0, "Rubro afín: " + " y ".join(rubros))

    def resta(patron, p, txt):
        nonlocal s
        if re.search(patron, x):
            s -= p; cons.append(txt)

    resta(r"ingl[eé]s (avanzado|fluido|biling|excluyente)|advanced english|fluent english|english.{0,25}(fluent|advanced|proficien)|(fluent|advanced) (in )?english|nivel de ingl[eé]s avanzado", 1.5, "Inglés avanzado/fluido")
    if re.search(r"(the position|responsibilities|requirements|we are looking|you will)", x) and "Inglés avanzado/fluido" not in cons:
        s -= 1; cons.append("Aviso en inglés: probable inglés fluido")
    resta(r"ingenier[oa]s? industrial|ingenier[ií]a industrial|graduad[oa] en ingenier|t[ií]tulo de ingenier", 0.6, "Piden título de Ingeniería")
    resta(r"\bsql\b|python", 0.4, "SQL o Python")
    resta(r"power automate|power apps|powerapps", 0.3, "Power Automate / Power Apps")
    resta(r"flota|ruteo|ruteador|routing", 0.4, "Flota o ruteo")
    resta(r"six sigma|green belt|black belt", 0.3, "Certificación Six Sigma")
    resta(r"contador|contable|impositiv", 0.6, "Perfil contable o financiero")
    if re.search(r"turnos rotativos|rotativo|nocturno", x):
        s -= 0.5; cons.append("Turnos rotativos")
    if re.search(r"movilidad propia|veh[ií]culo propio|auto propio", x):
        ver.append("Movilidad propia")
    if re.search(r"disponibilidad para viajar|viajes frecuentes", x):
        ver.append("Viajes")
    if re.search(r"aiops|devops|\bbtp\b|abap|automatizaci[oó]n industrial|industrial automation|advanced analytics|data scien|machine learning|it operations|it process|\bplc\b|scada|consultor sap|sap consultant|architect|arquitect|pruebas|tosca|product manager|data engineer", t):
        s -= 2.5; cons.insert(0, "Perfil técnico de IT o desarrollo")
    if re.search(r"producci[oó]n|manufactur|planta|mantenimiento|energ[ií]a|ingeniero de operaciones|mejora continua", t) and re.search(r"(l[ií]nea de producci[oó]n|planta|manufactur|smed|tpm|oee|mantenimiento|automotriz|matricer|estampad)", x):
        s -= 1; cons.append("Orientado a planta o manufactura")
    if re.search(r"planificador de operaciones|analista de transporte|analista de tr[aá]fico", t):
        s -= 0.5

    mod = "No lo dice"
    if re.search(r"h[ií]brid|hybrid", x):
        mod = "Híbrido"
    elif re.search(r"100% remot|remoto|remote|home office", x):
        mod = "Remoto"
    elif re.search(r"presencial|on-site|onsite", x):
        mod = "Presencial"

    zona = zona_de(j["ubicacion"], desc)
    if zona == "fuera" and mod != "Remoto":
        return None
    if zona == "sin dato":
        ver.append("Ubicación exacta")

    kmv = km_de(j["ubicacion"], desc)
    if kmv is not None and kmv > 45:
        s -= 0.5; cons.append(f"Lejos ({kmv} km)")
    dias = ""
    if j["fecha"]:
        try:
            dias = max(0, (date.today() - datetime.strptime(j["fecha"], "%Y-%m-%d").date()).days)
        except ValueError:
            pass
    if re.search(r"m[aá]s de 100|200", appl.lower()):
        ver.append("Muchos postulantes")

    s = max(1, min(10, round(s * 2) / 2))
    if s < PUNTAJE_MINIMO:
        return None
    unicos = lambda l: ", ".join(dict.fromkeys(l))
    fila = {
        "Puntaje (1 a 10)": s,
        "Prioridad": "Alta" if s >= 8 else ("Media" if s >= 7 else "Baja"),
        "Estado": "Por postular",
        "Mi observación": "",
        "Puesto": j["titulo"],
        "Empresa": j["empresa"],
        "Área": area,
        "Nivel": nivel,
        "Ubicación": j["ubicacion"].replace(", Provincia de Buenos Aires, Argentina", "").replace(", Argentina", ""),
        "Km aprox. desde " + ORIGEN: "Sin dato" if kmv is None else kmv,
        "Modalidad": mod,
        "Publicado": j["fecha"],
        # Fórmula para que el Sheet recalcule los días cada día (usa la columna Publicado de la misma fila)
        "Días publicado": '=IF(INDIRECT("L"&ROW())="","",TODAY()-INDIRECT("L"&ROW()))',
        "Postulantes": appl.replace(" solicitudes", "").replace("Sé de los primeros 25 solicitantes", "Menos de 25"),
        "Lo que cumplís": unicos(pros),
        "Lo que te falta": unicos(cons),
        # Fórmula: marca si el aviso pide título de Ingeniería o inglés, que suelen ser filtros automáticos
        "Filtro duro": '=LET(t,INDIRECT("P"&ROW()),IF(INDIRECT("E"&ROW())="","",IF(OR(ISNUMBER(SEARCH("Ingenier",t)),ISNUMBER(SEARCH("ingl",t))),"Sí: "&TEXTJOIN(" y ",TRUE,IF(ISNUMBER(SEARCH("Ingenier",t)),"título",""),IF(ISNUMBER(SEARCH("ingl",t)),"inglés","")),"No")))',
        "A verificar": unicos(ver),
        "Link del aviso": j["link"],
        "Contacto en el aviso": (poster + (" - " + poster_sub[:60] if poster_sub else "")) if poster else "",
        "Perfil del contacto": poster_url,
        "Opiniones de la empresa": "https://www.glassdoor.com.ar/Search/results.htm?keyword=" + urllib.parse.quote(j["empresa"]),
        "Fecha de postulación": "",
        "Próximo paso": "",
        "Notas": "",
        "Agregado el": date.today().isoformat(),
    }
    return [fila[c] for c in COLUMNAS]


def main():
    carpeta = CARPETA
    ruta_vistos = os.path.join(carpeta, "vistos.json")
    vistos = set(json.load(open(ruta_vistos, encoding="utf-8"))) if os.path.exists(ruta_vistos) else set()
    avisos = buscar(vistos)
    filas = []
    for j in avisos:
        html = get("https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/" + j["id"])
        time.sleep(0.8)
        if not html:
            continue
        vistos.add(j["link"])
        fila = puntuar(j, html)
        if fila:
            filas.append(fila)
    filas.sort(key=lambda f: -f[0])
    json.dump(filas, open(os.path.join(carpeta, "nuevas_filas.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(sorted(vistos), open(ruta_vistos, "w", encoding="utf-8"), indent=0)
    open(RUTA_ULTIMA, "w", encoding="utf-8").write(datetime.now().isoformat(timespec="seconds"))
    print(f"Ventana de búsqueda: {VENTANA_SEG // 3600} horas. Avisos nuevos revisados: {len(avisos)}. Filas para agregar ({PUNTAJE_MINIMO} o más): {len(filas)}.")


if __name__ == "__main__":
    main()
