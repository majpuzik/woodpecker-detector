#!/usr/bin/env python3
"""
🦜 WOODPECKER DETECTOR - PROFESSIONAL FINAL VERSION
Real-time audio detection with professional features
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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
MODEL_PATH = "woodpecker_model.keras"
SAMPLE_RATE = 22050
N_MELS = 64
CONFIDENCE_THRESHOLD = 0.40  # SNÍŽENO pro vyšší citlivost!
SOUNDS_DIR = "static/sounds"

# Load AI model
logger.info(f"🧠 Loading model: {MODEL_PATH}")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    logger.info("✅ Model ready")
except Exception as e:
    logger.error(f"❌ Model error: {e}")
    model = None

app = FastAPI(title="Woodpecker Detector PRO")
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
        "model_loaded": model is not None,
        "threshold": CONFIDENCE_THRESHOLD,
        "sound_categories": list(get_sound_categories().keys())
    }

def detect_drumming_onset(audio_float32, sr=SAMPLE_RATE):
    """Fast onset-based drumming detection - detects both drumming & foraging (< 0.1s)"""
    try:
        duration = len(audio_float32) / sr

        # PRE-CHECK: Minimum RMS to avoid detecting noise
        rms = np.sqrt(np.mean(audio_float32**2))
        if rms < 0.015:  # Too quiet to be woodpecker (after 15x amplification)
            return False, 0.0

        # Onset strength envelope
        onset_env = librosa.onset.onset_strength(
            y=audio_float32,
            sr=sr,
            aggregate=np.median,
            fmax=8000,
            n_mels=64,
            hop_length=512
        )

        # Peak picking - STRICTER parameters to avoid false positives
        peaks = librosa.util.peak_pick(
            onset_env,
            pre_max=5, post_max=5,
            pre_avg=10, post_avg=10,
            delta=0.6,  # Increased from 0.4 - peaks must be more prominent
            wait=8      # Increased from 6 - more spacing between peaks
        )

        # Minimum 2 peaks to avoid random noise
        if len(peaks) < 2:
            return False, 0.0

        # Calculate rate
        rate = len(peaks) / duration

        # Calculate regularity (if enough peaks)
        if len(peaks) >= 2:
            peak_times = librosa.frames_to_time(peaks, sr=sr, hop_length=512)
            intervals = np.diff(peak_times)
            if len(intervals) > 0:
                regularity = np.std(intervals) / np.mean(intervals)
            else:
                regularity = 1.0
        else:
            regularity = 1.0

        # DRUMMING (teritoriální): 10-38 hits/s, může být nepravidelné (research-based)
        if 10 <= rate <= 38:
            if regularity <= 0.40:  # Allow irregularities as per research
                confidence = min(0.95, 0.6 + (1.0 - regularity) * 0.4)
                logger.info(f"🥁 DRUMMING: {rate:.1f} hits/s, reg={regularity:.2f}, rms={rms:.4f}")
                return True, confidence

        # FORAGING (pomalé klepání): 3-9 hits/s (narrowed from 2-10)
        # Requires at least 2 peaks in 0.36s window
        if 3 <= rate <= 9 and len(peaks) >= 2:
            # Must have some regularity (not completely random)
            if regularity <= 0.50:  # Allow more irregularity than drumming
                confidence = min(0.75, 0.5 + (rate / 20.0))
                logger.info(f"🔨 FORAGING: {rate:.1f} hits/s, reg={regularity:.2f}, rms={rms:.4f}")
                return True, confidence

        return False, 0.0

    except Exception as e:
        return False, 0.0

def analyze_audio(audio_float32):
    """Professional onset-based woodpecker drumming detection"""
    try:
        rms = np.sqrt(np.mean(audio_float32**2))
        max_amp = np.max(np.abs(audio_float32))

        # Ignore silence
        if rms < 0.001:
            return 0.0

        logger.info(f"🎵 Audio: len={len(audio_float32)}, RMS={rms:.4f}, max={max_amp:.4f}")

        # ONLY onset detection - AI model was overfitted garbage
        onset_detected, onset_conf = detect_drumming_onset(audio_float32)
        if onset_detected:
            logger.info(f"🥁 WOODPECKER DRUMMING: {onset_conf*100:.1f}%")
            return float(onset_conf)

        return 0.0

    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return 0.0

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Professional WebSocket handler with error recovery"""
    await websocket.accept()
    client_id = id(websocket)
    logger.info(f"📱 Client connected: {client_id}")

    chunk_count = 0
    detection_count = 0

    try:
        while True:
            try:
                # Receive audio data
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # Increased timeout for stable connection
                )

                message = json.loads(data)

                if message.get("type") == "audio":
                    chunk_count += 1

                    # Decode base64 audio
                    audio_b64 = message.get("audio")
                    audio_bytes = base64.b64decode(audio_b64)
                    audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                    audio_float32 = audio_int16.astype(np.float32) / 32768.0

                    # AMPLIFY 15x for Android microphone (AI model should handle this)
                    audio_float32 = np.clip(audio_float32 * 15.0, -1.0, 1.0)

                    # AI analysis
                    prob = analyze_audio(audio_float32)
                    detected = prob > CONFIDENCE_THRESHOLD

                    if detected:
                        detection_count += 1
                        logger.info(f"🦜 DETECTION #{detection_count}! Confidence: {prob*100:.1f}%")

                    # Send result (convert numpy types to Python types for JSON)
                    await websocket.send_text(json.dumps({
                        "detected": bool(detected),
                        "probability": float(prob),
                        "chunk": chunk_count,
                        "detections": detection_count,
                        "timestamp": datetime.now().isoformat()
                    }))

                    # Log every 20 chunks
                    if chunk_count % 20 == 0:
                        logger.info(f"📊 Processed {chunk_count} chunks, {detection_count} detections")

                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except asyncio.TimeoutError:
                logger.warning(f"⏱️  Timeout for client {client_id} - no data for 30s")
                await websocket.send_text(json.dumps({"type": "timeout"}))
                # Don't break - continue listening for reconnection

    except WebSocketDisconnect:
        logger.info(f"📱 Client disconnected: {client_id} ({chunk_count} chunks, {detection_count} detections)")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
    finally:
        logger.info(f"📱 Session ended: {client_id}")

# ===== PROFESSIONAL HTML INTERFACE =====
HTML = """<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <title>🦜 Woodpecker Detector PRO</title>
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
            font-size: 2rem;
            color: #ffa726;
            margin-bottom: 10px;
            text-align: center;
            letter-spacing: 1px;
        }
        .subtitle {
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 20px;
            text-align: center;
        }
        #indicator {
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: radial-gradient(circle, #1e1e1e, #0a0a0a);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 0 50px rgba(0,0,0,0.9);
            border: 8px solid #2c2c2c;
            margin: 20px 0;
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
            font-size: 2.8rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 4px;
        }
        #confidence-text {
            font-size: 1.2rem;
            margin-top: 10px;
            color: #ffa726;
        }
        .connection-status {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 15px;
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
            padding: 25px;
            border-radius: 20px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        button {
            width: 100%;
            padding: 18px;
            margin: 10px 0;
            border-radius: 12px;
            border: none;
            font-size: 1.1rem;
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
            margin: 10px 0;
        }
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 1rem;
        }
        .stat-label { color: #888; }
        .stat-value {
            font-weight: bold;
            color: #ffa726;
            font-family: "Courier New", monospace;
        }
        #confidence-bar {
            width: 100%;
            height: 14px;
            background: rgba(0,0,0,0.4);
            border-radius: 7px;
            overflow: hidden;
            margin: 15px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
        }
        #confidence-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #4caf50, #ffa726, #ff3b30);
            transition: width 0.2s ease-out;
            box-shadow: 0 0 10px rgba(255,167,38,0.5);
        }
        .error-msg {
            background: rgba(255, 59, 48, 0.2);
            border: 2px solid #ff3b30;
            border-radius: 10px;
            padding: 15px;
            margin: 15px 0;
            display: none;
        }
        .error-msg.show { display: block; animation: shake 0.5s; }
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }
    </style>
</head>
<body>
    <h1>🦜 WOODPECKER DETECTOR PRO</h1>
    <p class="subtitle">Professional Real-Time Detection System</p>

    <div id="https-warning" style="display: none; background: rgba(255,152,0,0.2); border: 2px solid #ffa726; border-radius: 10px; padding: 15px; margin: 15px 0; max-width: 400px;">
        <strong>⚠️ ANDROID WARNING:</strong><br>
        Microphone requires HTTPS!<br>
        Use: <strong>https://192.168.10.79:8000</strong>
    </div>

    <div class="connection-status">
        <div class="status-dot" id="status-dot"></div>
        <span id="status-label">Disconnected</span>
    </div>

    <div id="indicator">
        <div id="status-text">READY</div>
        <div id="confidence-text">0.0%</div>
    </div>

    <div class="controls">
        <button id="start-btn">🎤 START DETECTION</button>

        <div class="error-msg" id="error-msg">
            <strong>⚠️ Error:</strong> <span id="error-text"></span>
        </div>

        <div style="margin: 15px 0;">
            <label style="color: #888; font-size: 0.9rem;">Response Mode:</label>
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
            <span class="stat-label">Chunks Processed:</span>
            <span class="stat-value" id="chunks-count">0</span>
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
        const COOLDOWN_MS = 15000;  // 15s to prevent feedback loop
        let muteUntil = 0;  // Timestamp to mute detection after playback
        let pingInterval = null;

        // Show HTTPS warning if on HTTP
        if (window.location.protocol === 'http:') {
            document.getElementById('https-warning').style.display = 'block';
        }

        const indicator = document.getElementById("indicator");
        const statusText = document.getElementById("status-text");
        const confidenceText = document.getElementById("confidence-text");
        const startBtn = document.getElementById("start-btn");
        const statusDot = document.getElementById("status-dot");
        const statusLabel = document.getElementById("status-label");
        const fill = document.getElementById("confidence-fill");
        const confidenceVal = document.getElementById("confidence-val");
        const detectionsCount = document.getElementById("detections-count");
        const soundsPlayed = document.getElementById("sounds-played");
        const chunksCount = document.getElementById("chunks-count");
        const lastSound = document.getElementById("last-sound");
        const responseMode = document.getElementById("response-mode");
        const errorMsg = document.getElementById("error-msg");
        const errorText = document.getElementById("error-text");

        // Load sounds
        fetch("/api/sounds")
            .then(r => r.json())
            .then(data => {
                soundCategories = data;
                console.log("✅ Sounds loaded:", Object.keys(soundCategories));
            });

        function showError(msg) {
            errorText.textContent = msg;
            errorMsg.classList.add("show");
            setTimeout(() => errorMsg.classList.remove("show"), 5000);
        }

        function connectWebSocket() {
            const wsUrl = wsProtocol + "//" + window.location.host + "/ws";
            console.log("🔗 Connecting to WebSocket:", wsUrl);

            try {
                ws = new WebSocket(wsUrl);
            } catch (err) {
                console.error("❌ Failed to create WebSocket:", err);
                showError("WebSocket creation failed: " + err.message);
                return;
            }

            ws.onopen = () => {
                statusDot.classList.add("connected");
                statusLabel.textContent = "Connected";
                console.log("✅ WebSocket connected successfully");

                // Send initial ping immediately to confirm connection
                setTimeout(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: "ping" }));
                        console.log("🏓 Initial ping sent");
                    }
                }, 50);

                // Setup periodic ping to keep connection alive
                if (pingInterval) clearInterval(pingInterval);
                pingInterval = setInterval(() => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({ type: "ping" }));
                        console.log("🏓 Keep-alive ping sent");
                    }
                }, 4000);  // Send ping every 4 seconds (before server timeout)
            };

            ws.onclose = (event) => {
                statusDot.classList.remove("connected", "recording");
                statusLabel.textContent = "Disconnected";
                console.log("❌ WebSocket disconnected. Code:", event.code, "Reason:", event.reason);

                // Clear ping interval
                if (pingInterval) {
                    clearInterval(pingInterval);
                    pingInterval = null;
                }

                if (isRecording) {
                    stopDetection();
                }
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.chunk) {
                    chunksCount.textContent = data.chunk;
                }

                if (data.detections !== undefined) {
                    detectionsCount.textContent = data.detections;
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
                        // Check mute period first (to prevent detecting own playback)
                        if (now < muteUntil) {
                            console.log("🔇 Detection muted (playback protection)");
                        } else if (now - lastDetectionTime > COOLDOWN_MS) {
                            lastDetectionTime = now;
                            playResponseSound();
                            // Mute for 3 seconds after starting playback
                            muteUntil = now + 3000;
                        }

                        if (navigator.vibrate) {
                            navigator.vibrate([100, 50, 100]);
                        }

                        setTimeout(() => {
                            if (!data.detected) {
                                indicator.classList.remove("active");
                                statusText.textContent = "LISTENING";
                            }
                        }, 1000);
                    } else {
                        indicator.classList.remove("active");
                        statusText.textContent = "LISTENING";
                    }
                }
            };

            ws.onerror = (error) => {
                console.error("❌ WebSocket error:", error);
                showError("WebSocket connection error");
            };
        }

        async function checkMicrophonePermission() {
            try {
                const result = await navigator.permissions.query({name: 'microphone'});
                console.log('🎤 Microphone permission:', result.state);
                return result.state;
            } catch (err) {
                console.log('⚠️ Permissions API not supported, trying directly');
                return 'unknown';
            }
        }

        async function startDetection() {
            try {
                // Check permission first
                const permissionState = await checkMicrophonePermission();
                if (permissionState === 'denied') {
                    showError('Mikrofon zamítnut! Povol v nastavení prohlížeče → Weby → Oprávnění');
                    return;
                }

                // Request microphone with modern API
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        sampleRate: 22050,
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: true
                    }
                });

                // Connect WebSocket first and wait for connection
                connectWebSocket();

                // Wait for WebSocket to open with shorter timeout
                let connectionAttempts = 0;
                while ((!ws || ws.readyState !== WebSocket.OPEN) && connectionAttempts < 30) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                    connectionAttempts++;
                    console.log("⏳ Waiting for WebSocket...", connectionAttempts);
                }

                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    console.error("❌ WebSocket failed to connect after 3 seconds");
                    showError("WebSocket připojení selhalo - zkus znovu");
                    stream.getTracks().forEach(t => t.stop());
                    return;
                }

                console.log("✅ WebSocket connected, starting audio processing");

                audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 22050 });
                const source = audioContext.createMediaStreamSource(stream);

                // Use ScriptProcessor for real-time
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                let buffer = [];
                const targetLength = 8000;  // 0.36s chunks - AI model trained on this

                let firstChunkSent = false;
                let chunksSent = 0;

                processor.onaudioprocess = (e) => {
                    if (!isRecording) {
                        console.log("⚠️ Not recording anymore, stopping processor");
                        return;
                    }

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
                            // Convert bytes to base64 safely (avoid stack overflow on large arrays)
                            let binary = '';
                            for (let i = 0; i < bytes.length; i++) {
                                binary += String.fromCharCode(bytes[i]);
                            }
                            const b64 = btoa(binary);

                            try {
                                ws.send(JSON.stringify({
                                    type: "audio",
                                    audio: b64
                                }));

                                chunksSent++;
                                if (!firstChunkSent) {
                                    firstChunkSent = true;
                                    console.log("🎵 First audio chunk sent to server!");
                                }
                                if (chunksSent % 10 === 0) {
                                    console.log(`📊 Sent ${chunksSent} chunks`);
                                }
                            } catch (err) {
                                console.error("❌ Failed to send audio chunk:", err);
                            }
                        }
                    } else {
                        console.log("⚠️ WebSocket not ready, state:", ws ? ws.readyState : "null");
                    }
                };

                source.connect(processor);
                processor.connect(audioContext.destination);

                isRecording = true;
                statusDot.classList.add("recording");
                statusText.textContent = "LISTENING";
                startBtn.textContent = "⏹️ STOP DETECTION";
                startBtn.classList.add("active");
                mediaRecorder = { stream, processor, source };

                console.log("🎤 Detection started");

            } catch (err) {
                console.error("❌ Microphone error:", err);

                let errorMsg = "Chyba mikrofonu: ";
                if (err.name === 'NotAllowedError') {
                    errorMsg += "Přístup zamítnut! Povol v nastavení.";
                } else if (err.name === 'NotFoundError') {
                    errorMsg += "Mikrofon nenalezen!";
                } else if (err.name === 'NotReadableError') {
                    errorMsg += "Mikrofon používá jiná aplikace!";
                } else if (err.name === 'SecurityError') {
                    errorMsg += "⚠️ HTTPS vyžadováno! Použ https://";
                } else {
                    errorMsg += err.message;
                }

                showError(errorMsg);

                // If HTTPS error, show special message
                if (window.location.protocol === 'http:') {
                    showError('⚠️ ANDROID VYŽADUJE HTTPS! Použij: https://192.168.10.79:8000');
                }
            }
        }

        function stopDetection() {
            if (mediaRecorder) {
                if (mediaRecorder.stream) {
                    mediaRecorder.stream.getTracks().forEach(t => t.stop());
                }
                if (mediaRecorder.processor) {
                    mediaRecorder.processor.disconnect();
                }
                if (mediaRecorder.source) {
                    mediaRecorder.source.disconnect();
                }
            }
            if (audioContext) {
                audioContext.close();
            }
            if (pingInterval) {
                clearInterval(pingInterval);
                pingInterval = null;
            }
            if (ws) {
                ws.close();
            }

            isRecording = false;
            statusDot.classList.remove("recording");
            statusText.textContent = "READY";
            startBtn.textContent = "🎤 START DETECTION";
            startBtn.classList.remove("active");
            mediaRecorder = null;

            console.log("⏹️ Detection stopped");
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
    import os.path

    # Check for SSL certificates
    ssl_keyfile = "ssl/key.pem"
    ssl_certfile = "ssl/cert.pem"
    use_ssl = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)

    protocol = "https" if use_ssl else "http"

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║      🦜 WOODPECKER DETECTOR - PROFESSIONAL HTTPS         ║
    ╚══════════════════════════════════════════════════════════╝

    🚀 Real-time detection system
    🔒 Protocol: {protocol.upper()}
    📱 {protocol}://localhost:8000
    🌐 {protocol}://192.168.10.79:8000

    ⚡ Features:
    - Real-time AI detection (40% threshold)
    - Professional WebSocket streaming
    - HTTPS support for Android
    - Permissions API integration
    - Error recovery & auto-reconnect
    - Sound response system

    ⚠️  ANDROID USERS:
    1. Open: {protocol}://192.168.10.79:8000
    2. Accept self-signed certificate warning
    3. Allow microphone permission
    4. Click START DETECTION

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
        logger.warning("⚠️ Running without HTTPS - microphone may not work on Android!")
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
