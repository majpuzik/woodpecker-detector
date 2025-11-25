#!/usr/bin/env python3
"""
DEMO Dataset Generator
Vytvoří syntetická data pro test/demo bez API
"""
import os
import numpy as np
import soundfile as sf
from scipy import signal

DATASET_DIR = "dataset"
SAMPLE_RATE = 22050

def generate_drumming_sound(duration=1.0):
    """Generuje simulaci klepání datla"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    # Základní tóny (800-3000 Hz)
    freq = 1500
    sound = 0.5 * np.sin(2 * np.pi * freq * t)

    # Rytmické klepání (10-20 Hz repetition rate)
    beats_per_sec = 15
    pulse_train = signal.square(2 * np.pi * beats_per_sec * t, duty=0.1)
    pulse_train = (pulse_train + 1) / 2  # 0 to 1

    # Envelope (útlum)
    envelope = np.exp(-t * 3)

    audio = sound * pulse_train * envelope

    # Přidat šum
    noise = np.random.normal(0, 0.02, len(audio))
    audio = audio + noise

    # Normalizace
    audio = audio / np.max(np.abs(audio))

    return audio

def generate_noise_sound(duration=1.0):
    """Generuje obecný šum (les, vítr)"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))

    # Nízký freq šum (vítr)
    noise = np.random.normal(0, 0.1, len(t))

    # Band-pass filter (100-5000 Hz)
    sos = signal.butter(5, [100, 5000], 'bandpass', fs=SAMPLE_RATE, output='sos')
    filtered = signal.sosfilt(sos, noise)

    # Pár náhodných ptačích zvuků
    for i in range(3):
        start = int(np.random.rand() * len(t) * 0.7)
        bird_freq = np.random.randint(2000, 5000)
        chirp_len = int(0.1 * SAMPLE_RATE)
        chirp = 0.3 * np.sin(2 * np.pi * bird_freq * np.linspace(0, 0.1, chirp_len))
        if start + chirp_len < len(filtered):
            filtered[start:start+chirp_len] += chirp

    # Normalizace
    filtered = filtered / np.max(np.abs(filtered))

    return filtered

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║      🎬 WOODPECKER DETECTOR - DEMO DATASET               ║
    ║        Generování syntetických dat pro test              ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Vytvoř složky
    woodpecker_dir = os.path.join(DATASET_DIR, "woodpecker")
    noise_dir = os.path.join(DATASET_DIR, "noise")
    os.makedirs(woodpecker_dir, exist_ok=True)
    os.makedirs(noise_dir, exist_ok=True)

    # Generuj datly
    print("\n🦜 Generuji zvuky datlů...")
    for i in range(30):
        audio = generate_drumming_sound(duration=1.0)
        filename = os.path.join(woodpecker_dir, f"demo_woodpecker_{i:03d}.wav")
        sf.write(filename, audio, SAMPLE_RATE)
        if i % 10 == 0:
            print(f"   Vygenerováno: {i}/30", end='\r')
    print(f"   ✅ Vygenerováno: 30/30")

    # Generuj šum
    print("\n🌲 Generuji zvuky pozadí...")
    for i in range(30):
        audio = generate_noise_sound(duration=1.0)
        filename = os.path.join(noise_dir, f"demo_noise_{i:03d}.wav")
        sf.write(filename, audio, SAMPLE_RATE)
        if i % 10 == 0:
            print(f"   Vygenerováno: {i}/30", end='\r')
    print(f"   ✅ Vygenerováno: 30/30")

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                  ✅ DEMO DATA VYTVOŘENA                  ║
    ╠══════════════════════════════════════════════════════════╣
    ║  🦜 Datli:     30 WAV souborů                           ║
    ║  🌲 Pozadí:    30 WAV souborů                           ║
    ║  📦 Celkem:    60 souborů                               ║
    ╚══════════════════════════════════════════════════════════╝

    ⚠️  POZNÁMKA: Toto jsou SYNTETICKÁ data pro demo!
    Pro produkci použij reálná data z Xeno-canto když API funguje.

    Další krok: python 2_train_model.py
    """)

if __name__ == "__main__":
    main()
