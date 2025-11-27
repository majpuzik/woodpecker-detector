#!/usr/bin/env python3
"""
Woodpecker Detector - Simple Upload Version
Upload audio file for analysis (works on any device without getUserMedia)
"""
import numpy as np
import librosa
import tensorflow as tf
import os
import random
import io
from datetime import datetime
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
MODEL_PATH = "woodpecker_model.keras"
SAMPLE_RATE = 22050
DURATION = 1.0
N_MELS = 64
CONFIDENCE_THRESHOLD = 0.50
SOUNDS_DIR = "static/sounds"

# Load model
logger.info(f"🧠 Loading AI model: {MODEL_PATH}")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    logger.info("✅ Model loaded")
except Exception as e:
    logger.error(f"❌ Model loading error: {e}")
    model = None

app = FastAPI(title="Woodpecker Detector - Upload")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_sound_categories():
    """Get available sound categories"""
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
    return get_sound_categories()

@app.get("/api/sound/{category}/{filename}")
async def serve_sound(category: str, filename: str):
    file_path = os.path.join(SOUNDS_DIR, category, filename)
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    return FileResponse(file_path, media_type="audio/mpeg")

@app.post("/api/analyze")
async def analyze_audio(file: UploadFile = File(...)):
    """Analyze uploaded audio file"""
    try:
        if model is None:
            return JSONResponse({"error": "Model not loaded"}, status_code=500)

        # Read audio file
        audio_bytes = await file.read()
        audio_data, sr = librosa.load(io.BytesIO(audio_bytes), sr=SAMPLE_RATE, duration=DURATION)

        # Pad or trim
        target_length = int(SAMPLE_RATE * DURATION)
        if len(audio_data) < target_length:
            audio_data = np.pad(audio_data, (0, target_length - len(audio_data)))
        else:
            audio_data = audio_data[:target_length]

        # Mel-spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=audio_data,
            sr=SAMPLE_RATE,
            n_mels=N_MELS,
            fmax=8000
        )

        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (
            mel_spec_db.max() - mel_spec_db.min() + 1e-8
        )

        # Predict
        model_input = mel_spec_norm[np.newaxis, ..., np.newaxis]
        prediction = model.predict(model_input, verbose=0)
        prob = float(prediction[0][0])
        detected = prob > CONFIDENCE_THRESHOLD

        logger.info(f"📊 Analysis: {prob*100:.1f}% - {'WOODPECKER!' if detected else 'no detection'}")

        return {
            "detected": detected,
            "probability": prob,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

HTML = """
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Woodpecker Detector - Upload</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: system-ui, sans-serif;
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
            text-align: center;
        }
        #indicator {
            width: 250px;
            height: 250px;
            border-radius: 50%;
            background: radial-gradient(circle, #1e1e1e, #0a0a0a);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
            box-shadow: 0 0 40px rgba(0,0,0,0.8);
            border: 6px solid #2c2c2c;
            margin: 20px 0;
        }
        #indicator.active {
            background: radial-gradient(circle, #ff3b30, #c41c13);
            box-shadow: 0 0 80px rgba(255, 59, 48, 0.8);
            border-color: #ff8a80;
            transform: scale(1.1);
            animation: pulse 0.6s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1.1); }
            50% { transform: scale(1.15); }
        }
        #status-text {
            font-size: 2.5rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .controls {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 15px;
            width: 100%;
            max-width: 400px;
        }
        button, select, input[type="file"] {
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border: none;
            font-size: 1rem;
            cursor: pointer;
        }
        button {
            background: #ffa726;
            color: #000;
            font-weight: bold;
        }
        button:disabled {
            background: #666;
            cursor: not-allowed;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .stat-value { color: #ffa726; font-weight: bold; }
        #confidence-bar {
            width: 100%;
            height: 15px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            overflow: hidden;
            margin: 15px 0;
        }
        #confidence-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #4caf50, #ffa726, #ff3b30);
            transition: width 0.3s;
        }
        #audio-visualizer {
            width: 100%;
            height: 60px;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            margin: 15px 0;
            position: relative;
            overflow: hidden;
        }
        .bar {
            width: 4px;
            background: #ffa726;
            position: absolute;
            bottom: 0;
            animation: wave 1s ease-in-out infinite;
        }
    </style>
</head>
<body>
    <h1>🦜 Woodpecker Detector</h1>
    <p style="color: #888; margin-bottom: 20px; text-align: center;">Nahrávej zvuk - žádný mikrofon není potřeba!</p>

    <div id="indicator">
        <div id="status-text">READY</div>
    </div>

    <div class="controls">
        <button id="record-btn">🎤 NAHRÁT ZVUK (3s)</button>
        <input type="file" id="file-input" accept="audio/*" style="display: none;">
        <button id="upload-btn">📁 Nebo nahrát soubor</button>

        <div style="margin: 15px 0;">
            <label style="color: #888; font-size: 0.9rem;">Reakce na detekci:</label>
            <select id="response-mode">
                <option value="predators">🦅 Dravci (odstrašení)</option>
                <option value="woodpecker">🦜 Datli (přilákání)</option>
                <option value="mixed">🔀 Smíšené</option>
                <option value="silent">🔇 Bez zvuku</option>
            </select>
        </div>

        <div id="confidence-bar">
            <div id="confidence-fill"></div>
        </div>

        <div class="stat">
            <span>Jistota AI:</span>
            <span class="stat-value" id="confidence-val">0%</span>
        </div>

        <div class="stat">
            <span>Přehráno zvuků:</span>
            <span class="stat-value" id="sounds-played">0</span>
        </div>

        <div class="stat">
            <span>Poslední zvuk:</span>
            <span class="stat-value" id="last-sound">—</span>
        </div>
    </div>

    <script>
        const indicator = document.getElementById("indicator");
        const statusText = document.getElementById("status-text");
        const recordBtn = document.getElementById("record-btn");
        const uploadBtn = document.getElementById("upload-btn");
        const fileInput = document.getElementById("file-input");
        const responseMode = document.getElementById("response-mode");
        const fill = document.getElementById("confidence-fill");
        const confidenceVal = document.getElementById("confidence-val");
        const soundsPlayed = document.getElementById("sounds-played");
        const lastSound = document.getElementById("last-sound");

        let soundCategories = {};
        let playCount = 0;
        let mediaRecorder = null;

        // Load sounds
        fetch("/api/sounds")
            .then(r => r.json())
            .then(data => {
                soundCategories = data;
                console.log("✅ Sounds loaded:", Object.keys(soundCategories));
            });

        // Record audio
        recordBtn.addEventListener("click", async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                const chunks = [];

                mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
                mediaRecorder.onstop = async () => {
                    const blob = new Blob(chunks, { type: 'audio/webm' });
                    await analyzeAudio(blob);
                    stream.getTracks().forEach(t => t.stop());
                };

                recordBtn.textContent = "⏺️ NAHRÁVÁM...";
                recordBtn.disabled = true;
                statusText.textContent = "RECORDING";

                mediaRecorder.start();
                setTimeout(() => {
                    mediaRecorder.stop();
                    recordBtn.textContent = "🎤 NAHRÁT ZVUK (3s)";
                    recordBtn.disabled = false;
                }, 3000);

            } catch (err) {
                alert("Mikrofon nedostupný: " + err.message);
            }
        });

        // Upload file
        uploadBtn.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", async (e) => {
            if (e.target.files.length > 0) {
                await analyzeAudio(e.target.files[0]);
            }
        });

        // Analyze audio
        async function analyzeAudio(blob) {
            statusText.textContent = "ANALYZING";
            const formData = new FormData();
            formData.append("file", blob);

            try {
                const response = await fetch("/api/analyze", {
                    method: "POST",
                    body: formData
                });

                const data = await response.json();
                const prob = data.probability;

                fill.style.width = (prob * 100) + "%";
                confidenceVal.textContent = (prob * 100).toFixed(1) + "%";

                if (data.detected) {
                    indicator.classList.add("active");
                    statusText.textContent = "DATEL!";
                    playResponseSound();

                    setTimeout(() => {
                        indicator.classList.remove("active");
                        statusText.textContent = "READY";
                    }, 3000);
                } else {
                    statusText.textContent = "NO BIRD";
                    setTimeout(() => {
                        statusText.textContent = "READY";
                    }, 2000);
                }

            } catch (err) {
                console.error("Analysis error:", err);
                alert("Chyba analýzy: " + err);
                statusText.textContent = "ERROR";
            }
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
            const file = files[Math.floor(Math.random() * files.length)];

            const audio = new Audio(`/api/sound/${category}/${file}`);
            audio.volume = 0.8;
            audio.play()
                .then(() => {
                    playCount++;
                    soundsPlayed.textContent = playCount;
                    lastSound.textContent = category.replace(/_/g, ' ');
                    console.log("🔊 Playing:", category, file);
                })
                .catch(err => console.error("Play error:", err));
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(HTML)

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     🦜 WOODPECKER DETECTOR - SIMPLE UPLOAD VERSION       ║
    ╚══════════════════════════════════════════════════════════╝

    🚀 HTTP server (funguje VŠUDE!)
    📱 http://localhost:8000
    🌐 http://192.168.10.79:8000

    ✅ Nahrávání zvuku - ŽÁDNÉ HTTPS!
    ✅ Funguje na všech zařízeních

    Ctrl+C = stop
    """)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
