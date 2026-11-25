"""Legge le info traffico di ATMB (A40, A41 Nord, Traforo del Monte Bianco) e le salva in sito/atmb.json."""
import json, re, html, sys, datetime, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}
CANDIDATI = ["https://www.atmb.com", "https://www.atmb.com/infos-trafic", "https://www.atmb.com/fr/infos-trafic",
             "https://www.atmb.com/trafic", "https://www.atmb.com/fr/trafic-en-temps-reel", "https://www.tunnelmb.net/fr",
             "https://www.tunnelmb.net/it", "https://www.tunnelmb.net/fr/info-trafic"]
def leggi(u):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
        return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:
        return getattr(e, "code", 0) or str(e)[:80], ""
def testo(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()
rapporto = {}
for u in CANDIDATI:
    st, h = leggi(u)
    t = testo(h)
    link = sorted(set(re.findall(r'href="([^"]*(?:trafic|traffic|travaux|chantier|fermeture|info)[^"]*)"', h, re.I)))[:40]
    idx = [m.start() for m in re.finditer(r"(?i)fermeture|travaux|chantier|circulation|basculement|alternat", t)][:6]
    rapporto[u] = {"stato": st, "lunghezza": len(h), "link": link, "estratti": [t[max(0, i-120):i+260] for i in idx],
                   "json_api": sorted(set(re.findall(r'["\'](/[^"\']*(?:api|json|ajax)[^"\']*)["\']', h)))[:20]}
json.dump({"aggiornato": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"), "debug": rapporto},
          open("traffico/sito/atmb_debug.json", "w"), ensure_ascii=False, indent=1)
