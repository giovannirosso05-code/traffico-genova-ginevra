"""Storico per la previsione: per ogni coda, incidente o chiusura salvo dove era e per quanto è durata.

- sito/storico.json         conteggio degli eventi per tipo a ogni giro (come prima)
- sito/storico_eventi.json  un record per evento: posizione, direzione, prima e ultima volta che l'ho visto
Tengo gli ultimi 90 giorni. Il sito usa questo file per capire a che ore, di solito, ci sono code sul tuo percorso.
"""
import json, os, collections, datetime

d = json.load(open("traffico/sito/dati.json"))
adesso = d["aggiornato"]

p = "traffico/sito/storico.json"
s = json.load(open(p)) if os.path.exists(p) else []
s.append({"t": adesso, "n": dict(collections.Counter(e["tipo"] for e in d["eventi"]))})
json.dump(s[-96 * 30:], open(p, "w"), separators=(",", ":"))

p = "traffico/sito/storico_eventi.json"
st = json.load(open(p)) if os.path.exists(p) else {}
for e in d["eventi"]:
    if e.get("tipo") not in ("code", "incidente", "chiusura") or "lat" not in e:
        continue
    if e.get("tipo") == "chiusura" and "dalle" in e.get("testo", "") and "alle" in e.get("testo", ""):
        continue        # le chiusure programmate hanno già l'orario: non servono per imparare le abitudini
    r = st.get(e["id"])
    if r:
        r["f"] = adesso
    else:
        st[e["id"]] = {k: e[k] for k in ("tipo", "strada", "lat", "lon", "lat2", "lon2", "dirlat", "dirlon", "da", "a", "indicativo") if k in e}
        st[e["id"]].update(i=adesso, f=adesso)
limite = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).isoformat()
st = {k: v for k, v in st.items() if v["f"] >= limite}
json.dump(st, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
print(len(st), "eventi nello storico")
