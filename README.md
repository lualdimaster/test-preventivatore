# Lualdi Industria Grafica — Configuratore Preventivi (Python)

Sistema completamente riscritto in **Python puro** con Streamlit.  
Il database è un file SQLite reale sul tuo PC: niente più browser, niente più localStorage.

---

## 📁 Struttura file

```
lualdi_configuratore/
│
├── app.py              ← Applicazione principale (tutto qui)
├── database.py         ← Gestione database SQLite
├── importa_dati.py     ← Migrazione dal vecchio JSON
├── requirements.txt    ← Dipendenze Python (solo streamlit)
├── AVVIA.bat           ← Avvio rapido Windows (doppio clic)
├── avvia.sh            ← Avvio rapido Mac/Linux
│
└── data/               ← Creata automaticamente
    ├── lualdi.db       ← DATABASE SQLITE (questo è il tuo database!)
    └── admin_config.json ← Password admin
```

---

## 🚀 Prima installazione

### Prerequisiti
- **Python 3.8+** → https://www.python.org/downloads/
  - Windows: spunta ✅ "Add Python to PATH" durante installazione

### Avvio Windows
Fai doppio clic su **`AVVIA.bat`** → installa tutto automaticamente e apre il browser.

### Avvio Mac/Linux
```bash
chmod +x avvia.sh
./avvia.sh
```

### Avvio manuale
```bash
pip install streamlit
streamlit run app.py
```

Poi apri il browser su **http://localhost:8501**

---

## 📥 Migrazione dati (prima volta)

Se hai un file JSON dal vecchio configuratore HTML:

```bash
python importa_dati.py lualdi_database.json
```

Oppure dall'Admin → scheda **Import / Export** → carica il JSON.

---

## 💾 Dove sono i dati?

In `data/lualdi.db` — un file SQLite.  
Per fare **backup**: copia questo file in una cartella sicura.  
Per **ripristinare**: sostituisci il file.  
Per **esportare in JSON**: Admin → Import/Export → Esporta.

---

## 🔐 Accesso Admin

URL: http://localhost:8501 → bottone "Admin"  
Password default: **`lualdi2024`**  
Cambiala da Admin → Impostazioni → Cambia password

---

## 🌐 Pubblicazione online (futuro)

Per pubblicare su server web (clienti accedono da Internet):
1. Usa **Streamlit Cloud** (gratuito) → https://streamlit.io/cloud
2. Oppure **Railway**, **Render**, o qualsiasi VPS con Python
3. Il codice non cambia nulla — solo il file `data/lualdi.db` va sul server

---

## ❓ Risoluzione problemi

**"streamlit: comando non trovato"**  
→ `pip install streamlit` poi riprova

**"Porta 8501 già in uso"**  
→ `streamlit run app.py --server.port 8502`

**"Database vuoto dopo avvio"**  
→ Vai Admin → Import/Export → carica il tuo JSON

---

*Lualdi Industria Grafica — Configuratore v2.0 Python*
