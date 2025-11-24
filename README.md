# 🦜 Woodpecker Detector

AI-powered real-time woodpecker drumming detection system using deep learning.

**Features:**
- 🎯 Real-time audio detection
- 🧠 CNN-based AI model (TensorFlow)
- 📱 Mobile-friendly web interface
- 🔊 Automatic dataset download from Xeno-canto
- 📊 Confidence scoring and statistics

---

## 🚀 Quick Start

### 1. Installation

```bash
cd ~/apps/woodpecker-detector

# Install dependencies
pip install -r requirements.txt

# macOS: Install PortAudio for audio input
brew install portaudio
```

### 2. Download Training Data

```bash
python 1_download_dataset.py
```

This will automatically download:
- 50 woodpecker drumming samples
- 50 background noise samples (forest ambience)

### 3. Train AI Model

```bash
python 2_train_model.py
```

Training takes 5-10 minutes. Output:
- `woodpecker_model.keras` - Trained model
- `model_metadata.json` - Model statistics

### 4. Run Detection Server

```bash
python 3_main_app.py
# Or with uvicorn:
uvicorn 3_main_app:app --host 0.0.0.0 --port 8000
```

### 5. Open Web Interface

**Desktop:**
```
http://localhost:8000
```

**Mobile (same WiFi):**
```
http://YOUR_MAC_IP:8000
```

Find Mac IP: `System Settings → Network`

---

## 📊 How It Works

### Audio Processing Pipeline

```
Microphone Input (22050 Hz)
    ↓
Mel-Spectrogram Conversion
    ↓
Normalized 64-band Mel-Spectrogram
    ↓
CNN Model (3 Conv Blocks + Dense)
    ↓
Binary Classification (0-1 probability)
    ↓
Threshold Check (75% confidence)
    ↓
WebSocket → Mobile GUI
```

### Model Architecture

```python
Input: (64, 44, 1)  # Mel-spectrogram

Conv2D(32) → BatchNorm → MaxPool → Dropout
Conv2D(64) → BatchNorm → MaxPool → Dropout
Conv2D(128) → BatchNorm → MaxPool → Dropout
Dense(256) → BatchNorm → Dropout
Dense(1, sigmoid)

Output: Probability [0.0 - 1.0]
```

### Dataset

- **Source:** [Xeno-canto](https://xeno-canto.org/) - world's largest community database of bird sounds
- **Species:** *Dendrocopos* (Great Spotted Woodpecker)
- **Type:** Drumming recordings (A-quality)
- **Negative samples:** *Parus* (Tit) songs

---

## 🎨 Web Interface

The mobile interface features:
- 🔴 **Real-time indicator** - Turns red when woodpecker detected
- 📊 **Confidence bar** - Visual probability meter
- 📈 **Statistics panel** - Detection count, timestamps
- 🔊 **Audio alert** - Beep sound on detection
- 📳 **Vibration** - Haptic feedback (mobile only)

---

## ⚙️ Configuration

Edit variables in `3_main_app.py`:

```python
SAMPLE_RATE = 22050           # Audio sample rate (Hz)
DURATION = 1.0                # Analysis window (seconds)
N_MELS = 64                   # Mel-spectrogram bands
CONFIDENCE_THRESHOLD = 0.75   # Detection threshold (0-1)
```

**Threshold tuning:**
- `0.5` - Very sensitive (more false positives)
- `0.75` - Balanced (recommended)
- `0.9` - Very strict (may miss some detections)

---

## 📁 Project Structure

```
woodpecker-detector/
├── dataset/
│   ├── woodpecker/          # Positive samples (MP3)
│   └── noise/               # Negative samples (MP3)
├── logs/                    # Application logs
├── 1_download_dataset.py    # Dataset downloader
├── 2_train_model.py         # Model trainer
├── 3_main_app.py            # FastAPI server + GUI
├── requirements.txt         # Python dependencies
├── woodpecker_model.keras   # Trained model (generated)
├── model_metadata.json      # Training stats (generated)
└── README.md
```

---

## 🧪 Testing

### Test Model Accuracy

```bash
python 2_train_model.py
# Check output for:
# - Test Accuracy
# - Test Precision
# - Test Recall
```

### Test Real-time Detection

1. Start server: `python 3_main_app.py`
2. Open browser: `http://localhost:8000`
3. Tap on desk near microphone (simulates drumming)
4. Watch indicator turn red

### API Health Check

```bash
curl http://localhost:8000/api/status
```

---

## 🛠️ Troubleshooting

### "No module named 'sounddevice'"

```bash
brew install portaudio
pip install sounddevice
```

### "Model file not found"

Run training first:
```bash
python 2_train_model.py
```

### "No audio input detected"

Check microphone permissions:
```bash
# macOS
System Settings → Privacy & Security → Microphone
# Enable Terminal/Python
```

### Poor detection accuracy

1. Download more data (increase `limit=50` to `limit=100` in script 1)
2. Retrain model (script 2)
3. Lower threshold to 0.6 in `3_main_app.py`

---

## 📚 Technical Details

### Audio Features

- **Sample Rate:** 22.05 kHz (standard for speech/music)
- **Window Size:** 1 second (22,050 samples)
- **Feature Extraction:** Mel-frequency cepstral coefficients
- **Frequency Range:** 0-8000 Hz

### Model Training

- **Architecture:** Convolutional Neural Network (CNN)
- **Optimizer:** Adam (lr=0.001)
- **Loss:** Binary Crossentropy
- **Metrics:** Accuracy, Precision, Recall
- **Regularization:** Dropout (0.25-0.5), BatchNormalization
- **Callbacks:** Early Stopping, ReduceLROnPlateau

### Performance

- **Latency:** ~100ms (detection to display)
- **CPU Usage:** ~30% (MacBook Pro M4)
- **Memory:** ~500MB (model + audio buffers)

---

## 🔮 Future Improvements

- [ ] Species classification (multiple woodpecker types)
- [ ] Audio recording of detections
- [ ] Daily/weekly statistics dashboard
- [ ] Push notifications (via Telegram/Discord)
- [ ] Raspberry Pi deployment
- [ ] LoRaWAN remote monitoring
- [ ] Battery-powered field station

---

## 📖 References

- [Xeno-canto API Documentation](https://xeno-canto.org/explore/api)
- [Librosa Documentation](https://librosa.org/)
- [TensorFlow Audio Tutorial](https://www.tensorflow.org/tutorials/audio/simple_audio)

---

## 📄 License

Private project - Not for public distribution

---

## 👤 Author

majpuzik

---

**Version:** 1.0.0
**Created:** 2025-11-15
**Platform:** macOS (Apple Silicon)
