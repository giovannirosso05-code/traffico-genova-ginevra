# Strada Libera – cosa fare (aggiornato 25/11/2026 sera)

Sito: https://giovannirosso05-code.github.io/traffico-genova-ginevra/

## Stato delle fonti

| Fonte | Stato | Cosa copre |
|---|---|---|
| CCISS (Italia) | ✅ funziona | ~100 eventi alla volta, tutte le autostrade e strade principali italiane; ~80% con puntino sulla mappa |
| Bison Futé (Francia) | ✅ funziona | ~460 eventi, strade statali e autostrade gratuite, con coordinate precise |
| ATMB (Francia, a pagamento) | ✅ funziona (lettura del sito) | A40 Ginevra–Chamonix, A41 Nord, RN205, Traforo Monte Bianco: solo nel riquadro, niente puntini |
| APRR / AREA (Francia, a pagamento) | ✅ funziona (lettura del sito) | ~18 lavori programmati (A40 Mâcon–Ginevra, A41, A43, A6…): solo nel riquadro |
| Vinci Autoroutes (Francia) | ❌ non leggibile | il sito carica i dati con codice: solo link |
| Svizzera (opentransportdata.swiss) | ⏳ chiave salvata 26/11, accesso in attesa di approvazione (errore 403) | codice mai provato con dati veri |

## Da fare – Giovanni

1. ~~Chiave Svizzera~~ ✅ salvata 26/11. **Ora**: aspettare l'approvazione di "traffic situations" (sparisce "Pending access" su api-manager.opentransportdata.swiss), poi scrivere a Claude per controllare.
   Vecchie istruzioni: registrarsi gratis su https://opentransportdata.swiss → creare una chiave per "Traffic Situations".
   Poi GitHub → https://github.com/giovannirosso05-code/traffico-genova-ginevra/settings/secrets/actions
   → New repository secret → Name `OTD_TOKEN` → incollare la chiave. NON incollarla in chat.
2. **Posizione sul telefono**: Impostazioni → App → Safari (o Chrome) → Posizione → Consenti/Chiedi;
   Privacy e sicurezza → Localizzazione → Siti web Safari → Mentre usi l'app. Aprire il sito in Safari, non da WhatsApp.
3. **Provare dal telefono** e mandare screenshot di cosa non va:
   - suggerimenti mentre scrivi (es. "San siro" → Stadio San Siro) – mai provato col servizio vero
   - tasto Calcola con un percorso vero (es. Genova → Ginevra) – mai provato col servizio vero
   - puntini sulla mappa: tocco → problema, tratto, lunghezza, carreggiata
4. ~~Eliminare vecchio portale Claude~~ ✅ fatto 26/11.

## Da fare – Claude, appena c'è la chiave o un riscontro

- Provare e sistemare la lettura Svizzera.
- Correggere ciò che non va dagli screenshot.

## Cose da migliorare (in ordine di utilità)

1. ~~Puntini per ATMB/APRR~~ ✅ fatto 26/11 (posizione dai luoghi nel titolo; se c'è solo la direzione è indicativa).
2. **Notifiche sul telefono** (ntfy) quando c'è una chiusura sul percorso salvato: già pronte, basta la variabile `NTFY_TOPIC`.
3. ~~Eventi sul percorso più precisi~~ ✅ fatto 26/11 (entro 1,5 km, esclusa la carreggiata opposta quando la fonte indica la direzione).
4. ~~Traduzione francese~~ ✅ ampliata 26/11 (~70 parole in più); mandare screenshot delle frasi ancora strane.
5. **Tempi con traffico**: oggi i tempi sono "senza traffico"; il tempo reale resta su Google Maps.
6. **Vinci Autoroutes**: servirebbe un browser simulato su GitHub; fragile, da fare solo se serve davvero.
7. **Nome dell'indirizzo**: il sito si chiama ancora `traffico-genova-ginevra`; si può rinominare il repository (cambia il link).
