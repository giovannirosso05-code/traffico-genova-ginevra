"""Cantieri di Autostrade per l'Italia: gli stessi dati della pagina "cantieri previsti" del loro sito.

Due file pubblici usati dal loro sito (viabilita.autostrade.it/json/):
- cantieri_imm.json: cantieri di oggi e della notte (spesso notturni 20:00-05:00)
- cantieri.json: cantieri lunghi e programmati nelle prossime settimane
Ogni cantiere ha coordinate vere del tratto, inizio e fine previsti e il tipo di restringimento.
"""
import json, datetime, urllib.request
from zoneinfo import ZoneInfo
ROMA = ZoneInfo("Europe/Rome")

BASE = "https://viabilita.autostrade.it/json/"
UA = {"User-Agent": "Mozilla/5.0 (traffico-genova-ginevra)", "Referer": "https://viabilita.autostrade.it/"}


def scarica(nome):
    with urllib.request.urlopen(urllib.request.Request(BASE + nome + ".json", headers=UA), timeout=40) as r:
        return json.load(r)


def iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat(timespec="minutes") if ms else None


def strada(c):
    # "A07" -> "A7"
    return "A" + c[1:].lstrip("0") if c and c[0] == "A" and c[1:].isdigit() else (c or "")


def cantieri(cerca=None, dati=None):
    """Restituisce gli eventi nel formato del sito. `cerca` trova le coordinate di una città (per la direzione)."""
    adesso = datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000
    visti, out = set(), []
    for nome in ("cantieri", "cantieri_imm"):  # prima la versione della loro pagina "cantieri previsti"
        lista = dati[nome] if dati else scarica(nome)
        for c in lista:
            idc = c.get("n_prg_can")
            if idc in visti: continue
            visti.add(idc)
            fine = c.get("d_ora_rmz_pre")
            if fine and fine < adesso: continue
            inizio = c.get("d_ora_nst_pre") or c.get("d_ora_nst")
            path = [p for p in (c.get("geoPath") or []) if p.get("LAT") and p.get("LON")]
            if path:
                lat, lon, lat2, lon2 = path[0]["LAT"], path[0]["LON"], path[-1]["LAT"], path[-1]["LON"]
            elif c.get("n_lat"):
                lat, lon, lat2, lon2 = c["n_lat"], c["n_lon"], None, None
            else:
                continue
            s = strada(c.get("c_str"))
            nome_str = (c.get("t_des_str") or "").strip().title()
            dirn = (c.get("t_des_dir") or "").strip()
            tratto = (c.get("t_des") or c.get("t_des_trt") or "").strip()
            sgn = (c.get("t_des_sgn") or "").strip()
            lav = (c.get("t_des_lav") or "").strip().lower()
            vel = c.get("n_vel_max")
            def ora(ms):
                return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).astimezone(ROMA).strftime(
                    "%d/%m" + ("/%Y" if abs(ms - adesso) > 150 * 864e5 else "") + " %H:%M") if ms else "?"
            ki, kf = c.get("n_prg_km_ini"), c.get("n_prg_km_fin")
            kmtxt = f" (dal km {ki} al km {kf})" if isinstance(ki, (int, float)) and isinstance(kf, (int, float)) and ki != kf else ""
            testo = f"cantiere tra {tratto.title()}{kmtxt} in direzione {dirn.title()}: {sgn.lower()}" + \
                    (f" ({lav})" if lav else "") + (f", limite {vel} km/h" if vel else "") + \
                    f" · dal {ora(inizio)} al {ora(fine)}"
            e = {"id": f"aspi{idc}", "strada": f"{s} {nome_str} (Autostrade)".replace("  ", " "), "testo": testo,
                 "tipo": "lavori", "inizio": iso(inizio), "fine": iso(fine), "corsie": sgn.lower() or None,
                 "lat": lat, "lon": lon, "da": tratto.title(), "paese": "Italia", "fonte": "Autostrade per l'Italia",
                 "url": "https://www.autostrade.it/it/infoviabilita/cantieri-previsti"}
            if lat2 is not None and (abs(lat2 - lat) + abs(lon2 - lon)) > 1e-4:
                e.update(lat2=lat2, lon2=lon2)
            km_ = [c.get("n_prg_km_ini"), c.get("n_prg_km_fin")]
            if all(isinstance(x, (int, float)) for x in km_) and km_[0] != km_[1]:
                e["km"] = round(abs(km_[0] - km_[1]), 1)
            if cerca and dirn and not dirn.upper().startswith("AUTOSTRADA"):
                cd = cerca(dirn.title() + ", Italia")
                if cd: e.update(dirlat=cd[0], dirlon=cd[1], dir=dirn.title())
            out.append(e)
    return out


if __name__ == "__main__":
    ev = cantieri()
    print(len(ev)); print(json.dumps(ev[:2], ensure_ascii=False, indent=1))
