# 🦜 Woodpecker Detector - Návod

## ✅ OPRAVA - v3 FIXED

Problém byl, že aplikace naslouchala mikrofonu NA SERVERU (Mac), ne na klientovi (telefon).

**Nová verze v3** správně přijímá audio stream z prohlížeče.

---

## 🚀 Jak používat

### 1. Otevři aplikaci na mobilu
```
http://192.168.10.79:8000
```

### 2. Klikni na tlačítko "🎤 Spustit mikrofon"
- Prohlížeč požádá o povolení mikrofonu
- **POVOL** přístup k mikrofonu
- Tlačítko se změní na "✅ Mikrofon aktivní"

### 3. Sleduj indikátor
- **KLID** = žádný datel
- **DATEL!** = detekován (červené, pulzuje)
- Automaticky se přehraje zvuk reakce

---

## 🎵 Režimy reakce

- **🦅 Dravci** - odstrašení (výchozí)
  - Hlasy jestřábů, sov, káňat

- **🦜 Datli** - přilákání
  - Klepání a volání datlů

- **🔀 Smíšené** - náhodné ze všech

- **🔇 Bez zvuku** - jen detekce, bez přehrávání

---

## 📊 Statistiky

- **Jistota AI** - jak moc si je model jistý (0-100%)
- **Přehráno zvuků** - kolikrát se spustil zvuk
- **Poslední zvuk** - která kategorie hrála naposledy
- **Chunky odeslány** - kolik audio bloků poslal prohlížeč

---

## 🔧 Technické info

### Co je opraveno v v3:
```python
# PŮVODNÍ (špatně):
# Server naslouchal vlastnímu mikrofonu přes sounddevice
with sd.InputStream(...) as stream:
    data, _ = stream.read(BLOCK_SIZE)
    # Audio z MAC mikrofonu!

# NOVÉ (správně):
# Prohlížeč pošle audio přes WebSocket
ws.send(JSON.stringify({
    type: "audio",
    audio: base64_encoded_audio
}))
# Audio z TELEFONU/PC mikrofonu!
```

### Audio pipeline:
1. **JavaScript** - přístup k mikrofonu zařízení
2. **AudioContext** - sampleRate 22050 Hz
3. **ScriptProcessor** - zpracování chunků
4. **WebSocket** - odesílání na server (Base64)
5. **Python server** - dekódování + AI analýza
6. **TensorFlow model** - detekce datla
7. **WebSocket response** - výsledek zpět klientovi
8. **HTML5 Audio** - přehrání reakce

---

## 🎯 Testování

### Test zvuku (bez detekce):
- Klikni "🔊 Test zvuku" - přehraje náhodný zvuk

### Test detekce:
- Spusť mikrofon
- Pískej/zatleskej/klepi - měla by se měnit "Jistota AI"
- Model je trénován na syntetických datech, takže může detekovat i jiné rytmické zvuky

### Debug v konzoli:
- F12 → Console (v prohlížeči)
- Vidíš:
  - "✅ WebSocket připojen"
  - "🎤 Mikrofon aktivní, streaming zahájen"
  - "🔊 Přehráno: predator_hawk predator_hawk_01.mp3"

### Debug na serveru:
```bash
tail -f ~/apps/woodpecker-detector/logs/server_v3_fixed.log
```
- Vidíš:
  - "📱 Nový klient připojen"
  - "📊 Chunk #10, Confidence: 12.3%"
  - "🦜 DATEL DETEKOVÁN! (Confidence: 87.5%)"

---

## 📁 Soubory

```
woodpecker-detector/
├── 5_main_app_FIXED.py      ← HLAVNÍ SERVER (v3)
├── woodpecker_model.keras    ← AI model (100% accuracy)
├── model_metadata.json       ← Info o modelu
├── static/sounds/            ← Zvukové soubory
│   ├── predator_hawk/        (2 MP3)
│   ├── predator_owl/         (1 MP3)
│   ├── predator_buzzard/     (3 MP3)
│   ├── woodpecker_drumming/  (3 MP3)
│   └── woodpecker_calls/     (3 MP3)
├── logs/
│   └── server_v3_fixed.log   ← Aktuální log
└── NAVOD.md                  ← Tento soubor
```

---

## 🐛 Pokud nefunguje

### 1. Mikrofon se nespustí
- Zkontroluj povolení v prohlížeči (Settings → Privacy)
- Zkus jiný prohlížeč (Chrome, Safari)
- Na iPhone: Settings → Safari → Camera & Microphone

### 2. WebSocket se nepřipojí
- Zkontroluj že server běží: `lsof -ti:8000`
- Zkontroluj firewall
- Zkus přes localhost: http://localhost:8000

### 3. Nízká detekce
- Model je trénován na syntetických datech
- Pro produkci potřeba reálná nahrávka datlů
- Zkus hlasitější zvuky

### 4. Zvuky se nepřehrávají
- Zkontroluj hlasitost zařízení
- Zkus "Test zvuku"
- Zkontroluj režim reakce (ne "Bez zvuku")

---

## 🔄 Restart serveru

```bash
# Zastavit
lsof -ti:8000 | xargs kill -9

# Spustit
cd ~/apps/woodpecker-detector
./venv/bin/python3 5_main_app_FIXED.py
```

---

## ✅ Checklist

- [ ] Server běží na portu 8000
- [ ] Otevřel jsem http://192.168.10.79:8000 na mobilu
- [ ] Kliknul jsem "Spustit mikrofon"
- [ ] Povolil jsem přístup k mikrofonu
- [ ] Vidím zelené kolečko (připojeno)
- [ ] Vidím rostoucí číslo "Chunky odeslány"
- [ ] Když dělám hluk, mění se "Jistota AI"
- [ ] Test zvuku funguje

---

Vytvořeno: 2025-11-25
Verze: 3.0 FIXED
AI Model: 100% accuracy on synthetic data
Zvuky: 12 MP3 souborů (3 YouTube + 9 synthetic)
