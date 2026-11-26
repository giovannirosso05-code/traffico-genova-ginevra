"""Legge il feed CCISS (tutta Italia) e salva gli eventi con le coordinate, per il sito."""
import json, re, sys, os, time, math, html, hashlib, datetime, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

UA = {"User-Agent": "traffico-genova-ginevra/1.0 (GitHub Actions)"}
CACHE = "traffico/sito/luoghi.json"
luoghi = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

def tipo(t):
    t = t.lower()
    for k, v in [("chius", "chiusura"), ("incidente", "incidente"), ("lavori", "lavori"), ("cantier", "lavori"),
                 ("coda", "code"), ("code", "code"), ("rallent", "code"), ("neve", "meteo"), ("catene", "meteo"),
                 ("nebbia", "meteo"), ("pioggia", "meteo"), ("vento", "meteo")]:
        if k in t: return v
    return "altro"

def pulisci(n):
    n = re.sub(r"^\d[\d,.]*\s*k?m\s+(?:prima|dopo)\s+(?:di\s+)?", "", (n or "").strip())
    n = re.sub(r"^(Svincolo|Allacciamento|Area di servizio|Barriera|Incrocio|Uscita|Entrata|Diramazione|Diram\.)\s+", "", n, flags=re.I)
    n = re.sub(r"^(Entrata|Uscita|Diramazione|Diram\.)\s+", "", n, flags=re.I)
    n = re.sub(r"\s+(Est|Ovest|Nord|Sud|Centro)$", "", n).strip(" -/.")
    if re.match(r"^(A|SS|SP|RA|T)\s?\d+\b", n): return None
    return n or None

def luoghi_di(testo):
    t = re.split(r"\s+(?:in direzione|provenendo)\s+", testo)[0]
    m = re.search(r"\btra\s+(.+?)\s+e\s+(.+)$", t)
    if m: return pulisci(m.group(1)), pulisci(m.group(2))
    m = re.search(r"\b(?:a|presso)\s+((?:Svincolo|Allacciamento|Area di servizio|Barriera|Incrocio|Diram).+)$", t)
    return (pulisci(m.group(1)), None) if m else (None, None)

def cerca(q, box=None):
    key = q + ("|" + ",".join(f"{x:.1f}" for x in box) if box else "")
    if key in luoghi: return luoghi[key]
    par = {"q": q, "format": "json", "limit": 1, "countrycodes": "it"}
    if box: par.update(viewbox=f"{box[0]},{box[1]},{box[2]},{box[3]}", bounded=1)
    try:
        r = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(par), headers=UA)
        j = json.loads(urllib.request.urlopen(r, timeout=20).read())
        luoghi[key] = [float(j[0]["lat"]), float(j[0]["lon"])] if j else None
    except Exception:
        return None
    time.sleep(1.1)
    return luoghi[key]

def box_strada(titolo):
    """Riquadro attorno alle città che danno il nome alla strada (es. 'A26 Genova-Gravellona Toce')."""
    nomi = re.sub(r"^\S+\s+", "", titolo).replace("Diramazione", "").split("-")
    pts = [c for c in (cerca(n.strip()) for n in nomi if len(n.strip()) > 2) if c]
    if not pts: return None
    la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    return [min(lo) - .35, max(la) + .35, max(lo) + .35, min(la) - .35]

def km(a, b):
    k = math.pi / 180
    return 6371 * math.acos(min(1, math.sin(a[0]*k)*math.sin(b[0]*k) + math.cos(a[0]*k)*math.cos(b[0]*k)*math.cos((b[1]-a[1])*k)))

req = urllib.request.Request("https://www.cciss.it/rss", headers={"User-Agent": "Mozilla/5.0"})
root = ET.fromstring(urllib.request.urlopen(req, timeout=30).read())
out = []
for it in root.iter("item"):
    title = (it.findtext("title") or "").strip()
    desc = re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))
    desc = re.sub(r"\(Fonte:[^)]*\)", "", re.sub(r"\s+", " ", desc)).strip()
    testo = desc[len(title):].strip() if desc.startswith(title) else desc
    e = {"id": hashlib.sha1((title + testo).encode()).hexdigest()[:16], "strada": title, "testo": testo,
         "tipo": tipo(testo), "quando": it.findtext("{http://purl.org/dc/elements/1.1/}date") or ""}
    if os.environ.get("GEOCODE") == "1":
        a, b = luoghi_di(testo)
        box = box_strada(title) if (a or b) else None
        ca = cerca(a, box) if a else None
        cb = cerca(b, box) if b else None
        if ca: e.update(lat=ca[0], lon=ca[1], da=a)
        if cb: e.update(lat2=cb[0], lon2=cb[1], a=b)
        if ca and cb: e["km"] = round(km(ca, cb) * 1.2, 1)
        m = re.search(r"\bin direzione\s+(.+?)(?:\s+provenendo|\s*<|$)", testo)
        if m and (ca or cb):
            dn = re.sub(r"^(A|SS|RA|T)\s?\d+\s*", "", m.group(1)).split("-")[-1].strip(" .")
            dn = re.sub(r"\b(Voltri|Centro|Nord|Sud|Est|Ovest)$", "", dn).strip() or dn
            cd = cerca(dn) if len(dn) > 2 else None
            if cd: e.update(dirlat=cd[0], dirlon=cd[1], dir=dn)
    out.append(e)
fonti = {"Italia": f"ok ({len(out)} eventi)"}
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estero
for nome, fn in [("Francia", estero.francia), ("Svizzera", estero.svizzera)]:
    try:
        ev = fn()
        if ev is None:
            fonti[nome] = "non attiva (manca la chiave)"
        else:
            out.extend(ev); fonti[nome] = f"ok ({len(ev)} eventi)"
    except Exception as ex:
        dett = ""
        if hasattr(ex, "code"):
            try: corpo = ex.read().decode("utf-8", "replace")
            except Exception: corpo = ""
            corpo = re.sub(r"<[^>]+>", " ", corpo)
            dett = f" {ex.code} {re.sub(chr(92)+'s+', ' ', corpo)[:160].strip()}"
        fonti[nome] = f"errore: {type(ex).__name__}{dett}"
        print(f"{nome}: {ex}", file=sys.stderr)
if os.environ.get("GEOCODE") == "1":
    json.dump(luoghi, open(CACHE, "w"), ensure_ascii=False, indent=0)
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
json.dump({"aggiornato": now, "fonte": "CCISS, Bison Futé, opentransportdata.swiss", "fonti": fonti, "eventi": out}, sys.stdout, ensure_ascii=False, indent=1)
