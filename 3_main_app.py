#!/usr/bin/env python3
"""
Woodpecker Detector - Real-time Detection Server
FastAPI server s WebSocket streamin pro Android GUI
"""
import numpy as np
import librosa
import sounddevice as sd
import tensorflow as tf
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import logging

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
MODEL_PATH = "woodpecker_model.keras"
SAMPLE_RATE = 22050
DURATION = 1.0
N_MELS = 64
CONFIDENCE_THRESHOLD = 0.75  # 75% jistota pro alarm

# Načtení modelu
logger.info(f"🧠 Načítám AI model: {MODEL_PATH}")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    logger.info("✅ Model načten")
except Exception as e:
    logger.error(f"❌ Chyba načtení modelu: {e}")
    logger.error("⚠️  Spusť nejprve: python 2_train_model.py")
    model = None

app = FastAPI(title="Woodpecker Detector API")

# --- HTML GUI PRO ANDROID ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html>
<head>
    <title>Woodpecker Pro Detector</title>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0"/>
    <meta charset="utf-8">
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
            margin-bottom: 30px;
            text-shadow: 0 2px 10px rgba(255, 167, 38, 0.3);
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
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            box-shadow:
                0 0 40px rgba(0,0,0,0.8),
                inset 0 0 30px rgba(255,255,255,0.05);
            border: 6px solid #2c2c2c;
            position: relative;
        }

        #indicator.active {
            background: radial-gradient(circle, #ff3b30, #c41c13);
            box-shadow:
                0 0 80px rgba(255, 59, 48, 0.8),
                0 0 120px rgba(255, 59, 48, 0.4);
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
            text-shadow: 0 4px 8px rgba(0,0,0,0.5);
        }

        #indicator.active #status-text {
            animation: shake 0.3s ease-in-out infinite;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }

        .info-panel {
            width: 100%;
            max-width: 350px;
            margin-top: 40px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }

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
            transition: width 0.2s, background 0.3s;
            border-radius: 6px;
        }

        #confidence-fill.danger {
            background: linear-gradient(90deg, #ff3b30, #ff8a80);
        }

        .stat {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 0.95rem;
        }

        .stat:last-child {
            border-bottom: none;
        }

        .stat-label {
            color: #888;
        }

        .stat-value {
            font-weight: bold;
            color: #ffa726;
        }

        #connection-status {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #ff3b30;
            box-shadow: 0 0 10px rgba(255, 59, 48, 0.5);
        }

        #connection-status.connected {
            background: #4caf50;
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
        }

        .logo {
            font-size: 4rem;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div id="connection-status"></div>

    <div class="logo">🦜</div>
    <h1>AI DETEKTOR DATLA</h1>

    <div id="indicator">
        <span id="status-text">KLID</span>
    </div>

    <div class="info-panel">
        <div id="confidence-bar">
            <div id="confidence-fill"></div>
        </div>

        <div class="stat">
            <span class="stat-label">Jistota AI:</span>
            <span class="stat-value" id="confidence-val">0%</span>
        </div>

        <div class="stat">
            <span class="stat-label">Status:</span>
            <span class="stat-value" id="status-val">Připraven</span>
        </div>

        <div class="stat">
            <span class="stat-label">Detekce celkem:</span>
            <span class="stat-value" id="total-detections">0</span>
        </div>

        <div class="stat">
            <span class="stat-label">Poslední detekce:</span>
            <span class="stat-value" id="last-detection">—</span>
        </div>
    </div>

    <script>
        const ws = new WebSocket("ws://" + window.location.host + "/ws");
        const indicator = document.getElementById("indicator");
        const statusText = document.getElementById("status-text");
        const fill = document.getElementById("confidence-fill");
        const confidenceVal = document.getElementById("confidence-val");
        const statusVal = document.getElementById("status-val");
        const totalDetections = document.getElementById("total-detections");
        const lastDetection = document.getElementById("last-detection");
        const connectionStatus = document.getElementById("connection-status");

        let detectionCount = 0;
        let audioContext = null;

        ws.onopen = () => {
            console.log("✅ WebSocket připojen");
            connectionStatus.classList.add("connected");
            statusVal.innerText = "Naslouchám...";
        };

        ws.onclose = () => {
            console.log("❌ WebSocket odpojen");
            connectionStatus.classList.remove("connected");
            statusVal.innerText = "Odpojeno";
        };

        ws.onerror = (error) => {
            console.error("❌ WebSocket chyba:", error);
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            const prob = data.probability;

            // Update progress bar
            fill.style.width = (prob * 100) + "%";
            confidenceVal.innerText = (prob * 100).toFixed(1) + "%";

            if (data.detected) {
                // DATEL DETEKOVÁN!
                indicator.classList.add("active");
                statusText.innerText = "DATEL!";
                fill.classList.add("danger");
                statusVal.innerText = "⚠️ DETEKOVÁN";

                detectionCount++;
                totalDetections.innerText = detectionCount;

                const now = new Date();
                lastDetection.innerText = now.toLocaleTimeString();

                // Vibrace (pokud podporováno)
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate([100, 50, 100]);
                }

                // Zvuk (pokud povoleno)
                playAlertSound();

            } else {
                // Klid
                indicator.classList.remove("active");
                statusText.innerText = "KLID";
                fill.classList.remove("danger");
                statusVal.innerText = "Naslouchám...";
            }
        };

        function playAlertSound() {
            try {
                if (!audioContext) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                }
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                oscillator.frequency.value = 800;
                oscillator.type = 'sine';

                gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.3);
            } catch (e) {
                console.warn("Audio nepodporováno:", e);
            }
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
    return {
        "status": "running",
        "model_loaded": model is not None,
        "sample_rate": SAMPLE_RATE,
        "threshold": CONFIDENCE_THRESHOLD
    }

# --- AUDIO PROCESSING ---
def process_realtime_audio(audio_chunk):
    """Převede RAW audio na predikci modelu"""
    try:
        if model is None:
            return 0.0

        # Mel-Spectrogram (stejný postup jako při tréninku)
        mel_spec = librosa.feature.melspectrogram(
            y=audio_chunk,
            sr=SAMPLE_RATE,
            n_mels=N_MELS,
            fmax=8000
        )

        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        # Normalizace
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (
            mel_spec_db.max() - mel_spec_db.min() + 1e-8
        )

        # Reshape pro model
        model_input = mel_spec_norm[np.newaxis, ..., np.newaxis]

        # Predikce
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
                    audio = data[:, 0]  # Mono

                    # Zpracování v thread poolu
                    prob = await loop.run_in_executor(None, process_realtime_audio, audio)

                    detected = prob > CONFIDENCE_THRESHOLD

                    if detected:
                        logger.info(f"🦜 DATEL DETEKOVÁN! (Confidence: {prob*100:.1f}%)")

                    # Odeslání výsledku
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
    ║        🦜 WOODPECKER DETECTOR - REAL-TIME SERVER         ║
    ╚══════════════════════════════════════════════════════════╝

    🚀 Spouštím server...
    📱 Otevři v prohlížeči: http://localhost:8000
    🌐 Z mobilu: http://YOUR_MAC_IP:8000

    Stiskni Ctrl+C pro ukončení
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000)
