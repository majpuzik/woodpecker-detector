#!/usr/bin/env python3
"""
Woodpecker Detector - Dataset Downloader
Stahuje audio vzorky z Xeno-canto API pro trénink modelu
"""
import os
import requests
import json
import time
from pathlib import Path

# Konfigurace
DATASET_DIR = "dataset"
CLASSES = ["woodpecker", "noise"]

def download_from_xeno_canto(query, folder, limit=30):
    """Stáhne vzorky z Xeno-canto API"""
    print(f"\n{'='*60}")
    print(f"🔍 Hledám: {query}")
    print(f"{'='*60}")

    os.makedirs(folder, exist_ok=True)

    api_url = f"https://xeno-canto.org/api/2/recordings?query={query}"

    try:
        print(f"📡 Připojuji se k API...")
        response = requests.get(api_url, timeout=10)
        data = response.json()
    except Exception as e:
        print(f"❌ Chyba připojení: {e}")
        return

    num_recordings = int(data.get('numRecordings', 0))
    print(f"✅ Nalezeno celkem: {num_recordings} nahrávek")

    if num_recordings == 0:
        print("⚠️  Žádné nahrávky nenalezeny!")
        return

    count = 0
    skipped = 0

    for rec in data.get('recordings', []):
        if count >= limit:
            break

        file_url = rec.get('file', '')
        file_id = rec.get('id', 'unknown')
        file_name = os.path.join(folder, f"{file_id}.mp3")

        # Stahování pouze pokud soubor neexistuje
        if os.path.exists(file_name):
            skipped += 1
            continue

        species = rec.get('en', 'Unknown')
        rec_type = rec.get('type', 'N/A')
        quality = rec.get('q', '?')

        print(f"\n📥 [{count+1}/{limit}] {species} ({rec_type}) [Q:{quality}]")
        print(f"   🔗 {file_url[:60]}...")

        try:
            # Stažení souboru
            audio_response = requests.get(file_url, timeout=30)
            audio_response.raise_for_status()

            with open(file_name, 'wb') as f:
                f.write(audio_response.content)

            file_size = os.path.getsize(file_name) / 1024  # KB
            print(f"   ✅ Uloženo: {file_size:.1f} KB")

            count += 1
            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"   ❌ Chyba stahování: {e}")

    print(f"\n{'='*60}")
    print(f"✅ Staženo: {count} souborů")
    if skipped > 0:
        print(f"⏭️  Přeskočeno (již existuje): {skipped}")
    print(f"{'='*60}")

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║         🦜 WOODPECKER DETECTOR - DATASET LOADER          ║
    ║              Automatické stahování audio dat             ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # 1. Stáhneme Datla (hledáme specificky "drumming")
    # Používáme rod Dendrocopos (Strakapoud), který je v ČR běžný
    print("\n🎯 FÁZE 1: Stahování zvuků datlů (bubnování)")
    download_from_xeno_canto(
        "gen:Dendrocopos type:drumming q:A",
        os.path.join(DATASET_DIR, "woodpecker"),
        limit=50
    )

    # 2. Stáhneme "Šum lesa" (negativní vzorky)
    print("\n🎯 FÁZE 2: Stahování pozadí (ptačí zpěv bez bubnování)")
    download_from_xeno_canto(
        "gen:Parus type:song q:A",
        os.path.join(DATASET_DIR, "noise"),
        limit=50
    )

    # Statistika
    woodpecker_count = len([f for f in os.listdir(os.path.join(DATASET_DIR, "woodpecker")) if f.endswith('.mp3')])
    noise_count = len([f for f in os.listdir(os.path.join(DATASET_DIR, "noise")) if f.endswith('.mp3')])

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                  📊 FINÁLNÍ STATISTIKA                   ║
    ╠══════════════════════════════════════════════════════════╣
    ║  🦜 Datli (drumming):     {woodpecker_count:3d} souborů                 ║
    ║  🌲 Pozadí (noise):       {noise_count:3d} souborů                 ║
    ║  📦 Celkem:               {woodpecker_count + noise_count:3d} souborů                 ║
    ╚══════════════════════════════════════════════════════════╝

    ✅ Dataset připraven ve složce 'dataset/'

    Další krok: python 2_train_model.py
    """)

if __name__ == "__main__":
    main()
