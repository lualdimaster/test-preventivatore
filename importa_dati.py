"""
Script di migrazione: importa il file JSON esistente (lualdi_database.json)
nel nuovo database SQLite.

Uso:
    python importa_dati.py
    oppure
    python importa_dati.py percorso/al/file.json
"""
import json
import sys
from pathlib import Path

# Aggiunge la cartella corrente al path
sys.path.insert(0, str(Path(__file__).parent))
from database import Database

def importa(json_path: str = None):
    # Cerca il file JSON
    if json_path:
        p = Path(json_path)
    else:
        # Cerca nella cartella corrente e in quella superiore
        candidati = [
            Path("lualdi_database.json"),
            Path("../lualdi_database.json"),
            Path("data/config.json"),
            Path("../configuratore e admin lualdi/data/config.json"),
        ]
        p = next((c for c in candidati if c.exists()), None)
        if not p:
            print("❌ File JSON non trovato.")
            print("   Specifica il percorso: python importa_dati.py mio_file.json")
            return

    print(f"📂 File trovato: {p.resolve()}")

    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"❌ Errore lettura file: {e}")
        return

    # Stampa anteprima
    print(f"\n📊 Anteprima dati:")
    print(f"   Categorie:        {len(data.get('categorie', []))}")
    print(f"   Materiali:        {len(data.get('materiali', []))}")
    print(f"   Colori:           {len(data.get('colori', []))}")
    print(f"   Prodotti:         {len(data.get('prodotti', []))}")
    print(f"   Stampa:           {len(data.get('stampa', []))}")
    print(f"   Stampa bianco:    {len(data.get('stampaBianco', []))}")
    print(f"   Tipologia stampa: {len(data.get('tipologiaStampa', []))}")
    print(f"   Rivenditori:      {len(data.get('rivenditori', []))}")

    print("\n🔄 Importazione in corso...")
    db = Database("data/lualdi.db")
    n, errori = db.import_json(data)
    db.log(f"Migrazione da JSON: {n} elementi importati", "import", "sistema")

    print(f"\n✅ Importati {n} elementi con successo!")
    if errori:
        print(f"⚠️  {len(errori)} errori:")
        for e in errori:
            print(f"   - {e}")

    # Verifica finale
    s = db.stats()
    print(f"\n📋 Database finale:")
    print(f"   Categorie:   {s['categorie']}")
    print(f"   Materiali:   {s['materiali']}")
    print(f"   Colori:      {s['colori']}")
    print(f"   Prodotti:    {s['prodotti']}")
    print(f"   Rivenditori: {s['rivenditori']}")
    print(f"\n🗄️  Database salvato in: {Path('data/lualdi.db').resolve()}")
    print("\n🚀 Ora puoi avviare l'app con: streamlit run app.py")


if __name__ == "__main__":
    json_arg = sys.argv[1] if len(sys.argv) > 1 else None
    importa(json_arg)
