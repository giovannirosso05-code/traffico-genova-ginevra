"""Aggiunge al file storico il conteggio eventi per tipo di questo giro (max 60 giorni)."""
import json, os, collections
p = "traffico/sito/storico.json"
s = json.load(open(p)) if os.path.exists(p) else []
d = json.load(open("traffico/sito/dati.json"))
s.append({"t": d["aggiornato"], "n": dict(collections.Counter(e["tipo"] for e in d["eventi"]))})
json.dump(s[-24 * 60:], open(p, "w"), separators=(",", ":"))
