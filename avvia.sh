#!/bin/bash
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       LUALDI INDUSTRIA GRAFICA                       ║"
echo "║       Configuratore Preventivi — Python              ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# Controlla Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trovato. Installalo con: brew install python3"
    exit 1
fi

# Installa dipendenze
echo "📦 Installazione dipendenze..."
pip3 install -r requirements.txt -q

echo ""
echo "🚀 Avvio applicazione..."
echo "📌 Aprirà il browser su: http://localhost:8501"
echo "⛔ Per fermare: Ctrl+C"
echo ""

streamlit run app.py --server.headless false --browser.gatherUsageStats false
