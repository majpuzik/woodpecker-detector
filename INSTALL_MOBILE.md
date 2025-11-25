# 📱 Instalace na mobil (PWA)

## Krok 1: Spusť server na Macu

```bash
cd ~/apps/woodpecker-detector
./start.sh
```

Poznamenej si IP adresu, například: **192.168.10.79**

---

## Krok 2: Otevři v mobilu

### Android (Chrome):
1. Otevři Chrome
2. Zadej: `http://192.168.10.79:8000`
3. Tap na ⋮ (3 tečky) → **Add to Home screen**
4. Pojmenuj: "Woodpecker"
5. Tap **Add**

✅ Ikona se objeví na ploše jako aplikace!

### iPhone (Safari):
1. Otevři Safari
2. Zadej: `http://192.168.10.79:8000`
3. Tap na 📤 (Share) tlačítko
4. Scroll dolů → **Add to Home Screen**
5. Pojmenuj: "Woodpecker"
6. Tap **Add**

✅ Ikona se objeví na ploše!

---

## 🎯 Jak to funguje?

Po přidání na plochu:
- Aplikace se otevře **bez browser UI** (vypadá jako nativní aplikace)
- **Ikona 🦜** na ploše
- **Splash screen** při spouštění
- **Standalone mode** - celá obrazovka

---

## 🔧 Troubleshooting

### "Cannot connect"
- Zkontroluj, že Mac i mobil jsou na **stejné WiFi**
- Zkontroluj, že server běží: `./start.sh`
- Zkus restartovat server

### "Manifest error"
- Refreshni stránku (Pull down v mobilu)
- Zkus znovu Add to Home Screen

### "No audio"
- Uděl browseru povolení k mikrofonu
- Chrome → Settings → Site settings → Microphone

---

## 💡 Tipy

- **Fullscreen:** Aplikace běží v celé obrazovce (standalone mode)
- **Offline:** Aplikace potřebuje připojení k serveru na Macu
- **Notifikace:** Zatím nejsou implementovány (přijdou v příští verzi)

---

## 🌐 Alternativa: Bez instalace

Prostě otevři v browseru:
```
http://192.168.10.79:8000
```

Funguje stejně, jen nemáš ikonu na ploše.
