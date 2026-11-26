"""Autovelox fissi da OpenStreetMap (Italia, Francia, Svizzera), aggiornati una volta a settimana.

Scrive traffico/sito/velox.json: lista di [lat, lon, limite] (limite 0 se non indicato).
"""
import json, os, time, urllib.request, urllib.parse

FILE = "traffico/sito/velox.json"
QUERY = """[out:json][timeout:300];
(area["ISO3166-1"="IT"][admin_level=2];area["ISO3166-1"="FR"][admin_level=2];area["ISO3166-1"="CH"][admin_level=2];)->.p;
node["highway"="speed_camera"](area.p);
out;"""
SERVER = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]


def limite(t):
    v = (t.get("maxspeed") or "").split()[0] if t.get("maxspeed") else ""
    return int(v) if v.isdigit() else 0


def aggiorna():
    if os.path.exists(FILE) and time.time() - os.path.getmtime(FILE) < 7 * 86400:
        return "già aggiornato"
    for srv in SERVER:
        try:
            r = urllib.request.Request(srv, data=urllib.parse.urlencode({"data": QUERY}).encode(),
                                       headers={"User-Agent": "traffico-genova-ginevra/1.0 (GitHub Actions)"})
            j = json.loads(urllib.request.urlopen(r, timeout=320).read())
            out = [[round(e["lat"], 5), round(e["lon"], 5), limite(e.get("tags", {}))]
                   for e in j.get("elements", []) if "lat" in e]
            if len(out) > 1000:
                json.dump(out, open(FILE, "w"), separators=(",", ":"))
                return f"{len(out)} velox"
        except Exception as ex:
            print(f"velox {srv}: {ex}")
    return "non aggiornato"


if __name__ == "__main__":
    print(aggiorna())
