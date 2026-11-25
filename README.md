# Traffico Genova–Ginevra

- `sito/` è il sito statico (GitHub Pages): legge `dati.json` e `storico.json`.
- `aggiorna.py` legge il feed ufficiale CCISS e scrive gli eventi del corridoio.
- `storico.py` accumula i conteggi per costruire lo storico delle settimane.
- `.github/workflows/traffico.yml` esegue tutto ogni ora e pubblica il sito.

Per attivarlo: repository pubblico, poi Settings → Pages → Source: "GitHub Actions".
Notifiche sul telefono (facoltative): app ntfy, iscriviti a un nome segreto e mettilo
in Settings → Secrets and variables → Actions → Variables come `NTFY_TOPIC`.
