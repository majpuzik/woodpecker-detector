#!/bin/bash

echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🦜 WOODPECKER DETECTOR - Quick Start             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Zjištění IP adresy Macu
MAC_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo "📱 Pro připojení z mobilu použij:"
echo "   http://$MAC_IP:8000"
echo ""
echo "💻 Lokálně:"
echo "   http://localhost:8000"
echo ""
echo "🚀 Spouštím server..."
echo ""

# Spuštění serveru
python3 3_main_app.py
