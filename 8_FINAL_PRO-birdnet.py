#!/usr/bin/env python3
"""
🦜 WOODPECKER DETECTOR - BIRDNET AI VERSION
Real-time bird species identification using BirdNET
Cornell Lab of Ornithology + TU Chemnitz
"""
import numpy as np
import asyncio
import json
import os
import random
import base64
import tempfile
import soundfile as sf
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
SAMPLE_RATE = 22050
BUFFER_DURATION = 3.0  # BirdNET requires 3-second chunks
BUFFER_SIZE = int(SAMPLE_RATE * BUFFER_DURATION)  # 66150 samples
CONFIDENCE_THRESHOLD = 0.25  # Minimum confidence for woodpecker detection
SOUNDS_DIR = "static/sounds"

# Target woodpecker species (Czech Great Spotted Woodpecker)
WOODPECKER_SPECIES = [
    "Great Spotted Woodpecker",
    "Lesser Spotted Woodpecker",
    "Middle Spotted Woodpecker",
    "White-backed Woodpecker",
    "Black Woodpecker",
    "European Green Woodpecker",
    "Grey-headed Woodpecker",
    "Eurasian Wryneck"
]

# Initialize BirdNET analyzer
logger.info("🧠 Initializing BirdNET analyzer...")
try:
    analyzer = Analyzer()
    logger.info("✅ BirdNET ready")
except Exception as e:
    logger.error(f"❌ BirdNET initialization error: {e}")
    analyzer = None

app = FastAPI(title="Woodpecker Detector BirdNET")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_sound_categories():
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
        return {"error": "Not found"}
    return FileResponse(file_path, media_type="audio/mpeg")

@app.get("/api/status")
async def status():
    return {
        "status": "running",
        "model": "BirdNET",
        "analyzer_loaded": analyzer is not None,
        "threshold": CONFIDENCE_THRESHOLD,
        "buffer_duration": BUFFER_DURATION,
        "sound_categories": list(get_sound_categories().keys())
    }

def analyze_with_birdnet(audio_float32, sr=SAMPLE_RATE):
    """
    Analyze audio using BirdNET for species identification
    Returns: (is_woodpecker, confidence, species_name)
    """
    if analyzer is None:
        return False, 0.0, None

    try:
        # Pre-check: Minimum RMS to avoid analyzing silence
        rms = np.sqrt(np.mean(audio_float32**2))
        if rms < 0.015:  # Too quiet
            return False, 0.0, None

        # Save audio to temporary file (BirdNET requires file input)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            sf.write(tmp_path, audio_float32, sr)

        try:
            # Analyze with BirdNET
            recording = Recording(
                analyzer,
                tmp_path,
                min_conf=0.10  # Low threshold to see all detections
            )
            recording.analyze()

            # Check for woodpecker detections
            best_woodpecker = None
            best_confidence = 0.0

            if recording.detections:
                logger.info(f"🐦 BirdNET found {len(recording.detections)} bird(s)")

                for detection in recording.detections:
                    common_name = detection.get('common_name', '')
                    confidence = detection.get('confidence', 0.0)

                    logger.info(f"   - {common_name}: {confidence*100:.1f}%")

                    # Check if it's ANY woodpecker (European or American)
                    # Keywords: woodpecker, sapsucker (woodpecker family), wryneck
                    woodpecker_keywords = ['woodpecker', 'sapsucker', 'wryneck', 'dendrocopos', 'picoides']
                    if any(keyword in common_name.lower() for keyword in woodpecker_keywords):
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_woodpecker = common_name

            # Cleanup temp file
            os.unlink(tmp_path)

            if best_woodpecker and best_confidence > CONFIDENCE_THRESHOLD:
                logger.info(f"🥁 WOODPECKER DETECTED: {best_woodpecker} ({best_confidence*100:.1f}%)")
                return True, best_confidence, best_woodpecker

            return False, 0.0, None

        except Exception as e:
            logger.error(f"❌ BirdNET analysis error: {e}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return False, 0.0, None

    except Exception as e:
        logger.error(f"❌ Audio processing error: {e}")
        return False, 0.0, None

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket handler with 3-second audio buffering for BirdNET"""
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"📱 Client connected: {client_id}")

    chunk_count = 0
    detection_count = 0
    audio_buffer = []  # Buffer to accumulate 3 seconds of audio
    last_species = None

    try:
        while True:
            try:
                # Receive audio data
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                message = json.loads(data)

                if message.get("type") == "audio":
                    chunk_count += 1

                    # Decode base64 audio
                    audio_b64 = message.get("audio")
                    audio_bytes = base64.b64decode(audio_b64)
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                    audio_float32 = audio_int16.astype(np.float32) / 32768.0

                    # AMPLIFY 15x for Android microphone
                    audio_float32 = np.clip(audio_float32 * 15.0, -1.0, 1.0)

                    # Add to buffer
                    audio_buffer.extend(audio_float32)

                    # Check if we have 3 seconds of audio
                    if len(audio_buffer) >= BUFFER_SIZE:
                        # Extract 3-second chunk
                        chunk_3s = np.array(audio_buffer[:BUFFER_SIZE])
                        audio_buffer = audio_buffer[BUFFER_SIZE:]  # Remove processed audio

                        logger.info(f"🎵 Analyzing 3s chunk (buffer: {len(audio_buffer)} samples remaining)")

                        # Analyze with BirdNET
                        is_woodpecker, confidence, species = analyze_with_birdnet(chunk_3s)

                        if is_woodpecker:
                            detection_count += 1
                            last_species = species
                            logger.info(f"🦜 DETECTION #{detection_count}! {species}: {confidence*100:.1f}%")

                        # Send result
                        await websocket.send_text(json.dumps({
                            "detected": bool(is_woodpecker),
                            "probability": float(confidence) if confidence else 0.0,
                            "species": species if species else "—",
                            "chunk": chunk_count,
                            "detections": detection_count,
                            "buffer_size": len(audio_buffer),
                            "timestamp": datetime.now().isoformat()
                        }))
                    else:
                        # Still buffering, send status update
                        buffer_progress = (len(audio_buffer) / BUFFER_SIZE) * 100
                        await websocket.send_text(json.dumps({
                            "detected": False,
                            "probability": 0.0,
                            "species": "Buffering...",
                            "chunk": chunk_count,
                            "detections": detection_count,
                            "buffer_progress": buffer_progress,
                            "buffer_size": len(audio_buffer),
                            "timestamp": datetime.now().isoformat()
                        }))

                    # Log every 20 chunks
                    if chunk_count % 20 == 0:
                        logger.info(f"📊 Processed {chunk_count} chunks, {detection_count} detections, buffer: {len(audio_buffer)}")

                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except asyncio.TimeoutError:
                logger.warning(f"⏱️  Timeout for client {client_id}")
                await websocket.send_text(json.dumps({"type": "timeout"}))

    except WebSocketDisconnect:
        logger.info(f"📱 Client disconnected: {client_id} ({chunk_count} chunks, {detection_count} detections)")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        logger.info(f"📱 Session ended: {client_id}")

# ===== HTML INTERFACE =====
HTML = """<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>🦜 Woodpecker Detector BirdNET</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            overflow-x: hidden;
        }
        h1 {
            font-size: 1.8rem;
            color: #ffa726;
            margin-bottom: 5px;
            text-align: center;
            letter-spacing: 1px;
        }
        .subtitle {
            color: #888;
            font-size: 0.85rem;
            margin-bottom: 15px;
            text-align: center;
        }
        #indicator {
            width: 260px;
            height: 260px;
            border-radius: 50%;
            background: radial-gradient(circle, #1e1e1e, #0a0a0a);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 0 50px rgba(0,0,0,0.9);
            border: 8px solid #2c2c2c;
            margin: 15px 0;
            position: relative;
        }
        #indicator.active {
            background: radial-gradient(circle, #ff3b30, #c41c13);
            box-shadow: 0 0 100px rgba(255, 59, 48, 0.9);
            border-color: #ff8a80;
            transform: scale(1.15);
            animation: pulse 0.5s ease-in-out infinite;
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
        #species-text {
            font-size: 0.9rem;
            margin-top: 8px;
            color: #4caf50;
            text-align: center;
            max-width: 220px;
        }
        #confidence-text {
            font-size: 1.1rem;
            margin-top: 5px;
            color: #ffa726;
        }
        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }
        .status-dot {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #666;
            transition: all 0.3s;
        }
        .status-dot.connected { background: #4caf50; box-shadow: 0 0 15px #4caf50; }
        .status-dot.recording { background: #ff3b30; animation: blink 1s infinite; }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

        .controls {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 20px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        button {
            width: 100%;
            padding: 16px;
            margin: 8px 0;
            border-radius: 12px;
            border: none;
            font-size: 1.05rem;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        #start-btn {
            background: linear-gradient(135deg, #ffa726, #ff6f00);
            color: #000;
        }
        #start-btn:disabled {
            background: #555;
            cursor: not-allowed;
        }
        #start-btn.active {
            background: linear-gradient(135deg, #ff3b30, #c41c13);
            color: #fff;
            animation: btnPulse 1s infinite;
        }
        @keyframes btnPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }
        select {
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1rem;
            margin: 8px 0;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 0.95rem;
        }
        .stat-label { color: #888; }
        .stat-value {
            font-weight: bold;
            color: #ffa726;
            font-family: "Courier New", monospace;
        }
        #confidence-bar {
            width: 100%;
            height: 12px;
            background: rgba(0,0,0,0.4);
            border-radius: 6px;
            overflow: hidden;
            margin: 12px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
        }
        #confidence-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #4caf50, #ffa726, #ff3b30);
            transition: width 0.2s ease-out;
            box-shadow: 0 0 10px rgba(255,167,38,0.5);
        }
        .badge {
            display: inline-block;
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid #4caf50;
            color: #4caf50;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <h1>🦜 WOODPECKER DETECTOR</h1>
    <p class="subtitle">
        <span class="badge">🧠 BirdNET AI</span>
        Professional Species Identification
    </p>

    <div class="connection-status">
        <div class="status-dot" id="status-dot"></div>
        <span id="status-label">Disconnected</span>
    </div>

    <div id="indicator">
        <div id="status-text">READY</div>
        <div id="species-text" style="display: none;">—</div>
        <div id="confidence-text">0.0%</div>
    </div>

    <div class="controls">
        <button id="start-btn">🎤 START DETECTION</button>

        <div style="margin: 12px 0;">
            <label style="color: #888; font-size: 0.85rem;">Response Mode:</label>
            <select id="response-mode">
                <option value="predators">🦅 Predators (scare away)</option>
                <option value="woodpecker">🦜 Woodpeckers (attract)</option>
                <option value="mixed">🔀 Mixed</option>
                <option value="silent">🔇 Silent</option>
            </select>
        </div>

        <div id="confidence-bar">
            <div id="confidence-fill"></div>
        </div>

        <div class="stat">
            <span class="stat-label">Species:</span>
            <span class="stat-value" id="species-val">—</span>
        </div>

        <div class="stat">
            <span class="stat-label">AI Confidence:</span>
            <span class="stat-value" id="confidence-val">0.0%</span>
        </div>

        <div class="stat">
            <span class="stat-label">Detections:</span>
            <span class="stat-value" id="detections-count">0</span>
        </div>

        <div class="stat">
            <span class="stat-label">Sounds Played:</span>
            <span class="stat-value" id="sounds-played">0</span>
        </div>

        <div class="stat">
            <span class="stat-label">Buffer:</span>
            <span class="stat-value" id="buffer-status">0%</span>
        </div>

        <div class="stat">
            <span class="stat-label">Last Sound:</span>
            <span class="stat-value" id="last-sound">—</span>
        </div>
    </div>

    <script>
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let ws = null;
        let mediaRecorder = null;
        let audioContext = null;
        let isRecording = false;
        let soundCategories = {};
        let playCount = 0;
        let lastDetectionTime = 0;
        const COOLDOWN_MS = 15000;  // 15s cooldown
        let muteUntil = 0;
        let pingInterval = null;

        const indicator = document.getElementById("indicator");
        const statusText = document.getElementById("status-text");
        const speciesText = document.getElementById("species-text");
        const confidenceText = document.getElementById("confidence-text");
        const startBtn = document.getElementById("start-btn");
        const statusDot = document.getElementById("status-dot");
        const statusLabel = document.getElementById("status-label");
        const fill = document.getElementById("confidence-fill");
        const confidenceVal = document.getElementById("confidence-val");
        const speciesVal = document.getElementById("species-val");
        const detectionsCount = document.getElementById("detections-count");
        const soundsPlayed = document.getElementById("sounds-played");
        const bufferStatus = document.getElementById("buffer-status");
        const lastSound = document.getElementById("last-sound");
        const responseMode = document.getElementById("response-mode");

        // Load sounds
        fetch("/api/sounds")
            .then(r => r.json())
            .then(data => {
                soundCategories = data;
                console.log("✅ Sounds loaded:", Object.keys(soundCategories));
            });

        function connectWebSocket() {
            const wsUrl = wsProtocol + "//" + window.location.host + "/ws";
            console.log("🔗 Connecting to:", wsUrl);

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                statusDot.classList.add("connected");
                statusLabel.textContent = "Connected";
                console.log("✅ WebSocket connected");

                // Periodic ping
                if (pingInterval) clearInterval(pingInterval);
                pingInterval = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: "ping" }));
                    }
                }, 4000);
            };

            ws.onclose = () => {
                statusDot.classList.remove("connected", "recording");
                statusLabel.textContent = "Disconnected";
                if (pingInterval) clearInterval(pingInterval);
                if (isRecording) stopDetection();
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                // Update buffer progress
                if (data.buffer_progress !== undefined) {
                    bufferStatus.textContent = data.buffer_progress.toFixed(0) + "%";
                }

                if (data.detections !== undefined) {
                    detectionsCount.textContent = data.detections;
                }

                if (data.species) {
                    speciesVal.textContent = data.species;
                    speciesText.textContent = data.species;
                    if (data.species !== "—" && data.species !== "Buffering...") {
                        speciesText.style.display = "block";
                    }
                }

                const prob = data.probability;
                if (prob !== undefined) {
                    fill.style.width = (prob * 100) + "%";
                    confidenceVal.textContent = (prob * 100).toFixed(1) + "%";
                    confidenceText.textContent = (prob * 100).toFixed(1) + "%";

                    if (data.detected) {
                        indicator.classList.add("active");
                        statusText.textContent = "BIRD!";

                        const now = Date.now();
                        if (now < muteUntil) {
                            console.log("🔇 Detection muted");
                        } else if (now - lastDetectionTime > COOLDOWN_MS) {
                            lastDetectionTime = now;
                            playResponseSound();
                            muteUntil = now + 3000;
                        }

                        if (navigator.vibrate) {
                            navigator.vibrate([100, 50, 100]);
                        }

                        setTimeout(() => {
                            indicator.classList.remove("active");
                            statusText.textContent = "LISTENING";
                        }, 1000);
                    } else {
                        indicator.classList.remove("active");
                        statusText.textContent = "LISTENING";
                    }
                }
            };

            ws.onerror = (error) => {
                console.error("❌ WebSocket error:", error);
            };
        }

        async function startDetection() {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        sampleRate: 22050,
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: true
                    }
                });

                connectWebSocket();

                // Wait for WebSocket
                let attempts = 0;
                while ((!ws || ws.readyState !== WebSocket.OPEN) && attempts < 30) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                    attempts++;
                }

                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    console.error("❌ WebSocket failed");
                    stream.getTracks().forEach(t => t.stop());
                    return;
                }

                audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 22050 });
                const source = audioContext.createMediaStreamSource(stream);
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                let buffer = [];
                const targetLength = 8000;

                processor.onaudioprocess = (e) => {
                    if (!isRecording) return;

                    if (ws && ws.readyState === WebSocket.OPEN) {
                        const inputData = e.inputBuffer.getChannelData(0);
                        buffer.push(...inputData);

                        if (buffer.length >= targetLength) {
                            const chunk = buffer.slice(0, targetLength);
                            buffer = buffer.slice(targetLength);

                            const int16 = new Int16Array(chunk.length);
                            for (let i = 0; i < chunk.length; i++) {
                                int16[i] = Math.max(-32768, Math.min(32767, chunk[i] * 32768));
                            }

                            const bytes = new Uint8Array(int16.buffer);
                            let binary = '';
                            for (let i = 0; i < bytes.length; i++) {
                                binary += String.fromCharCode(bytes[i]);
                            }
                            const b64 = btoa(binary);

                            ws.send(JSON.stringify({
                                type: "audio",
                                audio: b64
                            }));
                        }
                    }
                };

                source.connect(processor);
                processor.connect(audioContext.destination);

                isRecording = true;
                statusDot.classList.add("recording");
                statusText.textContent = "BUFFERING";
                startBtn.textContent = "⏹️ STOP DETECTION";
                startBtn.classList.add("active");
                mediaRecorder = { stream, processor, source };

                console.log("🎤 Detection started");

            } catch (err) {
                console.error("❌ Microphone error:", err);
            }
        }

        function stopDetection() {
            if (mediaRecorder) {
                if (mediaRecorder.stream) mediaRecorder.stream.getTracks().forEach(t => t.stop());
                if (mediaRecorder.processor) mediaRecorder.processor.disconnect();
                if (mediaRecorder.source) mediaRecorder.source.disconnect();
            }
            if (audioContext) audioContext.close();
            if (pingInterval) clearInterval(pingInterval);
            if (ws) ws.close();

            isRecording = false;
            statusDot.classList.remove("recording");
            statusText.textContent = "READY";
            speciesText.style.display = "none";
            startBtn.textContent = "🎤 START DETECTION";
            startBtn.classList.remove("active");
            mediaRecorder = null;
        }

        startBtn.addEventListener("click", () => {
            if (isRecording) {
                stopDetection();
            } else {
                startDetection();
            }
        });

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
            audio.volume = 0.9;
            audio.play()
                .then(() => {
                    playCount++;
                    soundsPlayed.textContent = playCount;
                    lastSound.textContent = category.replace(/_/g, ' ');
                    console.log("🔊 Playing:", category, file);
                })
                .catch(err => console.error("❌ Play error:", err));
        }
    </script>
</body>
</html>"""

@app.get("/")
async def get():
    return HTMLResponse(HTML)

if __name__ == "__main__":
    import uvicorn

    # Check for SSL certificates
    ssl_keyfile = "ssl/key.pem"
    ssl_certfile = "ssl/cert.pem"
    use_ssl = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)

    protocol = "https" if use_ssl else "http"

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║      🦜 WOODPECKER DETECTOR - BIRDNET AI VERSION         ║
    ╚══════════════════════════════════════════════════════════╝

    🧠 AI Model: BirdNET (Cornell Lab + TU Chemnitz)
    🔒 Protocol: {protocol.upper()}
    📱 {protocol}://localhost:8000
    🌐 {protocol}://192.168.10.79:8000

    ⚡ Features:
    - Professional bird species identification
    - 3-second audio buffering for accuracy
    - Real-time WebSocket streaming
    - HTTPS support for Android
    - Sound response system
    - 8 woodpecker species detection

    🦜 Target Species:
    - Great Spotted Woodpecker (Dendrocopos major)
    - Lesser Spotted, Middle Spotted, White-backed
    - Black Woodpecker, Green Woodpecker
    - Grey-headed Woodpecker, Eurasian Wryneck

    ⚠️  Note: 3-second latency due to BirdNET requirements

    Press Ctrl+C to stop
    """)

    if use_ssl:
        logger.info("🔒 Running with HTTPS (Android compatible)")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        logger.warning("⚠️ Running without HTTPS")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
