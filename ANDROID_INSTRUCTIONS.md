# 📱 ANDROID NÁVOD - HTTPS Mikrofon

## ✅ SERVER BĚŽÍ (PID: 35185)

**HTTPS URL:** https://192.168.10.79:8000

---

## 🔒 JAK POVOLIT NA ANDROIDU:

### KROK 1: Otevři URL
```
https://192.168.10.79:8000
```

### KROK 2: Povol Self-Signed Certifikát

**Chrome:**
1. Uvidíš: "Your connection is not private" / "Vaše připojení není soukromé"
2. Klikni: **"Advanced"** / **"Pokročilé"**
3. Klikni: **"Proceed to 192.168.10.79 (unsafe)"** / **"Pokračovat"**

**Firefox:**
1. Uvidíš: "Warning: Potential Security Risk"
2. Klikni: **"Advanced"**
3. Klikni: **"Accept the Risk and Continue"**

**Samsung Internet:**
1. Uvidíš varování certifikátu
2. Klikni: **"Pokračovat"** nebo **"Přijmout riziko"**

### KROK 3: Povol Mikrofon

1. Uvidíš tmavou stránku s velkým černým kruhem
2. Klikni: **"🎤 START DETECTION"**
3. Prohlížeč se zeptá: **"Allow microphone?"**
4. Klikni: **"ALLOW"** / **"POVOLIT"**

### KROK 4: Funguje!

- Status se změní na **"LISTENING"**
- Zelená tečka = připojeno
- Červená pulzující = nahrává
- Když detekuje zvuk → červený kruh + zvuk

---

## ❌ POKUD NEFUNGUJE:

### Problem 1: "Mikrofon zamítnut"

**Řešení:**
1. Chrome → Menu (⋮) → **Settings**
2. **Site Settings** → **Microphone**
3. Najdi **192.168.10.79** → **Allow**

NEBO:

1. Chrome → otevři stránku
2. Klikni na **"ikonu zámku"** vedle URL
3. **Permissions** → **Microphone** → **Allow**

### Problem 2: "Mikrofon není k dispozici"

**Android nastavení:**
1. Settings → **Apps** → **Chrome**
2. **Permissions** → **Microphone** → **Allow**

### Problem 3: "SecurityError - HTTPS required"

- Ujisti se že používáš **https://** (NE http://)
- URL: `https://192.168.10.79:8000` ✅
- URL: `http://192.168.10.79:8000` ❌

### Problem 4: Certifikát se stále nepřijímá

**Hard reset:**
1. Chrome → Settings → Privacy → **Clear browsing data**
2. Zaškrtni: **Cookies** + **Cached images**
3. Clear data
4. Zavři Chrome úplně (Force stop v nastavení)
5. Otevři znovu a zkus URL

---

## 🔍 DEBUG:

### Zkontroluj Console (vývojářská konzole):

**Chrome Android:**
1. Připoj telefon k PC přes USB
2. Na PC: Chrome → `chrome://inspect/#devices`
3. Najdi svůj telefon → **Inspect**
4. Vidíš JavaScript console

**Co hledat:**
- ✅ `🎤 Microphone permission: granted`
- ✅ `✅ WebSocket connected`
- ✅ `🎤 Detection started`

**Chyby:**
- ❌ `NotAllowedError` = Musíš povolit v nastavení
- ❌ `NotFoundError` = Mikrofon nenalezen
- ❌ `SecurityError` = Použij HTTPS
- ❌ `NotReadableError` = Mikrofon používá jiná app

---

## 📊 CO VIDÍŠ NA STRÁNCE:

```
🦜 WOODPECKER DETECTOR PRO
Professional Real-Time Detection System

⚠️ ANDROID WARNING:           ← Pokud vidíš tohle, jsi na HTTP!
Microphone requires HTTPS!      Přepni na https://
Use: https://192.168.10.79:8000

🟢 Connected                   ← Zelená = WebSocket OK
🔴 Recording                   ← Červená = nahrává

[VELKÝ ČERNÝ KRUH]
    LISTENING                  ← Status
    0.0%                       ← AI confidence

[🎤 START DETECTION]          ← Hlavní tlačítko

Response Mode: 🦅 Predators

AI Confidence: 45.2%          ← Real-time %
Detections: 3                 ← Kolik datlů detekováno
Sounds Played: 3              ← Kolik zvuků přehráno
Chunks Processed: 142         ← Zpracované audio bloky
```

---

## 🎯 SPRÁVNÉ FUNGOVÁNÍ:

1. **Otevřeš:** https://192.168.10.79:8000
2. **Povolíš certifikát** (1x)
3. **Klikneš START DETECTION**
4. **Povolíš mikrofon** (1x)
5. **Status:** "LISTENING" + zelená tečka
6. **Červená tečka pulzuje** = nahrává
7. **"Chunks Processed"** roste (každou sekundu +1)
8. **"AI Confidence"** se mění podle zvuků
9. **Při detekci:** kruh zčervená + přehraje se zvuk

---

## 🔧 DALŠÍ TIPY:

- **Mikrofon citlivost:** AutoGainControl = true (automaticky zesiluje)
- **AI threshold:** 40% (nízké = citlivější)
- **Cooldown:** 2 sekundy mezi přehráními
- **Sample rate:** 22050 Hz
- **Buffer:** 4096 samples

---

## 📞 POKUD STÁLE NEFUNGUJE:

1. Zkus jiný prohlížeč (Chrome → Firefox)
2. Restartuj telefon
3. Zkus jinou WiFi síť
4. Zkontroluj že jsi na stejné síti jako Mac (192.168.10.x)
5. Ping test: `ping 192.168.10.79` z telefonu

---

**Vytvořeno:** 2025-11-25
**Verze:** 7_FINAL_PRO.py
**Protocol:** HTTPS s self-signed certifikát
**Port:** 8000
