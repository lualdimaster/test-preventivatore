"""
╔══════════════════════════════════════════════════════╗
║   LUALDI — Database SQLite                           ║
║   Gestisce tutte le operazioni sul database          ║
╚══════════════════════════════════════════════════════╝
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


class Database:
    def __init__(self, db_path: str = "data/lualdi.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init_db(self):
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS categorie (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    colore TEXT DEFAULT '#888888',
                    ordine INTEGER DEFAULT 0,
                    attivo INTEGER DEFAULT 1,
                    sconto_rivenditore REAL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS materiali (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    cat_id TEXT REFERENCES categorie(id),
                    ordine INTEGER DEFAULT 0,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS colori (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    codice TEXT DEFAULT '#cccccc',
                    mat_id TEXT REFERENCES materiali(id),
                    ordine INTEGER DEFAULT 0,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS prodotti (
                    id TEXT PRIMARY KEY,
                    colore_id TEXT REFERENCES colori(id),
                    spessore TEXT NOT NULL,
                    prezzo_mq_pub REAL DEFAULT 0,
                    prezzo_mq_rev REAL DEFAULT 0,
                    stampa_ids TEXT DEFAULT '[]',
                    tipologia_ids TEXT DEFAULT '[]',
                    bianco_ids TEXT DEFAULT '[]',
                    cnc_ids TEXT DEFAULT '[]',
                    finitura_ids TEXT DEFAULT '[]',
                    optional_ids TEXT DEFAULT '[]',
                    supporta_stampa INTEGER DEFAULT 1,
                    supporta_cnc INTEGER DEFAULT 0,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS stampa (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    descrizione TEXT DEFAULT '',
                    add_mq_pub REAL DEFAULT 0,
                    add_mq_rev REAL DEFAULT 0,
                    noprint INTEGER DEFAULT 0,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS stampa_bianco (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    descrizione TEXT DEFAULT '',
                    add_mq_pub REAL DEFAULT 0,
                    add_mq_rev REAL DEFAULT 0,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS tipologia_stampa (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    descrizione TEXT DEFAULT '',
                    add_mq_pub REAL DEFAULT 0,
                    add_mq_rev REAL DEFAULT 0,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS rivenditori (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    pin TEXT NOT NULL,
                    attivo INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS storico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT NOT NULL,
                    descrizione TEXT NOT NULL,
                    tipo TEXT DEFAULT 'save',
                    utente TEXT DEFAULT 'admin'
                );
            """)

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _parse_prodotto(self, row: dict) -> dict:
        for f in ['stampa_ids', 'tipologia_ids', 'bianco_ids', 'cnc_ids', 'finitura_ids', 'optional_ids']:
            row[f] = json.loads(row.get(f) or '[]')
        return row

    def _serialize_prodotto(self, d: dict) -> dict:
        dd = dict(d)
        for f in ['stampa_ids', 'tipologia_ids', 'bianco_ids', 'cnc_ids', 'finitura_ids', 'optional_ids']:
            if isinstance(dd.get(f), list):
                dd[f] = json.dumps(dd[f])
            elif dd.get(f) is None:
                dd[f] = '[]'
        return dd

    def _new_id(self, prefix: str) -> str:
        import time
        return f"{prefix}_{int(time.time() * 1000)}"

    # ══════════════════════════════════════════════
    # CATEGORIE
    # ══════════════════════════════════════════════
    def get_categorie(self, solo_attive=True) -> list:
        with self._conn() as c:
            q = "SELECT * FROM categorie"
            if solo_attive:
                q += " WHERE attivo=1"
            q += " ORDER BY ordine"
            return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_categoria(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('cat')
        with self._conn() as c:
            c.execute("""
                INSERT INTO categorie (id,nome,colore,ordine,attivo,sconto_rivenditore)
                VALUES (:id,:nome,:colore,:ordine,:attivo,:sconto_rivenditore)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, colore=excluded.colore,
                    ordine=excluded.ordine, attivo=excluded.attivo,
                    sconto_rivenditore=excluded.sconto_rivenditore
            """, d)
        return d['id']

    def delete_categoria(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM categorie WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # MATERIALI
    # ══════════════════════════════════════════════
    def get_materiali(self, cat_id=None, solo_attivi=True) -> list:
        with self._conn() as c:
            params, conds = [], ["1=1"]
            if solo_attivi:
                conds.append("attivo=1")
            if cat_id:
                conds.append("cat_id=?")
                params.append(cat_id)
            q = f"SELECT * FROM materiali WHERE {' AND '.join(conds)} ORDER BY ordine"
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def upsert_materiale(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('mat')
        with self._conn() as c:
            c.execute("""
                INSERT INTO materiali (id,nome,cat_id,ordine,attivo)
                VALUES (:id,:nome,:cat_id,:ordine,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, cat_id=excluded.cat_id,
                    ordine=excluded.ordine, attivo=excluded.attivo
            """, d)
        return d['id']

    def delete_materiale(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM materiali WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # COLORI
    # ══════════════════════════════════════════════
    def get_colori(self, mat_id=None, solo_attivi=True) -> list:
        with self._conn() as c:
            params, conds = [], ["1=1"]
            if solo_attivi:
                conds.append("attivo=1")
            if mat_id:
                conds.append("mat_id=?")
                params.append(mat_id)
            q = f"SELECT * FROM colori WHERE {' AND '.join(conds)} ORDER BY ordine"
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def upsert_colore(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('col')
        with self._conn() as c:
            c.execute("""
                INSERT INTO colori (id,nome,codice,mat_id,ordine,attivo)
                VALUES (:id,:nome,:codice,:mat_id,:ordine,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, codice=excluded.codice,
                    mat_id=excluded.mat_id, ordine=excluded.ordine, attivo=excluded.attivo
            """, d)
        return d['id']

    def delete_colore(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM colori WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # PRODOTTI
    # ══════════════════════════════════════════════
    def get_prodotti(self, colore_id=None, solo_attivi=True) -> list:
        with self._conn() as c:
            params, conds = [], ["1=1"]
            if solo_attivi:
                conds.append("attivo=1")
            if colore_id:
                conds.append("colore_id=?")
                params.append(colore_id)
            q = (f"SELECT * FROM prodotti WHERE {' AND '.join(conds)} "
                 f"ORDER BY colore_id, CAST(REPLACE(spessore,'mm','') AS REAL)")
            return [self._parse_prodotto(dict(r)) for r in c.execute(q, params).fetchall()]

    def get_prodotto(self, id: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT * FROM prodotti WHERE id=?", (id,)).fetchone()
            return self._parse_prodotto(dict(r)) if r else None

    def upsert_prodotto(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('pr')
        dd = self._serialize_prodotto(d)
        with self._conn() as c:
            c.execute("""
                INSERT INTO prodotti
                    (id,colore_id,spessore,prezzo_mq_pub,prezzo_mq_rev,
                     stampa_ids,tipologia_ids,bianco_ids,cnc_ids,finitura_ids,optional_ids,
                     supporta_stampa,supporta_cnc,attivo)
                VALUES
                    (:id,:colore_id,:spessore,:prezzo_mq_pub,:prezzo_mq_rev,
                     :stampa_ids,:tipologia_ids,:bianco_ids,:cnc_ids,:finitura_ids,:optional_ids,
                     :supporta_stampa,:supporta_cnc,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    colore_id=excluded.colore_id, spessore=excluded.spessore,
                    prezzo_mq_pub=excluded.prezzo_mq_pub, prezzo_mq_rev=excluded.prezzo_mq_rev,
                    stampa_ids=excluded.stampa_ids, tipologia_ids=excluded.tipologia_ids,
                    bianco_ids=excluded.bianco_ids, cnc_ids=excluded.cnc_ids,
                    finitura_ids=excluded.finitura_ids, optional_ids=excluded.optional_ids,
                    supporta_stampa=excluded.supporta_stampa, supporta_cnc=excluded.supporta_cnc,
                    attivo=excluded.attivo
            """, dd)
        return d['id']

    def delete_prodotto(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM prodotti WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # STAMPA
    # ══════════════════════════════════════════════
    def get_stampa(self, solo_attiva=True) -> list:
        with self._conn() as c:
            q = "SELECT * FROM stampa"
            if solo_attiva:
                q += " WHERE attivo=1"
            return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_stampa(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('stampa')
        with self._conn() as c:
            c.execute("""
                INSERT INTO stampa (id,nome,descrizione,add_mq_pub,add_mq_rev,noprint,attivo)
                VALUES (:id,:nome,:descrizione,:add_mq_pub,:add_mq_rev,:noprint,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, descrizione=excluded.descrizione,
                    add_mq_pub=excluded.add_mq_pub, add_mq_rev=excluded.add_mq_rev,
                    noprint=excluded.noprint, attivo=excluded.attivo
            """, d)
        return d['id']

    def delete_stampa(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM stampa WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # STAMPA BIANCO
    # ══════════════════════════════════════════════
    def get_stampa_bianco(self, solo_attiva=True) -> list:
        with self._conn() as c:
            q = "SELECT * FROM stampa_bianco"
            if solo_attiva:
                q += " WHERE attivo=1"
            return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_stampa_bianco(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('bianco')
        with self._conn() as c:
            c.execute("""
                INSERT INTO stampa_bianco (id,nome,descrizione,add_mq_pub,add_mq_rev,attivo)
                VALUES (:id,:nome,:descrizione,:add_mq_pub,:add_mq_rev,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, descrizione=excluded.descrizione,
                    add_mq_pub=excluded.add_mq_pub, add_mq_rev=excluded.add_mq_rev,
                    attivo=excluded.attivo
            """, d)
        return d['id']

    def delete_stampa_bianco(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM stampa_bianco WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # TIPOLOGIA STAMPA
    # ══════════════════════════════════════════════
    def get_tipologia_stampa(self, solo_attiva=True) -> list:
        with self._conn() as c:
            q = "SELECT * FROM tipologia_stampa"
            if solo_attiva:
                q += " WHERE attivo=1"
            return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_tipologia_stampa(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('tipologia')
        with self._conn() as c:
            c.execute("""
                INSERT INTO tipologia_stampa (id,nome,descrizione,add_mq_pub,add_mq_rev,attivo)
                VALUES (:id,:nome,:descrizione,:add_mq_pub,:add_mq_rev,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, descrizione=excluded.descrizione,
                    add_mq_pub=excluded.add_mq_pub, add_mq_rev=excluded.add_mq_rev,
                    attivo=excluded.attivo
            """, d)
        return d['id']

    def delete_tipologia_stampa(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM tipologia_stampa WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # RIVENDITORI
    # ══════════════════════════════════════════════
    def get_rivenditori(self) -> list:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT * FROM rivenditori").fetchall()]

    def verifica_pin(self, pin: str) -> dict | None:
        with self._conn() as c:
            r = c.execute(
                "SELECT * FROM rivenditori WHERE pin=? AND attivo=1", (str(pin).strip(),)
            ).fetchone()
            return dict(r) if r else None

    def upsert_rivenditore(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('r')
        with self._conn() as c:
            c.execute("""
                INSERT INTO rivenditori (id,nome,pin,attivo)
                VALUES (:id,:nome,:pin,:attivo)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome, pin=excluded.pin, attivo=excluded.attivo
            """, d)
        return d['id']

    def delete_rivenditore(self, id: str):
        with self._conn() as c:
            c.execute("DELETE FROM rivenditori WHERE id=?", (id,))

    # ══════════════════════════════════════════════
    # STORICO
    # ══════════════════════════════════════════════
    def log(self, descrizione: str, tipo: str = 'save', utente: str = 'admin'):
        with self._conn() as c:
            c.execute(
                "INSERT INTO storico (data,descrizione,tipo,utente) VALUES (?,?,?,?)",
                (datetime.now().strftime("%d/%m/%Y %H:%M:%S"), descrizione, tipo, utente)
            )

    def get_storico(self, limit=100) -> list:
        with self._conn() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM storico ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()]

    def cancella_storico(self):
        with self._conn() as c:
            c.execute("DELETE FROM storico")

    # ══════════════════════════════════════════════
    # STATISTICHE
    # ══════════════════════════════════════════════
    def stats(self) -> dict:
        with self._conn() as c:
            return {
                'categorie': c.execute("SELECT COUNT(*) FROM categorie WHERE attivo=1").fetchone()[0],
                'materiali': c.execute("SELECT COUNT(*) FROM materiali WHERE attivo=1").fetchone()[0],
                'colori': c.execute("SELECT COUNT(*) FROM colori WHERE attivo=1").fetchone()[0],
                'prodotti': c.execute("SELECT COUNT(*) FROM prodotti WHERE attivo=1").fetchone()[0],
                'rivenditori': c.execute("SELECT COUNT(*) FROM rivenditori WHERE attivo=1").fetchone()[0],
                'storico': c.execute("SELECT COUNT(*) FROM storico").fetchone()[0],
            }

    # ══════════════════════════════════════════════
    # EXPORT / IMPORT JSON
    # ══════════════════════════════════════════════
    def export_json(self) -> dict:
        """Esporta tutto il database come JSON (compatibile con il vecchio formato)."""
        prodotti = self.get_prodotti(solo_attivi=False)
        # Converti chiavi al vecchio formato per compatibilità
        prodotti_exp = []
        for p in prodotti:
            prodotti_exp.append({
                'id': p['id'], 'colore': p['colore_id'], 'spessore': p['spessore'],
                'prezzoMqPub': p['prezzo_mq_pub'], 'prezzoMqRev': p['prezzo_mq_rev'],
                'stampaIds': p['stampa_ids'], 'tipologiaIds': p['tipologia_ids'],
                'biancIds': p['bianco_ids'], 'cncIds': p['cnc_ids'],
                'finitureIds': p['finitura_ids'], 'optionalIds': p['optional_ids'],
                'supportaStampa': bool(p['supporta_stampa']),
                'supportaCNC': bool(p['supporta_cnc']), 'attivo': bool(p['attivo']),
            })
        return {
            'categorie': self.get_categorie(solo_attive=False),
            'materiali': self.get_materiali(solo_attivi=False),
            'colori': self.get_colori(solo_attivi=False),
            'prodotti': prodotti_exp,
            'stampa': self.get_stampa(solo_attiva=False),
            'stampaBianco': self.get_stampa_bianco(solo_attiva=False),
            'tipologiaStampa': self.get_tipologia_stampa(solo_attiva=False),
            'rivenditori': self.get_rivenditori(),
        }

    def import_json(self, data: dict) -> tuple[int, list]:
        """Importa dati dal vecchio formato JSON. Restituisce (n_importati, errori)."""
        n, errori = 0, []

        def safe(fn, label):
            nonlocal n
            try:
                fn()
                n += 1
            except Exception as e:
                errori.append(f"{label}: {e}")

        for x in data.get('categorie', []):
            safe(lambda x=x: self.upsert_categoria({
                'id': x['id'], 'nome': x['nome'],
                'colore': x.get('colore', '#888888'),
                'ordine': x.get('ordine', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
                'sconto_rivenditore': x.get('scontoRivenditore', 0),
            }), f"Categoria {x.get('nome')}")

        for x in data.get('materiali', []):
            safe(lambda x=x: self.upsert_materiale({
                'id': x['id'], 'nome': x['nome'],
                'cat_id': x.get('cat', ''),
                'ordine': x.get('ordine', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Materiale {x.get('nome')}")

        for x in data.get('colori', []):
            safe(lambda x=x: self.upsert_colore({
                'id': x['id'], 'nome': x['nome'],
                'codice': x.get('codice', '#cccccc'),
                'mat_id': x.get('mat', ''),
                'ordine': x.get('ordine', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Colore {x.get('nome')}")

        for x in data.get('prodotti', []):
            safe(lambda x=x: self.upsert_prodotto({
                'id': x['id'], 'colore_id': x.get('colore', ''),
                'spessore': x.get('spessore', ''),
                'prezzo_mq_pub': x.get('prezzoMqPub', 0),
                'prezzo_mq_rev': x.get('prezzoMqRev', 0),
                'stampa_ids': x.get('stampaIds', []),
                'tipologia_ids': x.get('tipologiaIds', []),
                'bianco_ids': x.get('biancIds', []),
                'cnc_ids': x.get('cncIds', []),
                'finitura_ids': x.get('finitureIds', []),
                'optional_ids': x.get('optionalIds', []),
                'supporta_stampa': 1 if x.get('supportaStampa', True) else 0,
                'supporta_cnc': 1 if x.get('supportaCNC', False) else 0,
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Prodotto {x.get('spessore')}")

        for x in data.get('stampa', []):
            safe(lambda x=x: self.upsert_stampa({
                'id': x['id'], 'nome': x['nome'],
                'descrizione': x.get('desc', ''),
                'add_mq_pub': x.get('addMqPub', 0),
                'add_mq_rev': x.get('addMqRev', 0),
                'noprint': 1 if x.get('noprint', False) else 0,
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Stampa {x.get('nome')}")

        for x in data.get('stampaBianco', []):
            safe(lambda x=x: self.upsert_stampa_bianco({
                'id': x['id'], 'nome': x['nome'],
                'descrizione': x.get('desc', ''),
                'add_mq_pub': x.get('addMqPub', 0),
                'add_mq_rev': x.get('addMqRev', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Bianco {x.get('nome')}")

        for x in data.get('tipologiaStampa', []):
            safe(lambda x=x: self.upsert_tipologia_stampa({
                'id': x['id'], 'nome': x['nome'],
                'descrizione': x.get('desc', ''),
                'add_mq_pub': x.get('addMqPub', 0),
                'add_mq_rev': x.get('addMqRev', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Tipologia {x.get('nome')}")

        for x in data.get('rivenditori', []):
            safe(lambda x=x: self.upsert_rivenditore({
                'id': x['id'], 'nome': x['nome'],
                'pin': str(x.get('pin', '')),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Rivenditore {x.get('nome')}")

        return n, errori
