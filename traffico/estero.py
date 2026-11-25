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
        for gc in figli(rec, "generalPublicComment"):
            commento = testo_di(gc, "value") or ""
            if commento: break
        commento = re.sub(r"\s+", " ", commento)[:240]
        testo = f"{frase} {periodo(rec)}".strip()
        if commento:
            testo += f" · {commento}"
        e = {"id": hashlib.sha1((paese + (rec.get("id") or testo)).encode()).hexdigest()[:16],
             "strada": f"{strada} ({paese})", "testo": testo, "tipo": tipo,
             "quando": testo_di(rec, "situationRecordVersionTime") or "",
             "inizio": a.isoformat() if a else "", "fine": b.isoformat() if b else "",
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
