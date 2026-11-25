import json, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Accept-Language": "fr-FR,fr;q=0.9"}
out = {}
h = urllib.request.urlopen(urllib.request.Request("https://voyage.aprr.fr/travaux/previsions-travaux", headers=UA), timeout=25).read().decode("utf-8", "replace")
i = h.find("A40 - Ain")
out["aprr_html"] = h[max(0, i-2500):i+2500]
out["aprr_pager"] = re.findall(r'href="([^"]*page=\d+[^"]*)"', h)[:10]
v = urllib.request.urlopen(urllib.request.Request("https://www.vinci-autoroutes.com/fr/infos-travaux/", headers=UA), timeout=25).read().decode("utf-8", "replace")
out["vinci_link"] = sorted(set(re.findall(r'href="([^"]*(?:autoroute-a|/a\d)[^"]*)"', v, re.I)))[:30]
json.dump(out, open("traffico/sito/prova_siti.json", "w"), ensure_ascii=False, indent=1)
