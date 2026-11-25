"""Prova temporanea: com'è fatto il sito traffico di Vinci e APRR."""
import json, re, html, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}
URL = ["https://www.vinci-autoroutes.com/fr/infos-travaux/", "https://voyage.aprr.fr/travaux-et-operations", "https://voyage.aprr.fr/travaux/previsions-travaux", "https://voyage.aprr.fr/information-trafic"]
rep = {}
for u in URL:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25); h = r.read().decode("utf-8", "replace"); st = r.status
    except Exception as e:
        h, st = "", getattr(e, "code", 0) or str(e)[:60]
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h))))
    rep[u] = {"stato": st, "len": len(h), "testo_len": len(t),
              "link": sorted(set(re.findall(r'href="([^"]*(?:trafic|chantier|travaux|fermeture|evenement|event)[^"]*)"', h, re.I)))[:25],
              "api": sorted(set(re.findall(r'["\']((?:https?:)?/[^"\']*(?:api|json|graphql|datex|ajax)[^"\']*)["\']', h, re.I)))[:25],
              "estratti": [t[max(0, m.start()-100):m.start()+220] for m in re.finditer(r"(?i)fermeture|coupure|ferm[ée]e|nuit|A\d{1,3}\b", t)][:4]}
json.dump(rep, open("traffico/sito/prova_siti.json", "w"), ensure_ascii=False, indent=1)
