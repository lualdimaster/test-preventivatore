# Come pubblicare questo configuratore per testarlo (da Chromebook, senza terminale)

Tutto dal browser, in due parti: 1) caricare i file su GitHub, 2) pubblicarli su
Streamlit Community Cloud (gratuito).

⚠️ **Prima di iniziare — leggi questo**: questo configuratore usa un database
SQLite **locale** dentro l'app (`data/lualdi.db`), non Turso come il gestionale
magazzino. Su Streamlit Cloud i dati **non sono permanenti**: se modifichi
qualcosa da Admin (prezzi, materiali, PIN rivenditori...) e poi l'app si riavvia
o viene aggiornata, quelle modifiche si perdono e torna ai dati di partenza
inclusi in questo pacchetto. Va benissimo per **testare che tutto funzioni**,
ma non usarlo ancora per lavoro vero — prima lo migriamo su Turso, come
abbiamo già fatto per il gestionale.

---

## Parte 1 — Crea un repository GitHub per questo progetto

1. Vai su [github.com](https://github.com) ed effettua l'accesso (stesso
   account usato per `magazzino-lualdi`).
2. In alto a destra clicca **+** → **New repository**.
3. Nome repository, ad esempio: `lualdi-configuratore`.
4. Seleziona **Private**.
5. NON spuntare "Add a README file" (i file li carichiamo noi).
6. Clicca **Create repository**.

## Parte 2 — Carica i file

1. Nella pagina del nuovo repository vuoto, clicca il link **"uploading an
   existing file"** (oppure vai su **Add file → Upload files**).
2. Trascina dentro **tutti i file e le cartelle** che trovi in questo pacchetto:
   - `app.py`
   - `database.py`
   - `importa_dati.py`
   - `requirements.txt`
   - `README.md`
   - la cartella `data/` (con dentro `lualdi.db`)
   - la cartella `.streamlit/` (con dentro `config.toml`)
   - `AVVIA.bat` e `avvia.sh` (facoltativi, servono solo per un eventuale uso
     futuro in locale su PC/Mac — non servono per la pubblicazione online)

   Nota: alcuni browser non trascinano bene le cartelle intere. Se `data/` o
   `.streamlit/` non si caricano, apri quella cartella sul tuo Chromebook e
   trascina il singolo file al suo interno (es. `data/lualdi.db`) — GitHub
   ricrea la cartella da solo in base al percorso del file.
3. In basso, scrivi un messaggio tipo "Primo caricamento" e clicca
   **Commit changes**.

## Parte 3 — Pubblica su Streamlit Community Cloud

1. Vai su [share.streamlit.io](https://share.streamlit.io).
2. Accedi con lo stesso account GitHub (autorizza l'accesso se richiesto).
3. Clicca **New app** (o **Create app**).
4. Seleziona:
   - **Repository**: `<tuonome>/lualdi-configuratore`
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. (Facoltativo ma consigliato) In **Advanced settings**, imposta una App URL
   personalizzata a tua scelta.
6. Clicca **Deploy**. Il primo avvio richiede uno o due minuti.

## Parte 4 — Rendila privata (consigliato, dati anche solo di test)

Dalle impostazioni dell'app su Streamlit Cloud (icona ⚙️ in basso a destra
mentre l'app è aperta, o dal pannello "Manage app"):
- **Sharing** → invita solo il tuo indirizzo email, così l'app non è
  raggiungibile da chiunque abbia il link.

---

## Cosa provare una volta online

1. **Home** → **Configuratore**: percorri tutti i passi (categoria →
   materiale → colore → spessore → eventuali opzioni stampa → dimensioni →
   quantità) e controlla che il prezzo calcolato in fondo abbia senso.
2. Nel configuratore, prova **"🔑 Accesso rivenditore"** con PIN `0000` e
   verifica che il listino cambi (prezzo rivenditore invece di pubblico).
3. Vai su **Admin** (password default `lualdi2024`) e dai un'occhiata alle
   varie schede: Categorie, Materiali, Colori, Prodotti, Stampa, Rivenditori,
   Storico, Import/Export, Impostazioni.
4. Segnami qualsiasi cosa che si comporta in modo strano, con il passo
   preciso in cui l'hai notato.
