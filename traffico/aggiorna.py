"""Legge il feed CCISS e produce JSON con gli eventi sul corridoio Genova-Ginevra."""
import json, re, sys, os, time, html, urllib.request, urllib.parse, datetime, hashlib, xml.etree.ElementTree as ET
STRADE = r"\b(A26|A5|A4 Torino|A10 Genova|A7 Milano-Genova|A7 Serravalle|T1|T2|SS ?27|SS ?33|SS ?26)\b|Monte Bianco|Gran San Bernardo|Sempione"
def tipo(t):
    t = t.lower()
    for k, v in [("chius", "chiusura"), ("lavori", "lavori"), ("cantier", "lavori"), ("incidente", "incidente"),
                 ("coda", "code"), ("code", "code"), ("rallent", "code"), ("neve", "meteo"), ("catene", "meteo"), ("nebbia", "meteo")]:
        if k in t: return v
    return "altro"
req = urllib.request.Request("https://www.cciss.it/rss", headers={"User-Agent": "Mozilla/5.0"})
root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
out = []
for it in root.iter("item"):
    title = (it.findtext("title") or "").strip()
    desc = re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))
    desc = re.sub(r"\(Fonte:[^)]*\)", "", re.sub(r"\s+", " ", desc)).strip()
    if not re.search(STRADE, title + " " + desc, re.I): continue
    testo = desc[len(title):].strip() if desc.startswith(title) else desc
    did = hashlib.sha1((title + testo).encode()).hexdigest()[:16]
    out.append({"id": did, "strada": title, "testo": testo, "tipo": tipo(testo),
                "quando": it.findtext("{http://purl.org/dc/elements/1.1/}date") or ""})
# --- Coordinate dei luoghi (OpenStreetMap Nominatim, con cache) ---
CACHE = "traffico/sito/luoghi.json"
luoghi = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def pulisci(n):
    n = re.sub(r"^\d[\d,.]*\s*k?m\s+(?:prima|dopo)\s+(?:di\s+)?", "", n.strip())
    n = re.sub(r"^(Svincolo|Allacciamento|Area di servizio|Barriera|Incrocio|Uscita|Entrata|Diramazione)\s+", "", n, flags=re.I)
    n = re.sub(r"^(Entrata|Uscita)\s+", "", n, flags=re.I)
    n = re.sub(r"\s+(Est|Ovest|Nord|Sud|Centro)$", "", n).strip(" -/")
    if re.match(r"^A\d+\b", n): return None
    return n or None
def luoghi_di(testo):
    t = re.split(r"\s+in direzione\s+", testo)[0]
    m = re.search(r"\btra\s+(.+?)\s+e\s+(.+)$", t)
    if m: return [pulisci(m.group(1)), pulisci(m.group(2))]
    m = re.search(r"\b(?:a|presso)\s+((?:Svincolo|Allacciamento|Area di servizio|Barriera|Incrocio|Diramazione).+)$", t)
    return [pulisci(m.group(1)), None] if m else [None, None]
def coord(nome):
    if nome in luoghi: return luoghi[nome]
    q = urllib.parse.urlencode({"q": nome, "format": "json", "limit": 1, "countrycodes": "it,ch,fr", "viewbox": "5.5,46.8,9.6,44.0", "bounded": 1})
    try:
        r = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + q, headers={"User-Agent": "traffico-genova-ginevra/1.0 (GitHub Actions)"})
        j = json.loads(urllib.request.urlopen(r, timeout=20).read())
        luoghi[nome] = [float(j[0]["lat"]), float(j[0]["lon"])] if j else None
    except Exception:
        return None
    time.sleep(1.1)
    return luoghi[nome]
if os.environ.get("GEOCODE") == "1":
    import math
    for e in out:
        a, b = luoghi_di(e["testo"])
        ca = coord(a) if a else None
        cb = coord(b) if b else None
        if ca: e["lat"], e["lon"], e["da"] = ca[0], ca[1], a
        if cb: e["lat2"], e["lon2"], e["a"] = cb[0], cb[1], b
        if ca and cb:
            k = math.pi / 180
            d = 6371 * math.acos(min(1, math.sin(ca[0]*k)*math.sin(cb[0]*k) + math.cos(ca[0]*k)*math.cos(cb[0]*k)*math.cos((cb[1]-ca[1])*k)))
            e["km"] = round(d * 1.2, 1)
    json.dump(luoghi, open(CACHE, "w"), ensure_ascii=False, indent=0)
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
json.dump({"aggiornato": now, "fonte": "CCISS (feed ufficiale)", "eventi": out}, sys.stdout, ensure_ascii=False, indent=1)
