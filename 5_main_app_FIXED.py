#!/usr/bin/env python3
"""
Woodpecker Detector v3 - FIXED: Audio from Client Browser
FastAPI server s audio streamingem z prohlížeče klienta
"""
import numpy as np
import librosa
import tensorflow as tf
import asyncio
import json
import os
import random
import base64
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
CONFIDENCE_THRESHOLD = 0.50  # Sníženo z 0.75 pro vyšší citlivost
SOUNDS_DIR = "static/sounds"

# Načtení modelu
logger.info(f"🧠 Načítám AI model: {MODEL_PATH}")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    logger.info("✅ Model načten")
except Exception as e:
    logger.error(f"❌ Chyba načtení modelu: {e}")
    model = None

app = FastAPI(title="Woodpecker Detector v3")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- HELPER: Get available sounds ---
def get_sound_categories():
    """Vrátí seznam dostupných kategorií zvuků"""
    categories = {}
    if not os.path.exists(SOUNDS_DIR):
        return categories

    for category in os.listdir(SOUNDS_DIR):
        cat_path = os.path.join(SOUNDS_DIR, category)
        if os.path.isdir(cat_path):
            files = [f for f in os.listdir(cat_path) if f.endswith('.mp3')]
            if files:
                categories[category] = files

    return categories

@app.get("/api/sounds")
async def list_sounds():
    """Vrátí seznam dostupných zvuků"""
    return get_sound_categories()

@app.get("/api/sound/{category}/{filename}")
async def serve_sound(category: str, filename: str):
    """Vrátí audio soubor"""
    file_path = os.path.join(SOUNDS_DIR, category, filename)
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    return FileResponse(file_path, media_type="audio/mpeg")

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
def process_audio_chunk(audio_float32):
    """Převede audio chunk na predikci"""
    try:
        if model is None:
            return 0.0

        # Padding nebo trim na správnou délku
        target_length = int(SAMPLE_RATE * DURATION)
        if len(audio_float32) < target_length:
            audio_float32 = np.pad(audio_float32, (0, target_length - len(audio_float32)))
        else:
            audio_float32 = audio_float32[:target_length]

        # Mel-spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=audio_float32,
            sr=SAMPLE_RATE,
            n_mels=N_MELS,
            fmax=8000
        )

        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (
            mel_spec_db.max() - mel_spec_db.min() + 1e-8
        )

        # Predikce
        model_input = mel_spec_norm[np.newaxis, ..., np.newaxis]
        prediction = model.predict(model_input, verbose=0)
        prob = float(prediction[0][0])

        return prob

    except Exception as e:
        logger.error(f"❌ Chyba zpracování: {e}")
        return 0.0

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint - přijímá audio z prohlížeče"""
    await websocket.accept()
    logger.info("📱 Nový klient připojen")

    chunk_counter = 0

    try:
        while True:
            # Přijmi data z klienta
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "audio":
                chunk_counter += 1

                # Base64 dekódování
                audio_b64 = message.get("audio")
                audio_bytes = base64.b64decode(audio_b64)

                # Převod na float32 array
                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0

                # Zpracování AI modelem
                prob = process_audio_chunk(audio_float32)
                detected = prob > CONFIDENCE_THRESHOLD

                if detected:
                    logger.info(f"🦜 DATEL DETEKOVÁN! (Confidence: {prob*100:.1f}%)")

                # Log každých 10 chunků
                if chunk_counter % 10 == 0:
                    logger.info(f"📊 Chunk #{chunk_counter}, Confidence: {prob*100:.1f}%")

                # Odešli výsledek
                await websocket.send_text(json.dumps({
                    "detected": detected,
                    "probability": prob,
                    "timestamp": datetime.now().isoformat()
                }))

            await asyncio.sleep(0.001)

    except Exception as e:
        logger.error(f"❌ WebSocket chyba: {e}")
    finally:
        logger.info("📱 Klient odpojen")

# --- HTML INTERFACE ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Woodpecker Detector v3</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }
        h1 {
            font-size: 2rem;
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
            background: linear-gradient(90deg, #4caf50, #ffa726, #ff3b30);
            transition: width 0.2s;
        }
        #connection-status {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #666;
            display: inline-block;
            margin-left: 8px;
        }
        #connection-status.connected {
            background: #4caf50;
            box-shadow: 0 0 10px #4caf50;
        }
    </style>
</head>
<body>
    <h1>🦜 Woodpecker Detector v3</h1>
    <div style="text-align: center;">
        <span style="color: #888;">Připojení:</span>
        <span id="connection-status"></span>
    </div>

    <div id="indicator">
        <div id="status-text">ČEKÁM</div>
    </div>

    <div class="controls">
        <div class="control-group">
            <label>Reakce na detekci:</label>
            <select id="response-mode">
                <option value="predators">🦅 Dravci (odstrašení)</option>
                <option value="woodpecker">🦜 Datli (přilákání)</option>
                <option value="mixed">🔀 Smíšené</option>
                <option value="silent">🔇 Bez zvuku</option>
            </select>
        </div>

        <div class="control-group">
            <label>Hlasitost: <span id="volume-val">80%</span></label>
            <input type="range" id="volume" min="0" max="100" value="80"
                   style="width: 100%;">
        </div>

        <button id="test-sound">🔊 Test zvuku</button>
        <button id="start-mic">🎤 Spustit mikrofon</button>

        <div style="margin: 15px 0; padding: 10px; background: rgba(255,152,0,0.2); border-radius: 8px; font-size: 0.85rem; color: #ffb74d; display: none;" id="https-warning">
            ⚠️ Mikrofon může vyžadovat HTTPS připojení. Pokud nefunguje, zkus Chrome nebo Firefox.
        </div>

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

        <div class="stat">
            <span class="stat-label">Chunky odeslány:</span>
            <span class="stat-value" id="chunks-sent">0</span>
        </div>
    </div>

    <script>
        // Use wss:// for HTTPS, ws:// for HTTP
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(wsProtocol + "//" + window.location.host + "/ws");
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
        const startMicBtn = document.getElementById("start-mic");
        const chunksSent = document.getElementById("chunks-sent");

        let soundCategories = {};
        let audioContext = null;
        let mediaStream = null;
        let playCount = 0;
        let lastDetectionTime = 0;
        let chunkCounter = 0;
        const COOLDOWN_MS = 3000;

        // Check if getUserMedia is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            document.getElementById('https-warning').style.display = 'block';
        }

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

        // Start microphone
        startMicBtn.addEventListener("click", async () => {
            try {
                await startMicrophone();
                startMicBtn.innerText = "✅ Mikrofon aktivní";
                startMicBtn.disabled = true;
            } catch (err) {
                alert("Chyba mikrofonu: " + err.message);
            }
        });

        // WebSocket handlers
        ws.onopen = () => {
            connectionStatus.classList.add("connected");
            console.log("✅ WebSocket připojen");
        };

        ws.onclose = () => {
            connectionStatus.classList.remove("connected");
            console.log("❌ WebSocket odpojen");
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const prob = data.probability;

            fill.style.width = (prob * 100) + "%";
            confidenceVal.innerText = (prob * 100).toFixed(1) + "%";

            if (data.detected) {
                indicator.classList.add("active");
                statusText.innerText = "DATEL!";

                const now = Date.now();
                if (now - lastDetectionTime > COOLDOWN_MS) {
                    lastDetectionTime = now;
                    playResponseSound();
                }

                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate([100, 50, 100]);
                }
            } else {
                indicator.classList.remove("active");
                statusText.innerText = "KLID";
            }
        };

        // Start microphone and stream to server
        async function startMicrophone() {
            // Check for getUserMedia support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                // Try older API
                navigator.getUserMedia = navigator.getUserMedia ||
                                        navigator.webkitGetUserMedia ||
                                        navigator.mozGetUserMedia;

                if (!navigator.getUserMedia) {
                    throw new Error("Tvůj prohlížeč nepodporuje přístup k mikrofonu. Zkus Chrome nebo Firefox.");
                }
            }

            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 22050
            });

            // Try modern API first, fallback to old
            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: 22050,
                        channelCount: 1,
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: true
                    }
                });
            } catch (e) {
                // Fallback: try simpler constraints
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: true
                });
            }

            const source = audioContext.createMediaStreamSource(mediaStream);

            // ZVÝŠENÍ CITLIVOSTI MIKROFONU
            const gainNode = audioContext.createGain();
            gainNode.gain.value = 5.0; // 5x zesílení (1.0 = normal, 5.0 = 5x hlasitější)

            const bufferSize = 4096; // Musí být mocnina 2!
            const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);

            let audioBuffer = [];
            const targetLength = 22050; // 1 sekunda při 22050 Hz

            processor.onaudioprocess = (e) => {
                if (ws.readyState === WebSocket.OPEN) {
                    const inputData = e.inputBuffer.getChannelData(0);

                    // Přidej do bufferu
                    audioBuffer.push(...inputData);

                    // Když máme dostatek dat (1 sekunda), odešli
                    if (audioBuffer.length >= targetLength) {
                        const audioChunk = audioBuffer.slice(0, targetLength);
                        audioBuffer = audioBuffer.slice(targetLength);

                        // Convert Float32Array to Int16Array
                        const int16 = new Int16Array(audioChunk.length);
                        for (let i = 0; i < audioChunk.length; i++) {
                            int16[i] = Math.max(-32768, Math.min(32767, audioChunk[i] * 32768));
                        }

                        // Convert to base64
                        const bytes = new Uint8Array(int16.buffer);
                        const b64 = btoa(String.fromCharCode.apply(null, bytes));

                        // Send to server
                        ws.send(JSON.stringify({
                            type: "audio",
                            audio: b64
                        }));

                        chunkCounter++;
                        chunksSent.innerText = chunkCounter;
                    }
                }
            };

            // Audio chain: source -> gain -> processor -> destination
            source.connect(gainNode);
            gainNode.connect(processor);
            processor.connect(audioContext.destination);

            statusText.innerText = "NASLOUCHÁM";
            console.log("🎤 Mikrofon aktivní, 5x zesílení, streaming zahájen");
        }

        // Play response sound
        function playResponseSound() {
            const mode = responseMode.value;
            if (mode === "silent") return;

            let categories = [];
            if (mode === "predators") {
                categories = ["predator_hawk", "predator_owl", "predator_buzzard"];
            } else if (mode === "woodpecker") {
                categories = ["woodpecker_drumming", "woodpecker_calls"];
            } else {
                categories = Object.keys(soundCategories);
            }

            const available = categories.filter(c => soundCategories[c] && soundCategories[c].length > 0);
            if (available.length === 0) return;

            const category = available[Math.floor(Math.random() * available.length)];
            const files = soundCategories[category];
            const randomFile = files[Math.floor(Math.random() * files.length)];

            playSound(category, randomFile);
        }

        function playRandomSound() {
            const categories = Object.keys(soundCategories);
            if (categories.length === 0) {
                alert("Žádné zvuky k dispozici!");
                return;
            }

            const category = categories[Math.floor(Math.random() * categories.length)];
            const files = soundCategories[category];
            if (files.length === 0) return;

            const randomFile = files[Math.floor(Math.random() * files.length)];
            playSound(category, randomFile);
        }

        function playSound(category, filename) {
            const audio = new Audio(`/api/sound/${category}/${filename}`);
            audio.volume = volumeSlider.value / 100;

            audio.play()
                .then(() => {
                    playCount++;
                    soundsPlayed.innerText = playCount;
                    lastSound.innerText = category.replace(/_/g, ' ');
                    console.log("🔊 Přehráno:", category, filename);
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

if __name__ == "__main__":
    import uvicorn
    import os.path

    # Check for SSL certificates
    ssl_keyfile = "ssl/key.pem"
    ssl_certfile = "ssl/cert.pem"

    use_ssl = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)
    protocol = "https" if use_ssl else "http"

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║     🦜 WOODPECKER DETECTOR v3 - HTTPS VERSION            ║
    ╚══════════════════════════════════════════════════════════╝

    🚀 Server běží přes {protocol.upper()}...
    📱 Otevři: {protocol}://localhost:8000
    🌐 Mobil: {protocol}://192.168.10.79:8000

    ✅ Audio stream z PROHLÍŽEČE (ne ze serveru)
    ✅ HTTPS - mikrofon bude fungovat!
    ⚠️  Self-signed certifikát - povolíš v prohlížeči

    Stiskni Ctrl+C pro ukončení
    """)

    if use_ssl:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        logger.warning("⚠️ SSL certifikáty nenalezeny, spouštím HTTP (mikrofon nemusí fungovat)")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
