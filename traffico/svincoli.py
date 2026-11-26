"""Elenco di svincoli, caselli e aree di servizio italiani da OpenStreetMap (Overpass), aggiornato una volta a settimana.

Serve a mettere i puntini sullo svincolo vero invece che al centro del paese con lo stesso nome.
"""
import json, os, re, time, math, unicodedata, urllib.request, urllib.parse

FILE = "traffico/svincoli.json"
QUERY = """[out:json][timeout:300];
area["ISO3166-1"="IT"][admin_level=2]->.it;
(node["highway"="motorway_junction"](area.it);
 node["barrier"="toll_booth"](area.it);
 node["highway"="services"](area.it); way["highway"="services"](area.it);
 node["highway"="rest_area"](area.it); way["highway"="rest_area"](area.it););
out center tags;"""
SERVER = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
VUOTE = {"svincolo", "barriera", "casello", "allacciamento", "uscita", "entrata", "area", "di", "servizio", "del", "della",
         "dei", "diramazione", "diram", "stazione", "autostradale", "barriere", "pedaggio", "e", "d", "la", "il", "lo"}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(w for w in s.split() if w not in VUOTE)

def carica():
    if os.path.exists(FILE) and time.time() - os.path.getmtime(FILE) < 7 * 86400:
        return json.load(open(FILE))
    for srv in SERVER:
        try:
            r = urllib.request.Request(srv, data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                       headers={"User-Agent": "traffico-genova-ginevra/1.0 (GitHub Actions)"})
            j = json.loads(urllib.request.urlopen(r, timeout=320).read())
            out = []
            for el in j.get("elements", []):
                t = el.get("tags", {})
                nome = t.get("name") or t.get("exit_to") or ""
                lat = el.get("lat") or (el.get("center") or {}).get("lat")
                lon = el.get("lon") or (el.get("center") or {}).get("lon")
                if nome and lat:
                    out.append({"n": nome, "k": norm(nome), "lat": round(lat, 5), "lon": round(lon, 5),
                                "t": t.get("highway") or t.get("barrier")})
            if len(out) > 500:
                json.dump(out, open(FILE, "w"), ensure_ascii=False, separators=(",", ":"))
                return out
        except Exception:
            continue
    return json.load(open(FILE)) if os.path.exists(FILE) else []

ELENCO = None
def trova(nome, box=None):
    """Svincolo/casello/area con lo stesso nome; se ce ne sono più d'uno, quello dentro (o più vicino a) il riquadro della strada."""
    global ELENCO
    if ELENCO is None: ELENCO = carica()
    k = norm(nome)
    if not k: return None
    cand = [s for s in ELENCO if s["k"] == k]
    if not cand:
        parole = set(k.split())
        cand = [s for s in ELENCO if parole <= set(s["k"].split()) and len(s["k"].split()) <= len(parole) + 2]
    if not cand: return None
    if box:
        cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
        dentro = [s for s in cand if box[0] <= s["lon"] <= box[2] and box[3] <= s["lat"] <= box[1]]
        cand = dentro or cand
        cand.sort(key=lambda s: (s["lon"] - cx) ** 2 + (s["lat"] - cy) ** 2)
    if not box and len({(round(s["lat"], 1), round(s["lon"], 1)) for s in cand}) > 1:
        return None                                   # stesso nome in posti diversi e nessun indizio: meglio niente
    pref = [s for s in cand if s["t"] == "motorway_junction"] or cand
    return [pref[0]["lat"], pref[0]["lon"], True]
