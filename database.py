"""
╔══════════════════════════════════════════════════════╗
║   LUALDI — Database (Turso / SQLite)                  ║
║   Gestisce tutte le operazioni sul database           ║
╚══════════════════════════════════════════════════════╝

Il database vive su Turso (cloud, persistente — non si perde ai riavvii di
Streamlit Cloud). Se le credenziali Turso non sono configurate (nei Secrets
di Streamlit Cloud, o come variabili d'ambiente per un test in locale), si
usa un file SQLite locale come ripiego (utile solo per test: su Streamlit
Cloud senza Turso i dati si perderebbero ai riavvii, come già capitato al
gestionale magazzino prima della sua migrazione).

Stessa identica interfaccia pubblica (classe Database, stessi metodi) della
versione precedente basata su sqlite3 puro: app.py non ha bisogno di alcuna
modifica.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime

import libsql


# ══════════════════════════════════════════════════════════════
# CONNESSIONE (Turso con ripiego SQLite locale)
# ══════════════════════════════════════════════════════════════

def _credenziali_turso():
    """Legge URL e token Turso da Streamlit secrets (in produzione) o da
    variabili d'ambiente (test locali). Ritorna (url, token) o (None, None)
    se non configurate."""
    try:
        import streamlit as st
        if "TURSO_DATABASE_URL" in st.secrets:
            return st.secrets["TURSO_DATABASE_URL"], st.secrets.get("TURSO_AUTH_TOKEN", "")
    except Exception:
        pass
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    return (url, token) if url else (None, None)


class Row:
    """Riga con accesso sia per indice che per nome colonna (row['nome']),
    per restare compatibili con lo stile sqlite3.Row già usato in tutto il codice
    (in particolare con dict(row), usato ovunque in questo file)."""
    def __init__(self, columns, values):
        self._columns = columns
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._values[self._columns.index(key)]
        return self._values[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except (ValueError, IndexError):
            return default

    def keys(self):
        return self._columns

    def __iter__(self):
        return iter(self._values)

    def __repr__(self):
        return f"Row({dict(zip(self._columns, self._values))})"


class _CursorAdapter:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def _colonne(self):
        return [d[0] for d in self._cursor.description] if self._cursor.description else []

    def fetchone(self):
        r = self._cursor.fetchone()
        return None if r is None else Row(self._colonne(), r)

    def fetchall(self):
        cols = self._colonne()
        return [Row(cols, r) for r in self._cursor.fetchall()]


class _ConnectionAdapter:
    """Fa comportare la connessione libsql come una sqlite3.Connection,
    così il resto del file può restare quasi identico all'originale."""
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, sql, params=()):
        return _CursorAdapter(self._conn.execute(sql, params))

    def executescript(self, sql):
        self._conn.executescript(sql)

    def cursor(self):
        return _CursorAdapter(self._conn.cursor())

    def commit(self):
        self._conn.commit()
        # Le scritture vanno già dritte al database Turso in cloud con questo
        # commit (quindi sono già al sicuro). La sincronizzazione della
        # replica locale (per letture veloci) avviene a parte, con throttle,
        # NON qui — farla dopo ogni singolo commit sarebbe lentissimo con
        # tante operazioni ravvicinate (es. durante un import da JSON).

    def close(self):
        # Connessione condivisa e riutilizzata per tutta la vita del processo
        # (ogni riconnessione a Turso è un giro di rete) — non va chiusa qui.
        pass


_conn_condivisa = None
_REPLICA_PATH = Path(__file__).parent / "data" / "replica_locale.db"
_ultimo_sync = 0.0
_SYNC_INTERVALLO_SECONDI = 3.0
_db_path_fallback = "data/lualdi.db"


def _sync_se_necessario(raw_conn):
    """Sincronizza la replica locale con Turso al massimo ogni pochi secondi,
    invece che ad ogni singola query."""
    global _ultimo_sync
    if not hasattr(raw_conn, "sync"):
        return
    ora = time.time()
    if ora - _ultimo_sync > _SYNC_INTERVALLO_SECONDI:
        try:
            raw_conn.sync()
            _ultimo_sync = ora
        except Exception:
            pass


def get_connection():
    global _conn_condivisa
    if _conn_condivisa is None:
        url, token = _credenziali_turso()
        if url:
            # Modalità replica locale: letture veloci su file locale, scritture
            # dritte su Turso in cloud (quindi permanenti anche a riavvio).
            _REPLICA_PATH.parent.mkdir(parents=True, exist_ok=True)
            raw = libsql.connect(str(_REPLICA_PATH), sync_url=url, auth_token=token)
            try:
                raw.sync()
            except Exception:
                pass
        else:
            # Ripiego locale (solo per test senza Turso configurato): usa il
            # file passato al costruttore di Database (es. data/lualdi.db),
            # così un eventuale database già popolato in locale resta leggibile.
            Path(_db_path_fallback).parent.mkdir(parents=True, exist_ok=True)
            raw = libsql.connect(database=_db_path_fallback)
        _conn_condivisa = _ConnectionAdapter(raw)
    else:
        _sync_se_necessario(_conn_condivisa._conn)
    return _conn_condivisa


class Database:
    def __init__(self, db_path: str = "data/lualdi.db"):
        global _db_path_fallback
        _db_path_fallback = db_path
        self._init_db()

    def _conn(self):
        return get_connection()

    def _init_db(self):
        c = self._conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS categorie (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                colore TEXT DEFAULT '#888888',
                ordine INTEGER DEFAULT 0,
                attivo INTEGER DEFAULT 1,
                sconto_rivenditore REAL DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS materiali (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                cat_id TEXT REFERENCES categorie(id),
                ordine INTEGER DEFAULT 0,
                attivo INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS colori (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                codice TEXT DEFAULT '#cccccc',
                mat_id TEXT REFERENCES materiali(id),
                ordine INTEGER DEFAULT 0,
                attivo INTEGER DEFAULT 1
            )
        """)
        c.execute("""
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
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS stampa (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                descrizione TEXT DEFAULT '',
                add_mq_pub REAL DEFAULT 0,
                add_mq_rev REAL DEFAULT 0,
                noprint INTEGER DEFAULT 0,
                attivo INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS stampa_bianco (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                descrizione TEXT DEFAULT '',
                add_mq_pub REAL DEFAULT 0,
                add_mq_rev REAL DEFAULT 0,
                attivo INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tipologia_stampa (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                descrizione TEXT DEFAULT '',
                add_mq_pub REAL DEFAULT 0,
                add_mq_rev REAL DEFAULT 0,
                attivo INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS rivenditori (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                pin TEXT NOT NULL,
                attivo INTEGER DEFAULT 1
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS storico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                descrizione TEXT NOT NULL,
                tipo TEXT DEFAULT 'save',
                utente TEXT DEFAULT 'admin'
            )
        """)
        c.commit()

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _parse_prodotto(self, row: dict) -> dict:
        for f in ['stampa_ids', 'tipologia_ids', 'bianco_ids', 'cnc_ids', 'finitura_ids', 'optional_ids']:
            row[f] = json.loads(row.get(f) or '[]')
        return row

    def _serialize_lista(self, v):
        if isinstance(v, list):
            return json.dumps(v)
        if v is None:
            return '[]'
        return v

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{int(time.time() * 1000)}"

    # ══════════════════════════════════════════════
    # CATEGORIE
    # ══════════════════════════════════════════════
    def get_categorie(self, solo_attive=True) -> list:
        c = self._conn()
        q = "SELECT * FROM categorie"
        if solo_attive:
            q += " WHERE attivo=1"
        q += " ORDER BY ordine"
        return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_categoria(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('cat')
        c = self._conn()
        c.execute("""
            INSERT INTO categorie (id,nome,colore,ordine,attivo,sconto_rivenditore)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, colore=excluded.colore,
                ordine=excluded.ordine, attivo=excluded.attivo,
                sconto_rivenditore=excluded.sconto_rivenditore
        """, (d['id'], d['nome'], d.get('colore', '#888888'), d.get('ordine', 0),
              d.get('attivo', 1), d.get('sconto_rivenditore', 0)))
        c.commit()
        return d['id']

    def delete_categoria(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM categorie WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # MATERIALI
    # ══════════════════════════════════════════════
    def get_materiali(self, cat_id=None, solo_attivi=True) -> list:
        c = self._conn()
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
        c = self._conn()
        c.execute("""
            INSERT INTO materiali (id,nome,cat_id,ordine,attivo)
            VALUES (?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, cat_id=excluded.cat_id,
                ordine=excluded.ordine, attivo=excluded.attivo
        """, (d['id'], d['nome'], d.get('cat_id'), d.get('ordine', 0), d.get('attivo', 1)))
        c.commit()
        return d['id']

    def delete_materiale(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM materiali WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # COLORI
    # ══════════════════════════════════════════════
    def get_colori(self, mat_id=None, solo_attivi=True) -> list:
        c = self._conn()
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
        c = self._conn()
        c.execute("""
            INSERT INTO colori (id,nome,codice,mat_id,ordine,attivo)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, codice=excluded.codice,
                mat_id=excluded.mat_id, ordine=excluded.ordine, attivo=excluded.attivo
        """, (d['id'], d['nome'], d.get('codice', '#cccccc'), d.get('mat_id'),
              d.get('ordine', 0), d.get('attivo', 1)))
        c.commit()
        return d['id']

    def delete_colore(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM colori WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # PRODOTTI
    # ══════════════════════════════════════════════
    def get_prodotti(self, colore_id=None, solo_attivi=True) -> list:
        c = self._conn()
        params, conds = [], ["1=1"]
        if solo_attivi:
            conds.append("attivo=1")
        if colore_id:
            conds.append("colore_id=?")
            params.append(colore_id)
        q = (f"SELECT * FROM prodotti WHERE {' AND '.join(conds)} "
             f"ORDER BY colore_id, CAST(REPLACE(spessore,'mm','') AS REAL)")
        return [self._parse_prodotto(dict(r)) for r in c.execute(q, params).fetchall()]

    def get_prodotto(self, id: str):
        c = self._conn()
        r = c.execute("SELECT * FROM prodotti WHERE id=?", (id,)).fetchone()
        return self._parse_prodotto(dict(r)) if r else None

    def upsert_prodotto(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('pr')
        c = self._conn()
        c.execute("""
            INSERT INTO prodotti
                (id,colore_id,spessore,prezzo_mq_pub,prezzo_mq_rev,
                 stampa_ids,tipologia_ids,bianco_ids,cnc_ids,finitura_ids,optional_ids,
                 supporta_stampa,supporta_cnc,attivo)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                colore_id=excluded.colore_id, spessore=excluded.spessore,
                prezzo_mq_pub=excluded.prezzo_mq_pub, prezzo_mq_rev=excluded.prezzo_mq_rev,
                stampa_ids=excluded.stampa_ids, tipologia_ids=excluded.tipologia_ids,
                bianco_ids=excluded.bianco_ids, cnc_ids=excluded.cnc_ids,
                finitura_ids=excluded.finitura_ids, optional_ids=excluded.optional_ids,
                supporta_stampa=excluded.supporta_stampa, supporta_cnc=excluded.supporta_cnc,
                attivo=excluded.attivo
        """, (
            d['id'], d.get('colore_id'), d.get('spessore', ''),
            d.get('prezzo_mq_pub', 0), d.get('prezzo_mq_rev', 0),
            self._serialize_lista(d.get('stampa_ids')), self._serialize_lista(d.get('tipologia_ids')),
            self._serialize_lista(d.get('bianco_ids')), self._serialize_lista(d.get('cnc_ids')),
            self._serialize_lista(d.get('finitura_ids')), self._serialize_lista(d.get('optional_ids')),
            d.get('supporta_stampa', 1), d.get('supporta_cnc', 0), d.get('attivo', 1),
        ))
        c.commit()
        return d['id']

    def delete_prodotto(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM prodotti WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # STAMPA
    # ══════════════════════════════════════════════
    def get_stampa(self, solo_attiva=True) -> list:
        c = self._conn()
        q = "SELECT * FROM stampa"
        if solo_attiva:
            q += " WHERE attivo=1"
        return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_stampa(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('stampa')
        c = self._conn()
        c.execute("""
            INSERT INTO stampa (id,nome,descrizione,add_mq_pub,add_mq_rev,noprint,attivo)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, descrizione=excluded.descrizione,
                add_mq_pub=excluded.add_mq_pub, add_mq_rev=excluded.add_mq_rev,
                noprint=excluded.noprint, attivo=excluded.attivo
        """, (d['id'], d['nome'], d.get('descrizione', ''), d.get('add_mq_pub', 0),
              d.get('add_mq_rev', 0), d.get('noprint', 0), d.get('attivo', 1)))
        c.commit()
        return d['id']

    def delete_stampa(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM stampa WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # STAMPA BIANCO
    # ══════════════════════════════════════════════
    def get_stampa_bianco(self, solo_attiva=True) -> list:
        c = self._conn()
        q = "SELECT * FROM stampa_bianco"
        if solo_attiva:
            q += " WHERE attivo=1"
        return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_stampa_bianco(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('bianco')
        c = self._conn()
        c.execute("""
            INSERT INTO stampa_bianco (id,nome,descrizione,add_mq_pub,add_mq_rev,attivo)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, descrizione=excluded.descrizione,
                add_mq_pub=excluded.add_mq_pub, add_mq_rev=excluded.add_mq_rev,
                attivo=excluded.attivo
        """, (d['id'], d['nome'], d.get('descrizione', ''), d.get('add_mq_pub', 0),
              d.get('add_mq_rev', 0), d.get('attivo', 1)))
        c.commit()
        return d['id']

    def delete_stampa_bianco(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM stampa_bianco WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # TIPOLOGIA STAMPA
    # ══════════════════════════════════════════════
    def get_tipologia_stampa(self, solo_attiva=True) -> list:
        c = self._conn()
        q = "SELECT * FROM tipologia_stampa"
        if solo_attiva:
            q += " WHERE attivo=1"
        return [dict(r) for r in c.execute(q).fetchall()]

    def upsert_tipologia_stampa(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('tipologia')
        c = self._conn()
        c.execute("""
            INSERT INTO tipologia_stampa (id,nome,descrizione,add_mq_pub,add_mq_rev,attivo)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, descrizione=excluded.descrizione,
                add_mq_pub=excluded.add_mq_pub, add_mq_rev=excluded.add_mq_rev,
                attivo=excluded.attivo
        """, (d['id'], d['nome'], d.get('descrizione', ''), d.get('add_mq_pub', 0),
              d.get('add_mq_rev', 0), d.get('attivo', 1)))
        c.commit()
        return d['id']

    def delete_tipologia_stampa(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM tipologia_stampa WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # RIVENDITORI
    # ══════════════════════════════════════════════
    def get_rivenditori(self) -> list:
        c = self._conn()
        return [dict(r) for r in c.execute("SELECT * FROM rivenditori").fetchall()]

    def verifica_pin(self, pin: str):
        c = self._conn()
        r = c.execute(
            "SELECT * FROM rivenditori WHERE pin=? AND attivo=1", (str(pin).strip(),)
        ).fetchone()
        return dict(r) if r else None

    def upsert_rivenditore(self, d: dict):
        if not d.get('id'):
            d['id'] = self._new_id('r')
        c = self._conn()
        c.execute("""
            INSERT INTO rivenditori (id,nome,pin,attivo)
            VALUES (?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                nome=excluded.nome, pin=excluded.pin, attivo=excluded.attivo
        """, (d['id'], d['nome'], str(d.get('pin', '')), d.get('attivo', 1)))
        c.commit()
        return d['id']

    def delete_rivenditore(self, id: str):
        c = self._conn()
        c.execute("DELETE FROM rivenditori WHERE id=?", (id,))
        c.commit()

    # ══════════════════════════════════════════════
    # STORICO
    # ══════════════════════════════════════════════
    def log(self, descrizione: str, tipo: str = 'save', utente: str = 'admin'):
        c = self._conn()
        c.execute(
            "INSERT INTO storico (data,descrizione,tipo,utente) VALUES (?,?,?,?)",
            (datetime.now().strftime("%d/%m/%Y %H:%M:%S"), descrizione, tipo, utente)
        )
        c.commit()

    def get_storico(self, limit=100) -> list:
        c = self._conn()
        return [dict(r) for r in c.execute(
            "SELECT * FROM storico ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]

    def cancella_storico(self):
        c = self._conn()
        c.execute("DELETE FROM storico")
        c.commit()

    # ══════════════════════════════════════════════
    # STATISTICHE
    # ══════════════════════════════════════════════
    def stats(self) -> dict:
        c = self._conn()
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
        """Esporta tutto il database come JSON (compatibile con il vecchio formato).
        Usato sia per i backup manuali sia come metodo di migrazione verso Turso:
        esporta da qui mentre sei ancora su SQLite locale, poi Importa da JSON
        una volta collegato a Turso."""
        prodotti = self.get_prodotti(solo_attivi=False)
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

    def import_json(self, data: dict):
        """Importa dati dal formato JSON (export_json, o il vecchio formato del
        configuratore HTML). Restituisce (n_importati, errori)."""
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
                'sconto_rivenditore': x.get('scontoRivenditore', x.get('sconto_rivenditore', 0)),
            }), f"Categoria {x.get('nome')}")

        for x in data.get('materiali', []):
            safe(lambda x=x: self.upsert_materiale({
                'id': x['id'], 'nome': x['nome'],
                'cat_id': x.get('cat', x.get('cat_id', '')),
                'ordine': x.get('ordine', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Materiale {x.get('nome')}")

        for x in data.get('colori', []):
            safe(lambda x=x: self.upsert_colore({
                'id': x['id'], 'nome': x['nome'],
                'codice': x.get('codice', '#cccccc'),
                'mat_id': x.get('mat', x.get('mat_id', '')),
                'ordine': x.get('ordine', 0),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Colore {x.get('nome')}")

        for x in data.get('prodotti', []):
            safe(lambda x=x: self.upsert_prodotto({
                'id': x['id'], 'colore_id': x.get('colore', x.get('colore_id', '')),
                'spessore': x.get('spessore', ''),
                'prezzo_mq_pub': x.get('prezzoMqPub', x.get('prezzo_mq_pub', 0)),
                'prezzo_mq_rev': x.get('prezzoMqRev', x.get('prezzo_mq_rev', 0)),
                'stampa_ids': x.get('stampaIds', x.get('stampa_ids', [])),
                'tipologia_ids': x.get('tipologiaIds', x.get('tipologia_ids', [])),
                'bianco_ids': x.get('biancIds', x.get('bianco_ids', [])),
                'cnc_ids': x.get('cncIds', x.get('cnc_ids', [])),
                'finitura_ids': x.get('finitureIds', x.get('finitura_ids', [])),
                'optional_ids': x.get('optionalIds', x.get('optional_ids', [])),
                'supporta_stampa': 1 if x.get('supportaStampa', True) else 0,
                'supporta_cnc': 1 if x.get('supportaCNC', False) else 0,
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Prodotto {x.get('spessore')}")

        for x in data.get('stampa', []):
            safe(lambda x=x: self.upsert_stampa({
                'id': x['id'], 'nome': x['nome'],
                'descrizione': x.get('desc', x.get('descrizione', '')),
                'add_mq_pub': x.get('addMqPub', x.get('add_mq_pub', 0)),
                'add_mq_rev': x.get('addMqRev', x.get('add_mq_rev', 0)),
                'noprint': 1 if x.get('noprint', False) else 0,
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Stampa {x.get('nome')}")

        for x in data.get('stampaBianco', []):
            safe(lambda x=x: self.upsert_stampa_bianco({
                'id': x['id'], 'nome': x['nome'],
                'descrizione': x.get('desc', x.get('descrizione', '')),
                'add_mq_pub': x.get('addMqPub', x.get('add_mq_pub', 0)),
                'add_mq_rev': x.get('addMqRev', x.get('add_mq_rev', 0)),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Bianco {x.get('nome')}")

        for x in data.get('tipologiaStampa', []):
            safe(lambda x=x: self.upsert_tipologia_stampa({
                'id': x['id'], 'nome': x['nome'],
                'descrizione': x.get('desc', x.get('descrizione', '')),
                'add_mq_pub': x.get('addMqPub', x.get('add_mq_pub', 0)),
                'add_mq_rev': x.get('addMqRev', x.get('add_mq_rev', 0)),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Tipologia {x.get('nome')}")

        for x in data.get('rivenditori', []):
            safe(lambda x=x: self.upsert_rivenditore({
                'id': x['id'], 'nome': x['nome'],
                'pin': str(x.get('pin', '')),
                'attivo': 1 if x.get('attivo', True) else 0,
            }), f"Rivenditore {x.get('nome')}")

        return n, errori
