"""Legge le info traffico di ATMB (A40, A41 Nord, RN205, Traforo del Monte Bianco) e le salva in sito/atmb.json.

ATMB non pubblica dati aperti: leggo le sue pagine web. Se cambiano struttura, il file segnala l'errore
invece di dire "nessun problema".
"""
import json, re, os, sys, html, datetime, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from estero import traduci

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}
PAGINE = ["https://www.atmb.com", "https://www.atmb.com/info-trafic-a40-rn205/"]
OUT = "traffico/sito/atmb.json"

def leggi(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8", "replace")

def pulito(h):
    h = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()

def meta(h, nome):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(nome), h) or \
        re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="%s"' % re.escape(nome), h)
    return html.unescape(m.group(1)).strip() if m else ""

risultato = {"aggiornato": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes"),
             "fonte": "ATMB e APRR (siti ufficiali)", "stato": "ok", "tunnel": "", "eventi": []}
try:
    home = leggi(PAGINE[0])
    t = pulito(home)
    m = re.search(r"TUNNEL\s+(Le trafic est [^.]{3,40}?|Trafic [^.]{3,40}?|Circulation [^.]{3,60}?)\s+En savoir", t, re.I)
    if m: risultato["tunnel"] = traduci(m.group(1).replace("Le trafic est", "traffico"))
    link = set(re.findall(r'href="(https://www\.atmb\.com/atmb_event(?:_info)?/[^"]+)"', home))
    try:
        link |= set(re.findall(r'href="(https://www\.atmb\.com/atmb_event(?:_info)?/[^"]+)"', leggi(PAGINE[1])))
    except Exception:
        pass
    for u in sorted(link)[:15]:
        try:
            h = leggi(u)
        except Exception:
            continue
        titolo = meta(h, "og:title") or (re.search(r"(?is)<h1[^>]*>(.*?)</h1>", h) or [None, ""])[1]
        titolo = re.sub(r"\s*[-|–]\s*ATMB.*$", "", pulito(titolo or ""))
        descr = meta(h, "og:description") or meta(h, "description")
        if re.match(r"(?i)^ATMB\b", descr): descr = ""      # descrizione generica del sito, non dell'evento
        titolo_it, descr_it = traduci(titolo.replace("|", ",")), traduci(descr.replace("|", ","))
        testo = (titolo + " " + descr).lower()
        tipo = "chiusura" if re.search(r"fermeture|coupure|ferm[ée]|interruption", testo) else \
               "lavori" if re.search(r"travaux|chantier|r[ée]nov", testo) else "altro"
        risultato["eventi"].append({"titolo": titolo_it, "testo": descr_it if descr_it != titolo_it else "", "tipo": tipo, "url": u, "gestore": "ATMB"})
    # --- APRR / AREA: elenco dei lavori programmati (A40 Mâcon–Ginevra, A41, A43, A6, A39…) ---
    try:
        visti = set()
        for pg in range(8):
            h = leggi(f"https://voyage.aprr.fr/travaux/previsions-travaux?page={pg}")
            card = re.findall(r'aprr-news-card__footer-title"><a href="(/[^"]+)">(.*?)</a>', h, re.S)
            nuovi = [(u, t) for u, t in card if u not in visti]
            if not nuovi: break
            oggi = datetime.date.today()
            for u, t in nuovi:
                visti.add(u)
                t = pulito(t)
                date = [(int(d), int(mm)) for d, mm in re.findall(r"\b(\d{1,2})/(\d{1,2})\b", t) if 1 <= int(mm) <= 12 and 1 <= int(d) <= 31]
                if date:
                    d, mm = date[-1]
                    try:
                        fine = datetime.date(oggi.year, mm, d)
                        if fine < oggi and (oggi - fine).days < 200:
                            continue                      # lavoro già finito
                    except ValueError:
                        pass
                desc = ""
                if len(visti) <= 40:
                    try: desc = meta(leggi("https://voyage.aprr.fr" + u), "og:description") or ""
                    except Exception: pass
                blob = (t + " " + desc).lower()
                tipo = "chiusura" if re.search(r"fermeture|ferm[ée]|coupure|interdit", blob) else "lavori"
                risultato["eventi"].append({"titolo": traduci(t.replace(" - ", " · ")), "testo": traduci(desc)[:300] if desc else "",
                                            "tipo": tipo, "url": "https://voyage.aprr.fr" + u, "gestore": "APRR"})
        risultato["aprr"] = f"ok ({len(visti)} lavori)"
    except Exception as e:
        risultato["aprr"] = f"errore: {type(e).__name__}"
    if not risultato["eventi"] and not risultato["tunnel"]:
        risultato["stato"] = "nessun dato riconosciuto: forse il sito ATMB è cambiato"
except Exception as e:
    risultato["stato"] = f"errore nella lettura: {type(e).__name__}"
json.dump(risultato, open(OUT, "w"), ensure_ascii=False, indent=1)
print(risultato["stato"], len(risultato["eventi"]), "eventi ATMB", file=sys.stderr)
