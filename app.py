"""
╔══════════════════════════════════════════════════════════════╗
║   LUALDI INDUSTRIA GRAFICA — Configuratore Preventivi        ║
║   Applicazione Python pura con Streamlit                     ║
║   Avvia con:  streamlit run app.py                           ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import json
import time
from datetime import datetime
from pathlib import Path
from database import Database

# ══════════════════════════════════════════════════════════════
# CONFIGURAZIONE PAGINA
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Lualdi — Configuratore Preventivi",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS personalizzato ────────────────────────────────────────
st.markdown("""
<style>
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
  div[data-testid="stMetricValue"] { font-size: 2rem; }
  .stTabs [data-baseweb="tab-list"] { gap: 4px; }
  .stTabs [data-baseweb="tab"] { padding: 8px 20px; border-radius: 6px 6px 0 0; }
  /* Griglia step configuratore */
  .step-header {
    background: #1a1a1a; color: white; border-radius: 8px 8px 0 0;
    padding: 10px 16px; margin-bottom: 0;
    font-family: sans-serif; font-weight: 700; font-size: 15px;
    border-left: 4px solid #c8102e;
  }
  .step-body {
    background: white; border: 1px solid #ddd; border-radius: 0 0 8px 8px;
    padding: 16px; margin-bottom: 16px;
  }
  /* Box prezzo */
  .price-box {
    background: #1a1a1a; color: white; border-radius: 10px;
    padding: 20px; text-align: center;
  }
  .price-total { font-size: 2.5rem; font-weight: 900; color: #c8102e; }
  .price-label { color: #888; font-size: 0.82rem; letter-spacing: 0.05em; text-transform: uppercase; }
  .price-rev { color: #1a7a3c; font-size: 2rem; font-weight: 900; }
  /* Badge */
  .badge-pub { background: #dbeafe; color: #1e40af; padding: 3px 10px;
               border-radius: 100px; font-size: 0.78rem; font-weight: 700; display: inline-block; }
  .badge-rev { background: #e6f4eb; color: #1a7a3c; padding: 3px 10px;
               border-radius: 100px; font-size: 0.78rem; font-weight: 700; display: inline-block; }
  .badge-warn { background: #fff3cd; color: #856404; padding: 3px 10px;
                border-radius: 100px; font-size: 0.78rem; font-weight: 700; display: inline-block; }
  /* Header logo */
  .logo-header {
    background: #1a1a1a; color: white; padding: 14px 24px;
    border-bottom: 3px solid #c8102e; border-radius: 8px;
    display: flex; align-items: center; gap: 16px; margin-bottom: 20px;
  }
  .logo-badge {
    background: #c8102e; color: white; font-weight: 900; font-size: 18px;
    padding: 6px 14px; border-radius: 4px; letter-spacing: 0.04em;
  }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# DATABASE (singleton)
# ══════════════════════════════════════════════════════════════
@st.cache_resource
def get_db():
    return Database("data/lualdi.db")

db = get_db()

# ── Password admin (modificabile in data/admin_config.json) ───
ADMIN_CONFIG_FILE = Path("data/admin_config.json")

def get_admin_password() -> str:
    if ADMIN_CONFIG_FILE.exists():
        return json.loads(ADMIN_CONFIG_FILE.read_text()).get('password', 'lualdi2024')
    return 'lualdi2024'

def set_admin_password(pw: str):
    ADMIN_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_CONFIG_FILE.write_text(json.dumps({'password': pw}))

# ══════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════
def init_session():
    defaults = {
        'page': 'home',
        'admin_logged_in': False,
        # configuratore
        'cfg_step': 1,
        'cfg_cat_id': None,
        'cfg_mat_id': None,
        'cfg_col_id': None,
        'cfg_prod': None,
        'cfg_stampa_id': None,
        'cfg_bianco_id': None,
        'cfg_tipologia_id': None,
        'cfg_larghezza': 100.0,
        'cfg_altezza': 70.0,
        'cfg_qty': 1,
        'cfg_is_rev': False,
        'cfg_rev_nome': '',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ══════════════════════════════════════════════════════════════
# UTILITÀ
# ══════════════════════════════════════════════════════════════
def nav(page: str):
    st.session_state.page = page
    st.rerun()

def cfg_reset():
    for k in ['cfg_cat_id', 'cfg_mat_id', 'cfg_col_id', 'cfg_prod',
              'cfg_stampa_id', 'cfg_bianco_id', 'cfg_tipologia_id']:
        st.session_state[k] = None
    st.session_state.cfg_step = 1
    st.session_state.cfg_larghezza = 100.0
    st.session_state.cfg_altezza = 70.0
    st.session_state.cfg_qty = 1

def get_nome(lista: list, id: str, campo: str = 'nome') -> str:
    item = next((x for x in lista if x.get('id') == id), None)
    return item[campo] if item else id or '—'

def calcola_prezzo_dati() -> dict | None:
    prod = st.session_state.cfg_prod
    if not prod:
        return None
    is_rev = st.session_state.cfg_is_rev
    prezzo_mq = prod['prezzo_mq_rev'] if is_rev else prod['prezzo_mq_pub']

    if st.session_state.cfg_stampa_id:
        s = next((x for x in db.get_stampa() if x['id'] == st.session_state.cfg_stampa_id), None)
        if s:
            prezzo_mq += s['add_mq_rev'] if is_rev else s['add_mq_pub']

    if st.session_state.cfg_bianco_id:
        b = next((x for x in db.get_stampa_bianco() if x['id'] == st.session_state.cfg_bianco_id), None)
        if b:
            prezzo_mq += b['add_mq_rev'] if is_rev else b['add_mq_pub']

    if st.session_state.cfg_tipologia_id:
        t = next((x for x in db.get_tipologia_stampa() if x['id'] == st.session_state.cfg_tipologia_id), None)
        if t:
            prezzo_mq += t['add_mq_rev'] if is_rev else t['add_mq_pub']

    larg_m = st.session_state.cfg_larghezza / 100
    alt_m  = st.session_state.cfg_altezza  / 100
    sup_mq = larg_m * alt_m
    prezzo_pezzo = prezzo_mq * sup_mq
    prezzo_tot   = prezzo_pezzo * st.session_state.cfg_qty

    return {
        'prezzo_mq': prezzo_mq,
        'sup_mq': sup_mq,
        'prezzo_pezzo': prezzo_pezzo,
        'prezzo_tot': prezzo_tot,
    }

# ══════════════════════════════════════════════════════════════
# SIDEBAR PREVENTIVO (usata nel configuratore)
# ══════════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🧾 Preventivo in corso")
        is_rev = st.session_state.cfg_is_rev

        # ── Listino ─────────────────────────────────
        if is_rev:
            st.markdown(f'<span class="badge-rev">✅ Rivenditore: {st.session_state.cfg_rev_nome}</span>', unsafe_allow_html=True)
            if st.button("Cambia listino", key="rev_exit"):
                st.session_state.cfg_is_rev = False
                st.session_state.cfg_rev_nome = ''
                st.rerun()
        else:
            st.markdown('<span class="badge-pub">🔵 Listino Pubblico</span>', unsafe_allow_html=True)
            with st.expander("🔑 Accesso rivenditore"):
                pin = st.text_input("PIN rivenditore", type="password", key="pin_input")
                if st.button("Accedi", key="pin_accedi"):
                    rev = db.verifica_pin(pin)
                    if rev:
                        st.session_state.cfg_is_rev = True
                        st.session_state.cfg_rev_nome = rev['nome']
                        st.success(f"Benvenuto, {rev['nome']}!")
                        time.sleep(0.8)
                        st.rerun()
                    else:
                        st.error("PIN non riconosciuto")

        st.divider()

        # ── Selezioni ────────────────────────────────
        prod = st.session_state.cfg_prod
        if prod:
            colori    = db.get_colori(solo_attivi=False)
            materiali = db.get_materiali(solo_attivi=False)
            categorie = db.get_categorie(solo_attive=False)

            col_info = next((c for c in colori if c['id'] == st.session_state.cfg_col_id), None)
            mat_info = next((m for m in materiali if m['id'] == st.session_state.cfg_mat_id), None)
            cat_info = next((c for c in categorie if c['id'] == st.session_state.cfg_cat_id), None)

            st.markdown("**📋 Configurazione:**")
            if cat_info: st.caption(f"Categoria: {cat_info['nome']}")
            if mat_info: st.caption(f"Materiale: {mat_info['nome']}")
            if col_info: st.caption(f"Colore: {col_info['nome']}")
            st.caption(f"Spessore: {prod['spessore']}")

            if st.session_state.cfg_stampa_id:
                stampa = next((s for s in db.get_stampa() if s['id'] == st.session_state.cfg_stampa_id), None)
                if stampa: st.caption(f"Stampa: {stampa['nome']}")

            if st.session_state.cfg_bianco_id:
                bianco = next((b for b in db.get_stampa_bianco() if b['id'] == st.session_state.cfg_bianco_id), None)
                if bianco: st.caption(f"Bianco: {bianco['nome']}")

            if st.session_state.cfg_tipologia_id:
                tipo = next((t for t in db.get_tipologia_stampa() if t['id'] == st.session_state.cfg_tipologia_id), None)
                if tipo: st.caption(f"Tipologia: {tipo['nome']}")

            st.caption(f"Dimensioni: {st.session_state.cfg_larghezza:.0f} × {st.session_state.cfg_altezza:.0f} cm")
            st.caption(f"Quantità: {st.session_state.cfg_qty} pz")

            # ── Prezzo ──────────────────────────────
            p = calcola_prezzo_dati()
            if p and st.session_state.cfg_step >= 8:
                st.divider()
                col_cls = "price-rev" if is_rev else "price-total"
                st.markdown(f"""
                <div class="price-box">
                  <div class="price-label">€/m²</div>
                  <div style="font-size:1.3rem;font-weight:700;color:white">€ {p['prezzo_mq']:.2f}</div>
                  <div class="price-label" style="margin-top:8px">Superficie</div>
                  <div style="color:#aaa">{p['sup_mq']:.4f} m²</div>
                  <div class="price-label" style="margin-top:8px">Prezzo / pezzo</div>
                  <div style="color:white;font-weight:700">€ {p['prezzo_pezzo']:.2f}</div>
                  <div class="price-label" style="margin-top:10px">TOTALE ({st.session_state.cfg_qty} pz)</div>
                  <div class="{col_cls}">€ {p['prezzo_tot']:.2f}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Completa le selezioni per vedere il preventivo")

        st.divider()
        if st.button("🏠 Torna alla Home", use_container_width=True):
            cfg_reset()
            nav('home')

# ══════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════
def page_home():
    st.markdown("""
    <div class="logo-header">
      <span class="logo-badge">LUALDI</span>
      <div>
        <strong style="font-size:16px">Industria Grafica</strong><br>
        <span style="color:#888;font-size:12px;text-transform:uppercase;letter-spacing:.06em">
          Sistema Configuratore Preventivi
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats rapide
    s = db.stats()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Categorie",   s['categorie'])
    c2.metric("Materiali",   s['materiali'])
    c3.metric("Colori",      s['colori'])
    c4.metric("Prodotti",    s['prodotti'])
    c5.metric("Rivenditori", s['rivenditori'])

    st.divider()

    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("### 📋 Configuratore Clienti")
        st.write("Crea preventivi passo dopo passo scegliendo materiale, colore, spessore, stampa e dimensioni.")
        if st.button("▶  Apri Configuratore", type="primary", use_container_width=True):
            cfg_reset()
            nav('configuratore')

    with col2:
        st.markdown("### ⚙️ Pannello Amministrazione")
        st.write("Gestisci prodotti, prezzi, colori, categorie e rivenditori. Importa ed esporta i dati.")
        if st.button("🔐 Accedi all'Admin", use_container_width=True):
            nav('admin_login')

    # Avviso se database vuoto
    if s['prodotti'] == 0:
        st.warning(
            "⚠️ **Database vuoto!** Nessun prodotto trovato. "
            "Vai nell'**Admin → Importa JSON** per caricare i dati esistenti.",
            icon="⚠️"
        )

# ══════════════════════════════════════════════════════════════
# ADMIN LOGIN
# ══════════════════════════════════════════════════════════════
def page_admin_login():
    st.markdown("## 🔐 Accesso Amministrazione")
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pw = st.text_input("Password amministratore", type="password", key="admin_pw_input")
        if st.button("Accedi", type="primary", use_container_width=True):
            if pw == get_admin_password():
                st.session_state.admin_logged_in = True
                db.log("Accesso admin", "login")
                nav('admin')
            else:
                st.error("Password errata")
        st.divider()
        if st.button("← Torna alla Home", use_container_width=True):
            nav('home')

# ══════════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════════
def page_admin():
    if not st.session_state.admin_logged_in:
        nav('admin_login')
        return

    # Header
    col_h1, col_h2 = st.columns([6, 1])
    with col_h1:
        st.markdown("## ⚙️ Pannello Amministrazione")
    with col_h2:
        if st.button("🔓 Esci", use_container_width=True):
            st.session_state.admin_logged_in = False
            nav('home')

    tabs = st.tabs([
        "📊 Dashboard",
        "🗂️ Categorie",
        "🧱 Materiali",
        "🎨 Colori",
        "📦 Prodotti",
        "🖨️ Stampa",
        "👥 Rivenditori",
        "💾 Import / Export",
        "📋 Storico",
        "🔧 Impostazioni",
    ])

    with tabs[0]: admin_dashboard()
    with tabs[1]: admin_categorie()
    with tabs[2]: admin_materiali()
    with tabs[3]: admin_colori()
    with tabs[4]: admin_prodotti()
    with tabs[5]: admin_stampa()
    with tabs[6]: admin_rivenditori()
    with tabs[7]: admin_import_export()
    with tabs[8]: admin_storico()
    with tabs[9]: admin_impostazioni()


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
def admin_dashboard():
    st.subheader("📊 Riepilogo Database")
    s = db.stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Categorie attive",   s['categorie'])
    c1.metric("Materiali attivi",   s['materiali'])
    c2.metric("Colori attivi",      s['colori'])
    c2.metric("Prodotti attivi",    s['prodotti'])
    c3.metric("Rivenditori attivi", s['rivenditori'])
    c3.metric("Voci storico",       s['storico'])

    st.divider()
    st.subheader("Ultime 5 modifiche")
    storico = db.get_storico(5)
    if storico:
        for v in storico:
            icona = {"save": "💾", "login": "🔑", "delete": "🗑️", "import": "📥"}.get(v['tipo'], "📝")
            st.markdown(f"{icona} `{v['data']}` — **{v['utente']}** — {v['descrizione']}")
    else:
        st.info("Nessuna modifica registrata")


# ─────────────────────────────────────────────
# CATEGORIE
# ─────────────────────────────────────────────
def admin_categorie():
    st.subheader("🗂️ Categorie")
    categorie = db.get_categorie(solo_attive=False)

    if categorie:
        for cat in categorie:
            with st.expander(f"{'✅' if cat['attivo'] else '⬜'} {cat['nome']} — sconto rev: {cat['sconto_rivenditore']}%"):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                nuovo_nome  = col1.text_input("Nome", cat['nome'], key=f"cat_n_{cat['id']}")
                nuovo_sconto = col2.number_input("Sconto rev %", 0.0, 100.0, float(cat['sconto_rivenditore']), key=f"cat_s_{cat['id']}")
                nuovo_ord   = col3.number_input("Ordine", 0, 99, int(cat['ordine']), key=f"cat_o_{cat['id']}")
                nuovo_att   = col4.checkbox("Attivo", bool(cat['attivo']), key=f"cat_a_{cat['id']}")
                col_s, col_d = st.columns(2)
                if col_s.button("💾 Salva", key=f"cat_save_{cat['id']}"):
                    db.upsert_categoria({
                        'id': cat['id'], 'nome': nuovo_nome,
                        'colore': cat['colore'],
                        'ordine': nuovo_ord, 'attivo': 1 if nuovo_att else 0,
                        'sconto_rivenditore': nuovo_sconto,
                    })
                    db.log(f"Modificata categoria: {nuovo_nome}")
                    st.success("Salvato ✅")
                    st.rerun()
                if col_d.button("🗑️ Elimina", key=f"cat_del_{cat['id']}"):
                    db.delete_categoria(cat['id'])
                    db.log(f"Eliminata categoria: {cat['nome']}", "delete")
                    st.rerun()

    st.divider()
    st.subheader("➕ Nuova Categoria")
    with st.form("nuova_cat"):
        col1, col2, col3 = st.columns([3, 1, 1])
        nome_cat   = col1.text_input("Nome categoria")
        sconto_cat = col2.number_input("Sconto rivenditore %", 0.0, 100.0, 30.0)
        ordine_cat = col3.number_input("Ordine", 0, 99, len(categorie))
        if st.form_submit_button("➕ Aggiungi", type="primary"):
            if nome_cat.strip():
                db.upsert_categoria({
                    'id': None, 'nome': nome_cat.strip(),
                    'colore': '#888888',
                    'ordine': ordine_cat, 'attivo': 1,
                    'sconto_rivenditore': sconto_cat,
                })
                db.log(f"Aggiunta categoria: {nome_cat}")
                st.success("Categoria aggiunta!")
                st.rerun()
            else:
                st.error("Inserisci un nome")


# ─────────────────────────────────────────────
# MATERIALI
# ─────────────────────────────────────────────
def admin_materiali():
    st.subheader("🧱 Materiali")
    categorie = db.get_categorie(solo_attive=False)
    materiali = db.get_materiali(solo_attivi=False)

    cat_map = {c['id']: c['nome'] for c in categorie}
    cat_ids  = [c['id'] for c in categorie]
    cat_nomi = [c['nome'] for c in categorie]

    if materiali:
        for m in materiali:
            cat_nome = cat_map.get(m['cat_id'], '?')
            with st.expander(f"{'✅' if m['attivo'] else '⬜'} {m['nome']} [{cat_nome}]"):
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                nuovo_nome = col1.text_input("Nome", m['nome'], key=f"mat_n_{m['id']}")
                idx_cat = cat_ids.index(m['cat_id']) if m['cat_id'] in cat_ids else 0
                nuova_cat = col2.selectbox("Categoria", cat_nomi, index=idx_cat, key=f"mat_c_{m['id']}")
                nuovo_ord = col3.number_input("Ordine", 0, 99, int(m['ordine']), key=f"mat_o_{m['id']}")
                nuovo_att = col4.checkbox("Attivo", bool(m['attivo']), key=f"mat_a_{m['id']}")
                col_s, col_d = st.columns(2)
                if col_s.button("💾 Salva", key=f"mat_s_{m['id']}"):
                    cat_id_sel = cat_ids[cat_nomi.index(nuova_cat)]
                    db.upsert_materiale({
                        'id': m['id'], 'nome': nuovo_nome,
                        'cat_id': cat_id_sel,
                        'ordine': nuovo_ord, 'attivo': 1 if nuovo_att else 0,
                    })
                    db.log(f"Modificato materiale: {nuovo_nome}")
                    st.success("Salvato ✅")
                    st.rerun()
                if col_d.button("🗑️ Elimina", key=f"mat_d_{m['id']}"):
                    db.delete_materiale(m['id'])
                    db.log(f"Eliminato materiale: {m['nome']}", "delete")
                    st.rerun()

    st.divider()
    st.subheader("➕ Nuovo Materiale")
    with st.form("nuovo_mat"):
        col1, col2, col3 = st.columns([3, 2, 1])
        nome_m  = col1.text_input("Nome materiale")
        cat_sel = col2.selectbox("Categoria", cat_nomi)
        ord_m   = col3.number_input("Ordine", 0, 99, len(materiali))
        if st.form_submit_button("➕ Aggiungi", type="primary"):
            if nome_m.strip() and cat_nomi:
                cat_id_sel = cat_ids[cat_nomi.index(cat_sel)]
                db.upsert_materiale({
                    'id': None, 'nome': nome_m.strip(),
                    'cat_id': cat_id_sel,
                    'ordine': ord_m, 'attivo': 1,
                })
                db.log(f"Aggiunto materiale: {nome_m}")
                st.success("Materiale aggiunto!")
                st.rerun()
            else:
                st.error("Compila tutti i campi")


# ─────────────────────────────────────────────
# COLORI
# ─────────────────────────────────────────────
def admin_colori():
    st.subheader("🎨 Colori")
    materiali = db.get_materiali(solo_attivi=False)
    colori    = db.get_colori(solo_attivi=False)

    mat_map  = {m['id']: m['nome'] for m in materiali}
    mat_ids  = [m['id'] for m in materiali]
    mat_nomi = [m['nome'] for m in materiali]

    # Filtro per materiale
    filtro_mat = st.selectbox("Filtra per materiale", ["Tutti"] + mat_nomi, key="colori_filtro")
    if filtro_mat != "Tutti":
        mat_id_f = mat_ids[mat_nomi.index(filtro_mat)]
        colori_vis = [c for c in colori if c['mat_id'] == mat_id_f]
    else:
        colori_vis = colori

    if colori_vis:
        for col in colori_vis:
            mat_nome = mat_map.get(col['mat_id'], '?')
            with st.expander(f"{'✅' if col['attivo'] else '⬜'} {col['nome']} [{mat_nome}]"):
                c1, c2, c3, c4, c5 = st.columns([3, 2, 1, 1, 1])
                n_nome = c1.text_input("Nome", col['nome'], key=f"col_n_{col['id']}")
                idx_m = mat_ids.index(col['mat_id']) if col['mat_id'] in mat_ids else 0
                n_mat  = c2.selectbox("Materiale", mat_nomi, index=idx_m, key=f"col_m_{col['id']}")
                n_cod  = c3.color_picker("Colore", col['codice'], key=f"col_c_{col['id']}")
                n_ord  = c4.number_input("Ordine", 0, 99, int(col['ordine']), key=f"col_o_{col['id']}")
                n_att  = c5.checkbox("Attivo", bool(col['attivo']), key=f"col_a_{col['id']}")
                col_s, col_d = st.columns(2)
                if col_s.button("💾 Salva", key=f"col_s_{col['id']}"):
                    mat_id_sel = mat_ids[mat_nomi.index(n_mat)]
                    db.upsert_colore({
                        'id': col['id'], 'nome': n_nome,
                        'codice': n_cod, 'mat_id': mat_id_sel,
                        'ordine': n_ord, 'attivo': 1 if n_att else 0,
                    })
                    db.log(f"Modificato colore: {n_nome}")
                    st.success("Salvato ✅")
                    st.rerun()
                if col_d.button("🗑️ Elimina", key=f"col_d_{col['id']}"):
                    db.delete_colore(col['id'])
                    db.log(f"Eliminato colore: {col['nome']}", "delete")
                    st.rerun()
    else:
        st.info("Nessun colore trovato")

    st.divider()
    st.subheader("➕ Nuovo Colore")
    with st.form("nuovo_col"):
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        n_nome = c1.text_input("Nome colore")
        n_mat  = c2.selectbox("Materiale", mat_nomi)
        n_cod  = c3.color_picker("Campione", "#cccccc")
        n_ord  = c4.number_input("Ordine", 0, 99, len(colori))
        if st.form_submit_button("➕ Aggiungi", type="primary"):
            if n_nome.strip() and mat_nomi:
                mat_id_sel = mat_ids[mat_nomi.index(n_mat)]
                db.upsert_colore({
                    'id': None, 'nome': n_nome.strip(),
                    'codice': n_cod, 'mat_id': mat_id_sel,
                    'ordine': n_ord, 'attivo': 1,
                })
                db.log(f"Aggiunto colore: {n_nome}")
                st.success("Colore aggiunto!")
                st.rerun()
            else:
                st.error("Compila tutti i campi")


# ─────────────────────────────────────────────
# PRODOTTI (PREZZI)
# ─────────────────────────────────────────────
def admin_prodotti():
    st.subheader("📦 Prodotti e Prezzi")
    colori    = db.get_colori(solo_attivi=False)
    materiali = db.get_materiali(solo_attivi=False)
    prodotti  = db.get_prodotti(solo_attivi=False)
    all_stampa  = db.get_stampa(solo_attiva=False)
    all_bianco  = db.get_stampa_bianco(solo_attiva=False)
    all_tipol   = db.get_tipologia_stampa(solo_attiva=False)

    col_map = {c['id']: c for c in colori}
    mat_map = {m['id']: m for m in materiali}

    # Filtri
    col1, col2 = st.columns(2)
    mat_nomi = ["Tutti"] + [m['nome'] for m in materiali]
    filtro_mat = col1.selectbox("Filtra per materiale", mat_nomi, key="prod_fmat")
    col_nomi_f = ["Tutti"]
    if filtro_mat != "Tutti":
        mat_id_f = next((m['id'] for m in materiali if m['nome'] == filtro_mat), None)
        col_nomi_f += [c['nome'] for c in colori if c['mat_id'] == mat_id_f]
    else:
        col_nomi_f += [c['nome'] for c in colori]
    filtro_col = col2.selectbox("Filtra per colore", col_nomi_f, key="prod_fcol")

    # Filtra prodotti
    prodotti_vis = prodotti
    if filtro_mat != "Tutti":
        mat_id_f = next((m['id'] for m in materiali if m['nome'] == filtro_mat), None)
        colori_mat = {c['id'] for c in colori if c['mat_id'] == mat_id_f}
        prodotti_vis = [p for p in prodotti_vis if p['colore_id'] in colori_mat]
    if filtro_col != "Tutti":
        col_id_f = next((c['id'] for c in colori if c['nome'] == filtro_col), None)
        prodotti_vis = [p for p in prodotti_vis if p['colore_id'] == col_id_f]

    st.caption(f"Prodotti visualizzati: {len(prodotti_vis)} / {len(prodotti)}")

    s_ids  = [s['id'] for s in all_stampa]
    s_nomi = [s['nome'] for s in all_stampa]
    b_ids  = [b['id'] for b in all_bianco]
    b_nomi = [b['nome'] for b in all_bianco]
    t_ids  = [t['id'] for t in all_tipol]
    t_nomi = [t['nome'] for t in all_tipol]

    for prod in prodotti_vis:
        col_info = col_map.get(prod['colore_id'], {})
        mat_id   = col_info.get('mat_id', '')
        mat_info = mat_map.get(mat_id, {})
        etichetta = f"{'✅' if prod['attivo'] else '⬜'} {mat_info.get('nome','?')} / {col_info.get('nome','?')} — {prod['spessore']} — rev: €{prod['prezzo_mq_rev']}/m²"

        with st.expander(etichetta):
            c1, c2, c3 = st.columns(3)
            n_sp  = c1.text_input("Spessore", prod['spessore'], key=f"p_sp_{prod['id']}")
            n_pub = c2.number_input("€/m² Pubblico", 0.0, 9999.0, float(prod['prezzo_mq_pub']), 0.5, key=f"p_pub_{prod['id']}")
            n_rev = c3.number_input("€/m² Rivenditore", 0.0, 9999.0, float(prod['prezzo_mq_rev']), 0.5, key=f"p_rev_{prod['id']}")

            c4, c5, c6 = st.columns(3)
            n_stampa = c4.multiselect("Stampa disponibile",
                s_nomi,
                default=[s_nomi[s_ids.index(x)] for x in prod['stampa_ids'] if x in s_ids],
                key=f"p_s_{prod['id']}")
            n_bianco = c5.multiselect("Stampa bianco",
                b_nomi,
                default=[b_nomi[b_ids.index(x)] for x in prod['bianco_ids'] if x in b_ids],
                key=f"p_b_{prod['id']}")
            n_tipol  = c6.multiselect("Tipologia stampa",
                t_nomi,
                default=[t_nomi[t_ids.index(x)] for x in prod['tipologia_ids'] if x in t_ids],
                key=f"p_t_{prod['id']}")

            n_att = st.checkbox("Attivo", bool(prod['attivo']), key=f"p_a_{prod['id']}")

            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("💾 Salva", key=f"p_save_{prod['id']}"):
                db.upsert_prodotto({
                    'id': prod['id'],
                    'colore_id': prod['colore_id'],
                    'spessore': n_sp,
                    'prezzo_mq_pub': n_pub,
                    'prezzo_mq_rev': n_rev,
                    'stampa_ids': [s_ids[s_nomi.index(n)] for n in n_stampa],
                    'bianco_ids': [b_ids[b_nomi.index(n)] for n in n_bianco],
                    'tipologia_ids': [t_ids[t_nomi.index(n)] for n in n_tipol],
                    'cnc_ids': prod['cnc_ids'],
                    'finitura_ids': prod['finitura_ids'],
                    'optional_ids': prod['optional_ids'],
                    'supporta_stampa': prod['supporta_stampa'],
                    'supporta_cnc': prod['supporta_cnc'],
                    'attivo': 1 if n_att else 0,
                })
                db.log(f"Modificato prodotto: {mat_info.get('nome','?')} {col_info.get('nome','?')} {n_sp}")
                st.success("Salvato ✅")
                st.rerun()
            if col_btn2.button("🗑️ Elimina", key=f"p_del_{prod['id']}"):
                db.delete_prodotto(prod['id'])
                db.log(f"Eliminato prodotto: {prod['id']}", "delete")
                st.rerun()

    st.divider()
    st.subheader("➕ Nuovo Prodotto")
    col_ids_all  = [c['id'] for c in colori]
    col_lab_all  = [f"{mat_map.get(c['mat_id'],{}).get('nome','?')} / {c['nome']}" for c in colori]

    with st.form("nuovo_prod"):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        n_col  = c1.selectbox("Colore (materiale / colore)", col_lab_all)
        n_sp   = c2.text_input("Spessore", "3mm")
        n_pub  = c3.number_input("€/m² Pubblico", 0.0, 9999.0, 0.0, 0.5)
        n_rev  = c4.number_input("€/m² Rivenditore", 0.0, 9999.0, 0.0, 0.5)
        n_stampa = st.multiselect("Stampa disponibile", s_nomi)
        n_bianco = st.multiselect("Stampa bianco", b_nomi)
        n_tipol  = st.multiselect("Tipologia stampa", t_nomi)
        if st.form_submit_button("➕ Aggiungi", type="primary"):
            if n_sp.strip() and col_lab_all:
                col_id_sel = col_ids_all[col_lab_all.index(n_col)]
                db.upsert_prodotto({
                    'id': None,
                    'colore_id': col_id_sel,
                    'spessore': n_sp.strip(),
                    'prezzo_mq_pub': n_pub,
                    'prezzo_mq_rev': n_rev,
                    'stampa_ids': [s_ids[s_nomi.index(n)] for n in n_stampa],
                    'bianco_ids': [b_ids[b_nomi.index(n)] for n in n_bianco],
                    'tipologia_ids': [t_ids[t_nomi.index(n)] for n in n_tipol],
                    'cnc_ids': [], 'finitura_ids': [], 'optional_ids': [],
                    'supporta_stampa': 1, 'supporta_cnc': 0, 'attivo': 1,
                })
                db.log(f"Aggiunto prodotto: {n_col} {n_sp}")
                st.success("Prodotto aggiunto!")
                st.rerun()
            else:
                st.error("Compila i campi obbligatori")


# ─────────────────────────────────────────────
# STAMPA (+ Bianco + Tipologia)
# ─────────────────────────────────────────────
def _admin_tabella_semplice(titolo, items, upsert_fn, delete_fn, extra_fields=None):
    """Helper generico per gestire tabelle semplici (stampa, bianco, tipologia)."""
    st.markdown(f"#### {titolo}")
    for item in items:
        with st.expander(f"{'✅' if item['attivo'] else '⬜'} {item['nome']} — rev: +€{item['add_mq_rev']}/m²"):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            n_nome = c1.text_input("Nome", item['nome'], key=f"{delete_fn.__name__}_n_{item['id']}")
            n_pub  = c2.number_input("+€/m² Pub", 0.0, 999.0, float(item['add_mq_pub']), 0.5, key=f"{delete_fn.__name__}_p_{item['id']}")
            n_rev  = c3.number_input("+€/m² Rev", 0.0, 999.0, float(item['add_mq_rev']), 0.5, key=f"{delete_fn.__name__}_r_{item['id']}")
            n_att  = c4.checkbox("Attivo", bool(item['attivo']), key=f"{delete_fn.__name__}_a_{item['id']}")
            n_desc = st.text_input("Descrizione (opz.)", item.get('descrizione', ''), key=f"{delete_fn.__name__}_d_{item['id']}")

            extra = {}
            if extra_fields:
                for fname, flabel, fdefault in extra_fields:
                    extra[fname] = st.checkbox(flabel, bool(item.get(fname, fdefault)), key=f"{delete_fn.__name__}_{fname}_{item['id']}")

            col_s, col_d = st.columns(2)
            if col_s.button("💾 Salva", key=f"{delete_fn.__name__}_sv_{item['id']}"):
                d = {
                    'id': item['id'], 'nome': n_nome,
                    'descrizione': n_desc,
                    'add_mq_pub': n_pub, 'add_mq_rev': n_rev,
                    'attivo': 1 if n_att else 0,
                }
                d.update({k: 1 if v else 0 for k, v in extra.items()})
                upsert_fn(d)
                st.success("Salvato ✅")
                st.rerun()
            if col_d.button("🗑️ Elimina", key=f"{delete_fn.__name__}_dl_{item['id']}"):
                delete_fn(item['id'])
                st.rerun()

def admin_stampa():
    st.subheader("🖨️ Opzioni Stampa")
    tab1, tab2, tab3 = st.tabs(["Tipo di stampa", "Stampa bianco", "Tipologia stampa"])

    with tab1:
        items = db.get_stampa(solo_attiva=False)
        _admin_tabella_semplice("Tipi di stampa", items, db.upsert_stampa, db.delete_stampa,
                                 extra_fields=[('noprint', 'Senza stampa (noprint)', False)])
        st.divider()
        st.markdown("#### ➕ Nuovo tipo di stampa")
        with st.form("nuova_stampa"):
            c1, c2, c3 = st.columns([3, 1, 1])
            nome = c1.text_input("Nome")
            pub  = c2.number_input("+€/m² Pub", 0.0, 999.0, 0.0, 0.5)
            rev  = c3.number_input("+€/m² Rev", 0.0, 999.0, 0.0, 0.5)
            desc = st.text_input("Descrizione (opz.)")
            nop  = st.checkbox("Senza stampa (noprint)")
            if st.form_submit_button("➕ Aggiungi", type="primary"):
                if nome.strip():
                    db.upsert_stampa({'id': None, 'nome': nome.strip(), 'descrizione': desc,
                                      'add_mq_pub': pub, 'add_mq_rev': rev,
                                      'noprint': 1 if nop else 0, 'attivo': 1})
                    st.success("Aggiunto!")
                    st.rerun()

    with tab2:
        items = db.get_stampa_bianco(solo_attiva=False)
        _admin_tabella_semplice("Opzioni bianco", items, db.upsert_stampa_bianco, db.delete_stampa_bianco)
        st.divider()
        st.markdown("#### ➕ Nuovo bianco")
        with st.form("nuovo_bianco"):
            c1, c2, c3 = st.columns([3, 1, 1])
            nome = c1.text_input("Nome")
            pub  = c2.number_input("+€/m² Pub", 0.0, 999.0, 0.0, 0.5)
            rev  = c3.number_input("+€/m² Rev", 0.0, 999.0, 0.0, 0.5)
            desc = st.text_input("Descrizione (opz.)")
            if st.form_submit_button("➕ Aggiungi", type="primary"):
                if nome.strip():
                    db.upsert_stampa_bianco({'id': None, 'nome': nome.strip(), 'descrizione': desc,
                                             'add_mq_pub': pub, 'add_mq_rev': rev, 'attivo': 1})
                    st.success("Aggiunto!")
                    st.rerun()

    with tab3:
        items = db.get_tipologia_stampa(solo_attiva=False)
        _admin_tabella_semplice("Tipologie stampa", items, db.upsert_tipologia_stampa, db.delete_tipologia_stampa)
        st.divider()
        st.markdown("#### ➕ Nuova tipologia")
        with st.form("nuova_tipol"):
            c1, c2, c3 = st.columns([3, 1, 1])
            nome = c1.text_input("Nome")
            pub  = c2.number_input("+€/m² Pub", 0.0, 999.0, 0.0, 0.5)
            rev  = c3.number_input("+€/m² Rev", 0.0, 999.0, 0.0, 0.5)
            desc = st.text_input("Descrizione (opz.)")
            if st.form_submit_button("➕ Aggiungi", type="primary"):
                if nome.strip():
                    db.upsert_tipologia_stampa({'id': None, 'nome': nome.strip(), 'descrizione': desc,
                                                'add_mq_pub': pub, 'add_mq_rev': rev, 'attivo': 1})
                    st.success("Aggiunto!")
                    st.rerun()


# ─────────────────────────────────────────────
# RIVENDITORI
# ─────────────────────────────────────────────
def admin_rivenditori():
    st.subheader("👥 Rivenditori")
    rivenditori = db.get_rivenditori()

    if rivenditori:
        for r in rivenditori:
            with st.expander(f"{'✅' if r['attivo'] else '⬜'} {r['nome']} — PIN: {'****' if r['pin'] else 'non impostato'}"):
                c1, c2, c3 = st.columns([3, 2, 1])
                n_nome = c1.text_input("Nome", r['nome'], key=f"rev_n_{r['id']}")
                n_pin  = c2.text_input("PIN (visibile solo qui)", r['pin'], key=f"rev_p_{r['id']}")
                n_att  = c3.checkbox("Attivo", bool(r['attivo']), key=f"rev_a_{r['id']}")
                col_s, col_d = st.columns(2)
                if col_s.button("💾 Salva", key=f"rev_s_{r['id']}"):
                    db.upsert_rivenditore({
                        'id': r['id'], 'nome': n_nome,
                        'pin': str(n_pin).strip(),
                        'attivo': 1 if n_att else 0,
                    })
                    db.log(f"Modificato rivenditore: {n_nome}")
                    st.success("Salvato ✅")
                    st.rerun()
                if col_d.button("🗑️ Elimina", key=f"rev_d_{r['id']}"):
                    db.delete_rivenditore(r['id'])
                    db.log(f"Eliminato rivenditore: {r['nome']}", "delete")
                    st.rerun()
    else:
        st.info("Nessun rivenditore configurato")

    st.divider()
    st.subheader("➕ Nuovo Rivenditore")
    with st.form("nuovo_rev"):
        c1, c2 = st.columns(2)
        n_nome = c1.text_input("Nome rivenditore")
        n_pin  = c2.text_input("PIN di accesso")
        if st.form_submit_button("➕ Aggiungi", type="primary"):
            if n_nome.strip() and n_pin.strip():
                db.upsert_rivenditore({
                    'id': None, 'nome': n_nome.strip(),
                    'pin': n_pin.strip(), 'attivo': 1,
                })
                db.log(f"Aggiunto rivenditore: {n_nome}")
                st.success("Rivenditore aggiunto!")
                st.rerun()
            else:
                st.error("Inserisci nome e PIN")


# ─────────────────────────────────────────────
# IMPORT / EXPORT
# ─────────────────────────────────────────────
def admin_import_export():
    st.subheader("💾 Import / Export Dati")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("### 📥 Importa da JSON")
        st.write("Carica un file JSON (dal vecchio configuratore HTML o da un backup).")
        file_up = st.file_uploader("Scegli file JSON", type=["json"])
        if file_up:
            try:
                data = json.loads(file_up.read())
                n_cat = len(data.get('categorie', []))
                n_mat = len(data.get('materiali', []))
                n_col = len(data.get('colori', []))
                n_prod = len(data.get('prodotti', []))
                st.info(f"File riconosciuto: {n_cat} categorie, {n_mat} materiali, {n_col} colori, {n_prod} prodotti")
                if st.button("📥 Importa ora", type="primary"):
                    n, errori = db.import_json(data)
                    db.log(f"Importazione JSON: {n} elementi", "import")
                    st.success(f"✅ Importati {n} elementi con successo!")
                    if errori:
                        st.warning(f"Errori ({len(errori)}): " + "; ".join(errori[:5]))
                    st.rerun()
            except Exception as e:
                st.error(f"File JSON non valido: {e}")

    with col2:
        st.markdown("### 📤 Esporta in JSON")
        st.write("Scarica tutti i dati come file JSON (per backup o trasferimento).")
        if st.button("📤 Genera export", use_container_width=True):
            data = db.export_json()
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            st.download_button(
                label="⬇️ Scarica JSON",
                data=json_str,
                file_name=f"lualdi_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )

    st.divider()
    st.markdown("### 🗄️ Posizione Database")
    db_path = Path("data/lualdi.db").resolve()
    st.code(str(db_path), language="text")
    st.caption("Il database SQLite è un singolo file sul tuo PC. Copialo per fare backup.")

    st.markdown("### 💡 Come fare un backup manuale")
    st.info(
        "1. Premi **Esporta in JSON** per scaricare una copia leggibile di tutti i dati\n"
        "2. Oppure copia direttamente il file `data/lualdi.db` in una cartella sicura\n"
        "3. Per ripristinare: usa **Importa da JSON** con il file JSON, oppure sostituisci `lualdi.db`"
    )


# ─────────────────────────────────────────────
# STORICO
# ─────────────────────────────────────────────
def admin_storico():
    st.subheader("📋 Storico Modifiche")
    storico = db.get_storico(100)
    if storico:
        col1, col2 = st.columns([4, 1])
        col1.caption(f"{len(storico)} voci registrate")
        if col2.button("🗑️ Cancella storico"):
            db.cancella_storico()
            st.rerun()
        for v in storico:
            icona = {"save": "💾", "login": "🔑", "delete": "🗑️", "import": "📥"}.get(v['tipo'], "📝")
            st.markdown(f"{icona} `{v['data']}` — **{v['utente']}** — {v['descrizione']}")
    else:
        st.info("Nessuna voce nello storico")


# ─────────────────────────────────────────────
# IMPOSTAZIONI
# ─────────────────────────────────────────────
def admin_impostazioni():
    st.subheader("🔧 Impostazioni")
    st.markdown("#### Cambia password amministratore")
    with st.form("change_pw"):
        pw_attuale = st.text_input("Password attuale", type="password")
        pw_nuova   = st.text_input("Nuova password", type="password")
        pw_conf    = st.text_input("Conferma nuova password", type="password")
        if st.form_submit_button("💾 Cambia password", type="primary"):
            if pw_attuale != get_admin_password():
                st.error("Password attuale errata")
            elif pw_nuova != pw_conf:
                st.error("Le password non coincidono")
            elif len(pw_nuova) < 4:
                st.error("La password deve essere di almeno 4 caratteri")
            else:
                set_admin_password(pw_nuova)
                db.log("Cambio password admin", "save")
                st.success("Password cambiata con successo!")


# ══════════════════════════════════════════════════════════════
# CONFIGURATORE CLIENTE
# ══════════════════════════════════════════════════════════════
def page_configuratore():
    render_sidebar()

    # Header
    st.markdown("""
    <div class="logo-header">
      <span class="logo-badge">LUALDI</span>
      <div>
        <strong>Configuratore Preventivi</strong><br>
        <span style="color:#888;font-size:12px">Calcola il prezzo del tuo supporto</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.cfg_step

    # Breadcrumb testuale
    passi = ["Categoria", "Materiale", "Colore", "Spessore", "Stampa", "Bianco", "Tipologia", "Dimensioni", "Quantità"]
    bc = " › ".join(
        f"**{p}**" if i + 1 == step else (f"~~{p}~~" if i + 1 < step else p)
        for i, p in enumerate(passi)
    )
    st.markdown(f"<small>{bc}</small>", unsafe_allow_html=True)
    st.progress((step - 1) / (len(passi) - 1))
    st.divider()

    # ── STEP 1: Categoria ─────────────────────────────────────
    if step == 1:
        st.markdown("### Passo 1 — Scegli la categoria")
        categorie = db.get_categorie()
        if not categorie:
            st.warning("⚠️ Nessuna categoria disponibile. Configura il sistema dall'Admin.")
            return
        cols = st.columns(min(len(categorie), 4))
        for i, cat in enumerate(categorie):
            with cols[i % 4]:
                if st.button(f"📦\n\n**{cat['nome']}**",
                             key=f"cat_{cat['id']}", use_container_width=True,
                             type="primary" if st.session_state.cfg_cat_id == cat['id'] else "secondary"):
                    st.session_state.cfg_cat_id = cat['id']
                    st.session_state.cfg_mat_id = None
                    st.session_state.cfg_col_id = None
                    st.session_state.cfg_prod = None
                    st.session_state.cfg_step = 2
                    st.rerun()

    # ── STEP 2: Materiale ─────────────────────────────────────
    elif step == 2:
        cat = next((c for c in db.get_categorie(solo_attive=False) if c['id'] == st.session_state.cfg_cat_id), {})
        st.markdown(f"### Passo 2 — Scegli il materiale")
        st.caption(f"Categoria selezionata: **{cat.get('nome', '?')}**")

        materiali = db.get_materiali(cat_id=st.session_state.cfg_cat_id)
        if not materiali:
            st.warning("Nessun materiale disponibile per questa categoria.")
        else:
            cols = st.columns(min(len(materiali), 4))
            for i, mat in enumerate(materiali):
                with cols[i % 4]:
                    if st.button(f"🧱\n\n**{mat['nome']}**",
                                 key=f"mat_{mat['id']}", use_container_width=True,
                                 type="primary" if st.session_state.cfg_mat_id == mat['id'] else "secondary"):
                        st.session_state.cfg_mat_id = mat['id']
                        st.session_state.cfg_col_id = None
                        st.session_state.cfg_prod = None
                        st.session_state.cfg_step = 3
                        st.rerun()
        st.button("← Indietro", on_click=lambda: setattr(st.session_state, 'cfg_step', 1))

    # ── STEP 3: Colore ────────────────────────────────────────
    elif step == 3:
        mat = next((m for m in db.get_materiali(solo_attivi=False) if m['id'] == st.session_state.cfg_mat_id), {})
        st.markdown("### Passo 3 — Scegli il colore")
        st.caption(f"Materiale selezionato: **{mat.get('nome', '?')}**")

        colori = db.get_colori(mat_id=st.session_state.cfg_mat_id)
        if not colori:
            st.warning("Nessun colore disponibile per questo materiale.")
        else:
            cols = st.columns(min(len(colori), 4))
            for i, col in enumerate(colori):
                with cols[i % 4]:
                    if st.button(f"🎨\n\n**{col['nome']}**",
                                 key=f"col_{col['id']}", use_container_width=True,
                                 type="primary" if st.session_state.cfg_col_id == col['id'] else "secondary"):
                        st.session_state.cfg_col_id = col['id']
                        st.session_state.cfg_prod = None
                        st.session_state.cfg_step = 4
                        st.rerun()
        if st.button("← Indietro"):
            st.session_state.cfg_step = 2
            st.rerun()

    # ── STEP 4: Spessore ──────────────────────────────────────
    elif step == 4:
        col_info = next((c for c in db.get_colori(solo_attivi=False) if c['id'] == st.session_state.cfg_col_id), {})
        st.markdown("### Passo 4 — Scegli lo spessore")
        st.caption(f"Colore selezionato: **{col_info.get('nome', '?')}**")

        prodotti = db.get_prodotti(colore_id=st.session_state.cfg_col_id)
        is_rev   = st.session_state.cfg_is_rev

        if not prodotti:
            st.warning("Nessun spessore disponibile per questo colore.")
        else:
            cols = st.columns(min(len(prodotti), 5))
            for i, prod in enumerate(prodotti):
                prezzo = prod['prezzo_mq_rev'] if is_rev else prod['prezzo_mq_pub']
                etich  = f"**{prod['spessore']}**"
                if prezzo > 0:
                    etich += f"\n\n€ {prezzo:.2f}/m²"
                with cols[i % 5]:
                    if st.button(etich, key=f"prod_{prod['id']}", use_container_width=True):
                        st.session_state.cfg_prod = prod
                        st.session_state.cfg_stampa_id = None
                        st.session_state.cfg_bianco_id = None
                        st.session_state.cfg_tipologia_id = None
                        # Decide prossimo step
                        if prod['supporta_stampa'] and prod['stampa_ids']:
                            st.session_state.cfg_step = 5
                        else:
                            st.session_state.cfg_step = 8
                        st.rerun()
        if st.button("← Indietro"):
            st.session_state.cfg_step = 3
            st.rerun()

    # ── STEP 5: Stampa ────────────────────────────────────────
    elif step == 5:
        prod = st.session_state.cfg_prod
        st.markdown("### Passo 5 — Tipo di stampa")
        st.caption(f"Prodotto: **{prod['spessore']}**")

        all_stampa = db.get_stampa()
        stampa_ids = prod.get('stampa_ids', [])
        disponibili = [s for s in all_stampa if s['id'] in stampa_ids]
        is_rev = st.session_state.cfg_is_rev

        if not disponibili:
            st.info("Nessuna opzione stampa — passo saltato")
            st.session_state.cfg_step = 8
            st.rerun()

        for s in disponibili:
            add = s['add_mq_rev'] if is_rev else s['add_mq_pub']
            add_str = f"+€ {add:.2f}/m²" if add > 0 else "incluso"
            if st.button(f"🖨️  **{s['nome']}**  —  {add_str}",
                         key=f"st_{s['id']}", use_container_width=True):
                st.session_state.cfg_stampa_id = s['id']
                # Prossimo step
                bianco_ids = prod.get('bianco_ids', [])
                tipol_ids  = prod.get('tipologia_ids', [])
                all_b = db.get_stampa_bianco()
                bianco_d = [b for b in all_b if b['id'] in bianco_ids]
                if bianco_d and not s.get('noprint'):
                    st.session_state.cfg_step = 6
                elif tipol_ids:
                    st.session_state.cfg_step = 7
                else:
                    st.session_state.cfg_step = 8
                st.rerun()

        if st.button("← Indietro"):
            st.session_state.cfg_step = 4
            st.rerun()

    # ── STEP 6: Stampa Bianco ─────────────────────────────────
    elif step == 6:
        prod = st.session_state.cfg_prod
        st.markdown("### Passo 6 — Stampa bianco")

        all_b = db.get_stampa_bianco()
        bianco_ids = prod.get('bianco_ids', [])
        disponibili = [b for b in all_b if b['id'] in bianco_ids]
        is_rev = st.session_state.cfg_is_rev

        if not disponibili:
            st.session_state.cfg_bianco_id = None
            tipol_ids = prod.get('tipologia_ids', [])
            st.session_state.cfg_step = 7 if tipol_ids else 8
            st.rerun()

        for b in disponibili:
            add = b['add_mq_rev'] if is_rev else b['add_mq_pub']
            add_str = f"+€ {add:.2f}/m²" if add > 0 else "incluso"
            if st.button(f"⬜  **{b['nome']}**  —  {add_str}",
                         key=f"bn_{b['id']}", use_container_width=True):
                st.session_state.cfg_bianco_id = b['id']
                tipol_ids = prod.get('tipologia_ids', [])
                st.session_state.cfg_step = 7 if tipol_ids else 8
                st.rerun()

        if st.button("← Indietro"):
            st.session_state.cfg_step = 5
            st.rerun()

    # ── STEP 7: Tipologia Stampa ──────────────────────────────
    elif step == 7:
        prod = st.session_state.cfg_prod
        st.markdown("### Passo 7 — Tipologia di stampa")

        all_t = db.get_tipologia_stampa()
        tipol_ids = prod.get('tipologia_ids', [])
        disponibili = [t for t in all_t if t['id'] in tipol_ids]
        is_rev = st.session_state.cfg_is_rev

        if not disponibili:
            st.session_state.cfg_tipologia_id = None
            st.session_state.cfg_step = 8
            st.rerun()

        for t in disponibili:
            add = t['add_mq_rev'] if is_rev else t['add_mq_pub']
            add_str = f"+€ {add:.2f}/m²" if add > 0 else "incluso"
            if st.button(f"🖼️  **{t['nome']}**  —  {add_str}",
                         key=f"tp_{t['id']}", use_container_width=True):
                st.session_state.cfg_tipologia_id = t['id']
                st.session_state.cfg_step = 8
                st.rerun()

        prev_step = 6 if prod.get('bianco_ids') else 5
        if st.button("← Indietro"):
            st.session_state.cfg_step = prev_step
            st.rerun()

    # ── STEP 8: Dimensioni ────────────────────────────────────
    elif step == 8:
        st.markdown("### Passo 8 — Dimensioni del supporto")
        col1, col2, col3 = st.columns(3)
        with col1:
            larg = st.number_input("Larghezza (cm)", min_value=1.0, max_value=10000.0,
                                   value=st.session_state.cfg_larghezza, step=1.0)
            st.session_state.cfg_larghezza = larg
        with col2:
            alt = st.number_input("Altezza (cm)", min_value=1.0, max_value=10000.0,
                                  value=st.session_state.cfg_altezza, step=1.0)
            st.session_state.cfg_altezza = alt
        with col3:
            sup = (larg / 100) * (alt / 100)
            st.metric("Superficie", f"{sup:.4f} m²", f"{larg:.0f}cm × {alt:.0f}cm")

        p = calcola_prezzo_dati()
        if p:
            st.info(f"€/m²: **{p['prezzo_mq']:.2f}** → Prezzo pezzo: **€ {p['prezzo_pezzo']:.2f}**")

        col_n, col_a = st.columns(2)
        if col_n.button("← Indietro"):
            prod = st.session_state.cfg_prod
            tipol_ids = prod.get('tipologia_ids', []) if prod else []
            bianco_ids = prod.get('bianco_ids', []) if prod else []
            if tipol_ids:
                st.session_state.cfg_step = 7
            elif bianco_ids:
                st.session_state.cfg_step = 6
            elif prod and prod.get('stampa_ids'):
                st.session_state.cfg_step = 5
            else:
                st.session_state.cfg_step = 4
            st.rerun()
        if col_a.button("Avanti →", type="primary"):
            st.session_state.cfg_step = 9
            st.rerun()

    # ── STEP 9: Quantità e Riepilogo ─────────────────────────
    elif step == 9:
        st.markdown("### Passo 9 — Quantità e Riepilogo finale")

        qty = st.number_input("Numero di pezzi", min_value=1, max_value=99999,
                              value=st.session_state.cfg_qty, step=1)
        st.session_state.cfg_qty = qty

        p = calcola_prezzo_dati()
        is_rev = st.session_state.cfg_is_rev

        if p:
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("€ / m²",  f"€ {p['prezzo_mq']:.2f}")
            c2.metric("€ / pezzo", f"€ {p['prezzo_pezzo']:.2f}")
            c3.metric(f"TOTALE ({qty} pz)", f"€ {p['prezzo_tot']:.2f}")

        # Riepilogo configurazione
        st.divider()
        st.markdown("#### 📋 Dettaglio configurazione")

        colori_all    = db.get_colori(solo_attivi=False)
        materiali_all = db.get_materiali(solo_attivi=False)
        categorie_all = db.get_categorie(solo_attive=False)

        prod = st.session_state.cfg_prod
        col_info = next((c for c in colori_all    if c['id'] == st.session_state.cfg_col_id), {})
        mat_info = next((m for m in materiali_all if m['id'] == st.session_state.cfg_mat_id), {})
        cat_info = next((c for c in categorie_all if c['id'] == st.session_state.cfg_cat_id), {})

        dati = {
            "Categoria":   cat_info.get('nome', '—'),
            "Materiale":   mat_info.get('nome', '—'),
            "Colore":      col_info.get('nome', '—'),
            "Spessore":    prod['spessore'] if prod else '—',
            "Larghezza":   f"{st.session_state.cfg_larghezza:.0f} cm",
            "Altezza":     f"{st.session_state.cfg_altezza:.0f} cm",
            "Superficie":  f"{p['sup_mq']:.4f} m²" if p else '—',
            "Quantità":    f"{qty} pz",
            "Listino":     f"{'Rivenditore (' + st.session_state.cfg_rev_nome + ')' if is_rev else 'Pubblico'}",
        }

        if st.session_state.cfg_stampa_id:
            stampa = next((s for s in db.get_stampa() if s['id'] == st.session_state.cfg_stampa_id), {})
            dati["Stampa"] = stampa.get('nome', '—')

        if st.session_state.cfg_bianco_id:
            bianco = next((b for b in db.get_stampa_bianco() if b['id'] == st.session_state.cfg_bianco_id), {})
            dati["Bianco"] = bianco.get('nome', '—')

        if st.session_state.cfg_tipologia_id:
            tipo = next((t for t in db.get_tipologia_stampa() if t['id'] == st.session_state.cfg_tipologia_id), {})
            dati["Tipologia"] = tipo.get('nome', '—')

        if p:
            dati["€/m²"] = f"€ {p['prezzo_mq']:.2f}"
            dati["Prezzo / pezzo"] = f"€ {p['prezzo_pezzo']:.2f}"
            dati["**TOTALE**"] = f"**€ {p['prezzo_tot']:.2f}**"

        for k, v in dati.items():
            col_k, col_v = st.columns([2, 3])
            col_k.markdown(f"*{k}*")
            col_v.markdown(v)

        st.divider()
        c1, c2 = st.columns(2)
        if c1.button("← Modifica dimensioni"):
            st.session_state.cfg_step = 8
            st.rerun()
        if c2.button("🔄 Nuovo preventivo", type="primary"):
            cfg_reset()
            st.rerun()


# ══════════════════════════════════════════════════════════════
# ROUTING PRINCIPALE
# ══════════════════════════════════════════════════════════════
page = st.session_state.page

if page == 'home':
    page_home()
elif page == 'configuratore':
    page_configuratore()
elif page == 'admin_login':
    page_admin_login()
elif page == 'admin':
    page_admin()
else:
    page_home()
