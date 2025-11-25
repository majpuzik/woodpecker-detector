#!/usr/bin/env python3
"""
Woodpecker Detector v2 - With Auto-Play Response Sounds
FastAPI server s automatickým přehráváním odstrašovacích zvuků
"""
import numpy as np
import librosa
import sounddevice as sd
import tensorflow as tf
import asyncio
import json
import os
import random
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
MODEL_PATH = "woodpecker_model.keras"
SAMPLE_RATE = 22050
DURATION = 1.0
N_MELS = 64
CONFIDENCE_THRESHOLD = 0.75
SOUNDS_DIR = "static/sounds"

# Načtení modelu
logger.info(f"🧠 Načítám AI model: {MODEL_PATH}")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    logger.info("✅ Model načten")
except Exception as e:
    logger.error(f"❌ Chyba načtení modelu: {e}")
    logger.error("⚠️  Spusť nejprve: python 2_train_model.py")
    model = None

app = FastAPI(title="Woodpecker Detector v2")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- HELPER: Get available sounds ---
def get_sound_categories():
    """Vrátí seznam dostupných kategorií zvuků"""
    categories = {}
    if os.path.exists(SOUNDS_DIR):
        for category in os.listdir(SOUNDS_DIR):
            cat_path = os.path.join(SOUNDS_DIR, category)
            if os.path.isdir(cat_path):
                files = [f for f in os.listdir(cat_path) if f.endswith('.mp3')]
                if files:
                    categories[category] = files
    return categories

@app.get("/api/sounds")
async def list_sounds():
    """API endpoint pro seznam zvuků"""
    return get_sound_categories()

@app.get("/api/sound/{category}/{filename}")
async def serve_sound(category: str, filename: str):
    """Servírování audio souborů"""
    file_path = os.path.join(SOUNDS_DIR, category, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    return {"error": "Sound not found"}

# --- HTML GUI PRO ANDROID ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html>
<head>
    <title>Woodpecker Detector v2</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
    <meta charset="utf-8">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#ffa726">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }

        h1 {
            font-size: 1.8rem;
            color: #ffa726;
            margin-bottom: 20px;
            letter-spacing: 2px;
        }

        #indicator {
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: radial-gradient(circle, #1e1e1e, #0a0a0a);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            box-shadow: 0 0 40px rgba(0,0,0,0.8);
            border: 6px solid #2c2c2c;
            position: relative;
        }

        #indicator.active {
            background: radial-gradient(circle, #ff3b30, #c41c13);
            box-shadow: 0 0 80px rgba(255, 59, 48, 0.8);
            border-color: #ff8a80;
            transform: scale(1.15);
            animation: pulse 0.6s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1.15); }
            50% { transform: scale(1.2); }
        }

        #status-text {
            font-size: 2.5rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 3px;
        }

        .controls {
            margin-top: 30px;
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 15px;
            width: 100%;
            max-width: 350px;
        }

        .control-group {
            margin-bottom: 20px;
        }

        .control-group label {
            display: block;
            margin-bottom: 8px;
            color: #888;
            font-size: 0.9rem;
        }

        select, button {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1rem;
        }

        button {
            background: #ffa726;
            color: #0f0c29;
            font-weight: bold;
            cursor: pointer;
            margin-top: 10px;
        }

        button:active {
            transform: scale(0.98);
        }

        .stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 0.95rem;
        }

        .stat-label { color: #888; }
        .stat-value { font-weight: bold; color: #ffa726; }

        #confidence-bar {
            width: 100%;
            height: 12px;
            background: rgba(0,0,0,0.3);
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 15px;
        }

        #confidence-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #4caf50, #8bc34a);
            transition: width 0.2s;
        }

        #confidence-fill.danger {
            background: linear-gradient(90deg, #ff3b30, #ff8a80);
        }

        #connection-status {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff3b30;
        }

        #connection-status.connected {
            background: #4caf50;
        }
    </style>
</head>
<body>
    <div id="connection-status"></div>
    <div class="logo">🦜</div>
    <h1>DETEKTOR DATLA v2</h1>

    <div id="indicator">
        <span id="status-text">KLID</span>
    </div>

    <div class="controls">
        <div class="control-group">
            <label>🔊 Reakce při detekci:</label>
            <select id="response-mode">
                <option value="predators">🦅 Predátoři (odstrašení)</option>
                <option value="woodpecker">🦜 Datli (volání)</option>
                <option value="mixed">🎲 Mix (náhodně)</option>
                <option value="silent">🔇 Tichý (jen detekce)</option>
            </select>
        </div>

        <div class="control-group">
            <label>🎚️ Hlasitost:</label>
            <input type="range" id="volume" min="0" max="100" value="80"
                   style="width: 100%;">
            <span id="volume-val">80%</span>
        </div>

        <button id="test-sound">🔊 Test zvuku</button>

        <div id="confidence-bar">
            <div id="confidence-fill"></div>
        </div>

        <div class="stat">
            <span class="stat-label">Jistota AI:</span>
            <span class="stat-value" id="confidence-val">0%</span>
        </div>

        <div class="stat">
            <span class="stat-label">Přehráno zvuků:</span>
            <span class="stat-value" id="sounds-played">0</span>
        </div>

        <div class="stat">
            <span class="stat-label">Poslední zvuk:</span>
            <span class="stat-value" id="last-sound">—</span>
        </div>
    </div>

    <script>
        const ws = new WebSocket("ws://" + window.location.host + "/ws");
        const indicator = document.getElementById("indicator");
        const statusText = document.getElementById("status-text");
        const fill = document.getElementById("confidence-fill");
        const confidenceVal = document.getElementById("confidence-val");
        const soundsPlayed = document.getElementById("sounds-played");
        const lastSound = document.getElementById("last-sound");
        const connectionStatus = document.getElementById("connection-status");
        const responseMode = document.getElementById("response-mode");
        const volumeSlider = document.getElementById("volume");
        const volumeVal = document.getElementById("volume-val");
        const testSoundBtn = document.getElementById("test-sound");

        let soundCategories = {};
        let audioContext = null;
        let playCount = 0;
        let lastDetectionTime = 0;
        const COOLDOWN_MS = 3000; // 3s cooldown mezi přehráními

        // Načtení dostupných zvuků
        fetch("/api/sounds")
            .then(r => r.json())
            .then(data => {
                soundCategories = data;
                console.log("✅ Zvuky načteny:", Object.keys(soundCategories));
            });

        // Volume slider
        volumeSlider.addEventListener("input", (e) => {
            volumeVal.innerText = e.target.value + "%";
        });

        // Test sound
        testSoundBtn.addEventListener("click", () => {
            playRandomSound();
        });

        // WebSocket
        ws.onopen = () => {
            connectionStatus.classList.add("connected");
        };

        ws.onclose = () => {
            connectionStatus.classList.remove("connected");
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const prob = data.probability;

            fill.style.width = (prob * 100) + "%";
            confidenceVal.innerText = (prob * 100).toFixed(1) + "%";

            if (data.detected) {
                indicator.classList.add("active");
                statusText.innerText = "DATEL!";
                fill.classList.add("danger");

                // Auto-play sound (s cooldownem)
                const now = Date.now();
                if (now - lastDetectionTime > COOLDOWN_MS) {
                    lastDetectionTime = now;
                    playResponseSound();
                }

                // Vibrace
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate([100, 50, 100]);
                }
            } else {
                indicator.classList.remove("active");
                statusText.innerText = "KLID";
                fill.classList.remove("danger");
            }
        };

        function playResponseSound() {
            const mode = responseMode.value;

            if (mode === "silent") return;

            let category;

            if (mode === "predators") {
                const predatorCats = ["predator_hawk", "predator_owl", "predator_buzzard"];
                category = predatorCats[Math.floor(Math.random() * predatorCats.length)];
            } else if (mode === "woodpecker") {
                const woodpeckerCats = ["woodpecker_drumming", "woodpecker_calls"];
                category = woodpeckerCats[Math.floor(Math.random() * woodpeckerCats.length)];
            } else { // mixed
                const allCats = Object.keys(soundCategories);
                category = allCats[Math.floor(Math.random() * allCats.length)];
            }

            playSound(category);
        }

        function playRandomSound() {
            const allCats = Object.keys(soundCategories);
            if (allCats.length === 0) {
                alert("⚠️ Žádné zvuky! Spusť: python 0_download_sounds.py");
                return;
            }
            const category = allCats[Math.floor(Math.random() * allCats.length)];
            playSound(category);
        }

        function playSound(category) {
            if (!soundCategories[category] || soundCategories[category].length === 0) {
                console.warn("⚠️ Kategorie neexistuje:", category);
                return;
            }

            const files = soundCategories[category];
            const randomFile = files[Math.floor(Math.random() * files.length)];
            const url = `/api/sound/${category}/${randomFile}`;

            const audio = new Audio(url);
            audio.volume = volumeSlider.value / 100;
            audio.play()
                .then(() => {
                    playCount++;
                    soundsPlayed.innerText = playCount;
                    lastSound.innerText = category.replace(/_/g, ' ');
                    console.log("🔊 Přehráno:", category, randomFile);
                })
                .catch(err => {
                    console.error("❌ Chyba přehrávání:", err);
                });
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(HTML_INTERFACE)

@app.get("/api/status")
async def status():
    """API endpoint pro kontrolu stavu"""
    categories = get_sound_categories()
    return {
        "status": "running",
        "model_loaded": model is not None,
        "sample_rate": SAMPLE_RATE,
        "threshold": CONFIDENCE_THRESHOLD,
        "sound_categories": list(categories.keys()),
        "total_sounds": sum(len(files) for files in categories.values())
    }

# --- AUDIO PROCESSING ---
def process_realtime_audio(audio_chunk):
    """Převede RAW audio na predikci modelu"""
    try:
        if model is None:
            return 0.0

        mel_spec = librosa.feature.melspectrogram(
            y=audio_chunk,
            sr=SAMPLE_RATE,
            n_mels=N_MELS,
            fmax=8000
        )

        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (
            mel_spec_db.max() - mel_spec_db.min() + 1e-8
        )

        model_input = mel_spec_norm[np.newaxis, ..., np.newaxis]
        prediction = model.predict(model_input, verbose=0)
        return float(prediction[0][0])

    except Exception as e:
        logger.error(f"❌ Chyba zpracování: {e}")
        return 0.0

async def audio_loop(websocket: WebSocket):
    """Hlavní smyčka pro zpracování audia"""
    BLOCK_SIZE = int(SAMPLE_RATE * DURATION)
    loop = asyncio.get_event_loop()

    logger.info(f"🎤 Zahajuji naslouchání (Sample rate: {SAMPLE_RATE} Hz)")

    try:
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE
        ) as stream:

            while True:
                if stream.read_available >= BLOCK_SIZE:
                    data, _ = stream.read(BLOCK_SIZE)
                    audio = data[:, 0]

                    prob = await loop.run_in_executor(None, process_realtime_audio, audio)
                    detected = prob > CONFIDENCE_THRESHOLD

                    if detected:
                        logger.info(f"🦜 DATEL! (Confidence: {prob*100:.1f}%)")

                    await websocket.send_text(json.dumps({
                        "detected": detected,
                        "probability": prob,
                        "timestamp": datetime.now().isoformat()
                    }))

                await asyncio.sleep(0.01)

    except Exception as e:
        logger.error(f"❌ Chyba audio smyčky: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint pro real-time streaming"""
    await websocket.accept()
    logger.info("📱 Nový klient připojen")

    try:
        await audio_loop(websocket)
    except Exception as e:
        logger.error(f"❌ Spojení ukončeno: {e}")
    finally:
        logger.info("📱 Klient odpojen")

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     🦜 WOODPECKER DETECTOR v2 - WITH SOUND RESPONSE      ║
    ╚══════════════════════════════════════════════════════════╝

    🚀 Spouštím server...
    📱 Otevři: http://localhost:8000
    🌐 Mobil: http://YOUR_MAC_IP:8000

    ⚙️  Před spuštěním:
    1. python 0_download_sounds.py  (stáhnout zvuky)
    2. python 1_download_dataset.py (dataset)
    3. python 2_train_model.py      (trénink)

    Stiskni Ctrl+C pro ukončení
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000)
