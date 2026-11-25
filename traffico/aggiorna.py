"""Legge il feed CCISS e produce JSON con gli eventi sul corridoio Genova-Ginevra."""
import json, re, sys, html, urllib.request, datetime, hashlib, xml.etree.ElementTree as ET
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
now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")
json.dump({"aggiornato": now, "fonte": "CCISS (feed ufficiale)", "eventi": out}, sys.stdout, ensure_ascii=False, indent=1)
