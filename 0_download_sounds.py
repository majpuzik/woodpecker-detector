#!/usr/bin/env python3
"""
Woodpecker Detector - Sound Library Downloader
Stahuje zvuky pro odstrašování (datli + predátoři)
"""
import os
import requests
import time

SOUNDS_DIR = "static/sounds"
os.makedirs(SOUNDS_DIR, exist_ok=True)

def download_sound(query, category, limit=5):
    """Stáhne zvuky z Xeno-canto"""
    print(f"\n{'='*60}")
    print(f"🔊 Kategorie: {category}")
    print(f"{'='*60}")

    folder = os.path.join(SOUNDS_DIR, category)
    os.makedirs(folder, exist_ok=True)

    # URL encode query
    import urllib.parse
    encoded_query = urllib.parse.quote(query)
    api_url = f"https://xeno-canto.org/api/2/recordings?query={encoded_query}"

    try:
        print(f"📡 API: {api_url[:80]}...")
        response = requests.get(api_url, timeout=15)
        data = response.json()
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return

    recordings = data.get('recordings', [])
    num_total = data.get('numRecordings', 0)
    print(f"✅ Nalezeno: {num_total} nahrávek celkem")
    print(f"📥 Stahují se první: {min(limit, len(recordings))} vzorků")

    count = 0
    for rec in recordings[:limit]:
        if count >= limit:
            break

        file_url = rec.get('file', '')
        file_id = rec.get('id', 'unknown')
        species = rec.get('en', 'Unknown')
        rec_type = rec.get('type', 'N/A')

        file_name = os.path.join(folder, f"{file_id}.mp3")

        if os.path.exists(file_name):
            continue

        print(f"\n📥 [{count+1}/{limit}] {species} ({rec_type})")

        try:
            audio = requests.get(file_url, timeout=30)
            with open(file_name, 'wb') as f:
                f.write(audio.content)
            print(f"   ✅ Uloženo")
            count += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"   ❌ Chyba: {e}")

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║      🔊 WOODPECKER DETECTOR - SOUND LIBRARY              ║
    ║          Stahování zvuků pro odstrašování                ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Simplified queries (bez type: filtru)

    # 1. Zvuky datlů
    download_sound(
        "dendrocopos",
        "woodpecker_drumming",
        limit=10
    )

    # 2. Predátoři - Jestřáb
    download_sound(
        "accipiter gentilis",
        "predator_hawk",
        limit=10
    )

    # 3. Predátoři - Výr
    download_sound(
        "bubo bubo",
        "predator_owl",
        limit=10
    )

    # 4. Predátoři - Káně
    download_sound(
        "buteo buteo",
        "predator_buzzard",
        limit=10
    )

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                  ✅ HOTOVO                               ║
    ╠══════════════════════════════════════════════════════════╣
    ║  Zvuky uloženy ve: {SOUNDS_DIR}/                     ║
    ║                                                          ║
    ║  Kategorie:                                              ║
    ║  🦜 woodpecker_drumming  - Bubnování datla              ║
    ║  🗣️  woodpecker_calls     - Volání datla                ║
    ║  🦅 predator_hawk        - Jestřáb (hlavní predátor)   ║
    ║  🦉 predator_owl         - Výr                          ║
    ║  🦅 predator_buzzard     - Káně                         ║
    ╚══════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    main()
