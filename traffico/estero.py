"""Eventi di traffico da Francia (Bison Futé, dati aperti) e Svizzera (opentransportdata.swiss, serve chiave).

Entrambe le fonti usano DATEX II: lo leggo in modo generico (senza dipendere dai namespace)
e produco eventi nello stesso formato del CCISS, con testo in italiano e coordinate.
"""
import hashlib, os, re, urllib.request, datetime
import xml.etree.ElementTree as ET

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
FR_URL = "http://tipi.bison-fute.gouv.fr/bison-fute-ouvert/publicationsDIR/Evenementiel-DIR/grt/RRN/content.xml"
CH_URL = "https://api.opentransportdata.swiss/TDP/Soap_Datex2/Pull"
CH_ACTION = "http://opentransportdata.swiss/TDP/Soap_Datex2/Pull/v1/pullTrafficMessages"

# --- Traduzione dal francese: frasi e parole ricorrenti; i nomi di luogo restano in francese ---
FRASI = [
    (r"\bdu (?:\w+di |lundi |mardi |mercredi |jeudi |vendredi |samedi |dimanche )?(\d{1,2}/\d{1,2}) [àa] (\d{1,2})h(\d{2})? (?:au|[àa]) (?:\w+ )?(\d{1,2}/\d{1,2}) [àa] (\d{1,2})h(\d{2})?",
     lambda m: f"dal {m.group(1)} ore {m.group(2)}:{m.group(3) or '00'} al {m.group(4)} ore {m.group(5)}:{m.group(6) or '00'}"),
    (r"\bdans le secteur (de|du|des)\b", "nella zona di"), (r"\bDirection\b", "direzione"), (r"\bsecteur\b", "zona"),
    (r"\ble (\d{1,2})(?:er)? ", r"il \1 "), (r"\bla nuit du\b", "la notte del"),
    (r"^De (.+?) vers (.+)$", lambda m: f"Direzione {m.group(2)} (da {m.group(1)})"),
    (r"(?<![\w-])la nuit du\b", "la notte di"), (r"\bde (\d{1,2})\s?h(\d{2})?\s+[àa]\s+(\d{1,2})\s?h(\d{2})?", lambda m: f"dalle {m.group(1)}:{m.group(2) or '00'} alle {m.group(3)}:{m.group(4) or '00'}"),
    (r"\ble lendemain\b", "del giorno dopo"), (r"\bfermeture des voies\b", "chiusura delle corsie"), (r"\bdes voies\b", "delle corsie"),
    (r"\ble pont\b", "il ponte"), (r"(?<![\w-])de l[’']", "dell’"), (r"(?<![\w-])l[’']A(\d)", r"l’A\1"), (r"\bdans les deux sens( de circulation)?\b", "in entrambe le direzioni"),
    (r"\bpour r[ée]nover\b", "per rinnovare"), (r"\bdit de\b", "detto"), (r"\bnuits? de fermeture\b", "notti di chiusura"),
    (r"\bjeudi\b", "giovedì"), (r"\bdans le secteur (de|du|des)\b", "nella zona di"), (r"\bitin[ée]raires?\b", "percorso"),
    (r"\bdu (\d{1,2}/\d{1,2}) au (\d{1,2}/\d{1,2})\b", r"dal \1 al \2"), (r"\bau niveau (de|du)?\b", "all'altezza di"), (r"\bn°\s?", "n. "), (r"\bfluide\b", "scorrevole"), (r"\bdense\b", "intenso"), (r"\bsatur[ée]\b", "bloccato"),
    (r"\b1er\b", "1"), (r"(?<![\w-])à(?![\w-])", "a"), (r"\bvitesse r[ée]duite\b", "velocità ridotta"), (r"\bvitesse\b", "velocità"),
    (r"\bdans le cadre de l[’']application du\b", "in applicazione del"), (r"\bde la Vall[ée]e\b", "della valle"), (r"\bcomme\b", "come"), (r"^Cause\b", "Causa"), (r"\bnord\b", "nord"),
    (r"Point particulier\s*:\s*", ""),
    (r"d[ée]but\s*:\s*situ[ée]\s+", "da "), (r",?\s*fin\s*:\s*situ[ée]\s+", " fino a "), (r"\bsitu[ée]e?\s+", ""),
    (r"\b(\d[\d.,]*)\s*m\s+au\s+(nord|sud)\s+de\s+", lambda m: f"{m.group(1)} m a {m.group(2)} di "),
    (r"\b(\d[\d.,]*)\s*m\s+à\s+l'(est|ouest)\s+de\s+", lambda m: f"{m.group(1)} m a {'est' if m.group(2)=='est' else 'ovest'} di "),
    (r"\bLa mesure est obligatoire\.?", ""), (r"\bArr[êe]t[ée]\s*(n°)?\s*[\w./–-]*\d[\w./–-]*\.?", ""),
    (r"\bTravaux de construction\b", "lavori di costruzione"), (r"\bTravaux de maintenance\b", "lavori di manutenzione"),
    (r"\bTravaux d'entretien\b", "lavori di manutenzione"), (r"\bTravaux\b", "lavori"),
    (r"\bAlternat par feux( de chantier)?\b", "senso unico alternato con semaforo"), (r"\balternat\b", "senso unico alternato"), (r"\bchantier\b", "cantiere"),
    (r"\bfeux tricolores\b", "semaforo"), (r"\bviabilit[ée] hivernale\b", "viabilità invernale"),
    (r"\bfermeture hivernale\b", "chiusura invernale"), (r"\bfermeture( totale)?\b", "chiusura"), (r"\bcoupure( totale)?\b", "chiusura"),
    (r"\bferm[ée]e?s?\b", "chiuso"), (r"\bbarr[ée]e?s?\b", "chiuso"), (r"\bcoup[ée]e?s?\b", "interrotto"),
    (r"\bneutralisation( de| d'une)? (la )?voie( de droite| de gauche)?\b", lambda m: "corsia chiusa" + (" a destra" if m.group(3) and "droite" in m.group(3) else " a sinistra" if m.group(3) else "")),
    (r"\bvoie neutralis[ée]e\b", "corsia chiusa"), (r"\bvoies? de droite\b", "corsia di destra"), (r"\bvoies? de gauche\b", "corsia di sinistra"),
    (r"\bchauss[ée]e r[ée]tr[ée]cie\b", "carreggiata ristretta"), (r"\bchauss[ée]e\b", "carreggiata"), (r"\br[ée]tr[ée]cie?\b", "ristretta"),
    (r"\bbasculement de circulation\b", "deviazione sull'altra carreggiata"), (r"\bd[ée]viation\b", "deviazione"),
    (r"\blimitation de vitesse\b", "limite di velocità"), (r"\bvitesse limit[ée]e\b", "velocità ridotta"),
    (r"\binterdiction (à la circulation )?des v[ée]hicules de plus de\b", "vietato ai veicoli oltre"), (r"\baccès interdit\b", "accesso vietato"),
    (r"\binterdit\b", "vietato"), (r"\bconvois? exceptionnels?\b", "trasporto eccezionale"), (r"\baccident\b", "incidente"),
    (r"\bv[ée]hicule en panne\b", "veicolo in avaria"), (r"\bbouchons?\b", "coda"), (r"\bralentissements?\b", "rallentamenti"),
    (r"\bneige\b", "neve"), (r"\bverglas\b", "ghiaccio"), (r"\bbrouillard\b", "nebbia"), (r"\b[ée]quipements sp[ée]ciaux obligatoires\b", "catene o gomme invernali obbligatorie"),
    (r"\bchutes de blocs\b", "caduta massi"), (r"\bprotection contre les\b", "protezione contro"), (r"\b[ée]lagage( d'arbres)?\b", "potatura alberi"),
    (r"\beffondrement( de talus)?\b", "frana"), (r"\bmur anti-?bruit\b", "barriera antirumore"), (r"\benrob[ée]\b", "asfaltatura"),
    (r"\braccordement fibre optique\b", "collegamento fibra ottica"), (r"\bassainissement\b", "fognature"), (r"\bhydrocurage\b", "pulizia condotte"),
    (r"\bsortie\b", "uscita"), (r"\bentr[ée]e\b", "entrata"), (r"\bbretelle\b", "rampa"), (r"\b[ée]changeur\b", "svincolo"),
    (r"\baire( de repos| de service)?\b", "area di servizio"), (r"\bpont\b", "ponte"), (r"\bviaduc\b", "viadotto"), (r"\btunnel\b", "galleria"), (r"\bcol\b", "passo"),
    (r"\bsens\b", "direzione"), (r"\bvers\b", "verso"), (r"\bentre\b", "tra"), (r"\bjusqu'(au|en|à)\b", "fino a"),
    (r"\b24h/24\b", "giorno e notte"), (r"\bde nuit\b", "di notte"), (r"\bla nuit\b", "di notte"), (r"\bde jour\b", "di giorno"), (r"\bweek-?end\b", "fine settimana"),
    (r"\bjours? f[ée]ri[ée]s\b", "festivi"), (r"\bhabituellement\b", "di solito"), (r"\bsaison\b", "stagione"), (r"\bcirculation\b", "traffico"),
    (r"\bvoies?\b", "corsia"), (r"\bet\b", "e"), (r"\bsur\b", "su"), (r"\bpour\b", "per"), (r"\bavec\b", "con"), (r"\bdans\b", "in"),
    (r"\bouest\b", "ovest"), (r"\btonnes\b", "tonnellate"), (r"\bancienne\b", "ex"), (r"\bau\b", "a"), (r"\baux\b", "ai"), (r"\bde\b", "di"), (r"\bd'", "di "),
    (r"\bde la\b", "della"), (r"\bdes\b", "dei"), (r"\bdu\b", "del"), (r"\bles\b(?!\s+[A-ZÀ-Ý])", "i"), (r"\bde la\b(?=\s+[A-ZÀ-Ý])", "de la"),
    (r"\blundi\b", "lunedì"), (r"\bmardi\b", "martedì"), (r"\bmercredi\b", "mercoledì"), (r"\bjeudi\b", "giovedì"), (r"\bvendredi\b", "venerdì"), (r"\bsamedi\b", "sabato"), (r"\bdimanche\b", "domenica"),
    (r"\bjanvier\b", "gennaio"), (r"\bf[ée]vrier\b", "febbraio"), (r"\bmars\b", "marzo"), (r"\bavril\b", "aprile"), (r"\bmai\b", "maggio"), (r"\bjuin\b", "giugno"),
    (r"\bjuillet\b", "luglio"), (r"\bao[ûu]t\b", "agosto"), (r"\bseptembre\b", "settembre"), (r"\boctobre\b", "ottobre"), (r"\bnovembre\b", "novembre"), (r"\bd[ée]cembre\b", "dicembre"),
]
def traduci(t):
    t = re.sub(r"(?<=\w)-(?=\w)", "QXQ", t)   # protegge i nomi composti (Saint-Félix-de-Lodez)
    for a, b in FRASI:
        t = re.sub(a, b, t, flags=re.I)
    t = t.replace("QXQ", "-")
    t = re.sub(r"\s+([,.;:])", r"\1", re.sub(r"\s{2,}", " ", t)).strip(" ,.;:-")
    return t[:1].upper() + t[1:] if t else ""

def loc(el):
    return el.tag.rsplit("}", 1)[-1]

def figli(el, nome):
    return [x for x in el.iter() if loc(x) == nome]

def testo_di(el, nome):
    for x in el.iter():
        if loc(x) == nome and (x.text or "").strip():
            return x.text.strip()
    return None

def ora(iso):
    try:
        d = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(
            datetime.timezone(datetime.timedelta(hours=1)))
    except Exception:
        return None
    return d

def periodo(rec):
    a, b = ora(testo_di(rec, "overallStartTime") or ""), ora(testo_di(rec, "overallEndTime") or "")
    if not a:
        return ""
    s = f"dalle {a:%H:%M} del {a.day} {MESI[a.month-1]} {a.year}"
    if b and (b - a).days < 60:
        s += f" alle {b:%H:%M} del {b.day} {MESI[b.month-1]} {b.year}"
    return s

def classifica(rec):
    xtype = ""
    for k, v in rec.attrib.items():
        if k.endswith("}type") or k == "type":
            xtype = v.split(":")[-1]
    blob = (xtype + " " + " ".join((x.text or "") for x in rec.iter() if loc(x).endswith("Type"))).lower()
    if "accident" in blob or "vehicleobstruction" in blob:
        return "incidente", "incidente"
    if "roadclosed" in blob or "carriagewayclosures" in blob or "closed" in blob:
        return "chiusura", "strada chiusa"
    if "maintenance" in blob or "construction" in blob or "roadworks" in blob or "laneclosures" in blob:
        return "lavori", "lavori"
    if "abnormaltraffic" in blob or "queue" in blob or "congest" in blob:
        return "code", "code"
    if "weather" in blob or "environment" in blob or "snow" in blob or "ice" in blob or "fog" in blob:
        return "meteo", "condizioni meteo"
    return "altro", "segnalazione"

def coordinate(rec):
    lat = [float(x.text) for x in rec.iter() if loc(x) == "latitude" and x.text]
    lon = [float(x.text) for x in rec.iter() if loc(x) == "longitude" and x.text]
    pts = list(zip(lat, lon))
    return pts[0] if pts else None, (pts[-1] if len(pts) > 1 and pts[-1] != pts[0] else None)

def da_datex(xml_bytes, paese):
    root = ET.fromstring(xml_bytes)
    out = []
    for rec in figli(root, "situationRecord"):
        tipo, frase = classifica(rec)
        p1, p2 = coordinate(rec)
        if not p1:
            continue
        a, b = ora(testo_di(rec, "overallStartTime") or ""), ora(testo_di(rec, "overallEndTime") or "")
        adesso = datetime.datetime.now(datetime.timezone.utc)
        if b and b < adesso:
            continue                      # già finito
        if a and not b and (adesso - a).days > 120 and tipo in ("altro", "meteo", "code", "incidente"):
            continue                      # segnalazione vecchia senza fine: probabilmente scaduta
        strada = testo_di(rec, "roadNumber") or testo_di(rec, "roadName") or "Strada"
        strada = re.sub(r"^([ANDM])0*(\d)", r"\1\2", strada)
        commento = ""
        parti = []
        for gc in figli(rec, "generalPublicComment"):
            v = re.sub(r"\s+", " ", testo_di(gc, "value") or "")
            if re.match(r"^(DIR |District |CEI |SREI)", v): continue   # nome dell'ufficio che gestisce, non serve
            v = traduci(v)
            if v and v not in parti: parti.append(v)
        commento = " · ".join(parti)
        commento = re.sub(r"\s+", " ", commento)[:240]
        if tipo in ("altro", "lavori") and re.search(r"\b(ferm[ée]e?s?|fermeture|coup[ée]e?|barr[ée]e?|gesperrt|Sperrung)\b", commento, re.I):
            tipo, frase = "chiusura", "strada chiusa"
        tipi = " ".join((x.text or "") for x in rec.iter() if loc(x) in ("roadOrCarriagewayOrLaneManagementType", "roadMaintenanceType", "constructionWorkType")).lower()
        if "carriagewayclosures" in tipi or "roadclosed" in tipi: corsie = "carreggiata chiusa"
        elif "laneclosures" in tipi or "narrowlanes" in tipi or "singlealternatelinetraffic" in tipi: corsie = "corsie ridotte"
        elif "contraflow" in tipi: corsie = "doppio senso su una carreggiata"
        else: corsie = ""
        testo = f"{frase} {periodo(rec)}".strip()
        if commento:
            testo += f" · {commento}"
        e = {"id": hashlib.sha1((paese + (rec.get("id") or testo)).encode()).hexdigest()[:16],
             "strada": f"{strada} ({paese})", "testo": testo, "tipo": tipo,
             "quando": testo_di(rec, "situationRecordVersionTime") or "",
             "corsie": corsie, "inizio": a.isoformat() if a else "", "fine": b.isoformat() if b else "",
             "lat": round(p1[0], 5), "lon": round(p1[1], 5), "paese": paese}
        if p2:
            e.update(lat2=round(p2[0], 5), lon2=round(p2[1], 5))
        out.append(e)
    return out

def francia():
    r = urllib.request.Request(FR_URL, headers={"User-Agent": "Mozilla/5.0"})
    return da_datex(urllib.request.urlopen(r, timeout=60).read(), "Francia")

def svizzera():
    token = os.environ.get("OTD_TOKEN", "").strip()
    if not token:
        return None
    body = ('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
            'xmlns:dx223="http://datex2.eu/schema/2/2_0"><soapenv:Header/><soapenv:Body>'
            '<dx223:d2LogicalModel modelBaseVersion="2"><dx223:exchange><dx223:supplierIdentification>'
            '<dx223:country>ch</dx223:country><dx223:nationalIdentifier>OTD</dx223:nationalIdentifier>'
            '</dx223:supplierIdentification></dx223:exchange></dx223:d2LogicalModel>'
            '</soapenv:Body></soapenv:Envelope>').encode()
    r = urllib.request.Request(CH_URL, data=body, method="POST", headers={
        "Authorization": token, "Content-Type": "text/xml; charset=utf-8", "SOAPAction": CH_ACTION})
    return da_datex(urllib.request.urlopen(r, timeout=60).read(), "Svizzera")
