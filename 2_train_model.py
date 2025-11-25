#!/usr/bin/env python3
"""
Woodpecker Detector - AI Model Trainer
Trénuje CNN model pro rozpoznávání klepání datla
"""
import os
import numpy as np
import librosa
import tensorflow as tf
from sklearn.model_selection import train_test_split
from pathlib import Path
import json
from datetime import datetime

# Nastavení
DATASET_DIR = "dataset"
SAMPLE_RATE = 22050
DURATION = 1.0  # Délka vzorku v sekundách
N_MELS = 64
MODEL_PATH = "woodpecker_model.keras"
METADATA_PATH = "model_metadata.json"

def preprocess_audio(file_path):
    """Převede audio soubor na mel-spektrogram"""
    try:
        # Načtení zvuku
        y, sr = librosa.load(file_path, sr=SAMPLE_RATE, duration=DURATION)

        # Padding pokud je kratší
        target_length = int(SAMPLE_RATE * DURATION)
        if len(y) < target_length:
            y = np.pad(y, (0, target_length - len(y)))
        else:
            y = y[:target_length]

        # Mel-Spectrogram
        mel_spec = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_mels=N_MELS,
            fmax=8000
        )

        # Logaritmická škála
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        # Normalizace 0-1
        mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-8)

        return mel_spec_norm[..., np.newaxis]  # Přidání kanálu

    except Exception as e:
        print(f"❌ Chyba u {file_path}: {e}")
        return None

def load_dataset():
    """Načte a zpracuje všechny audio soubory"""
    X = []
    y = []
    labels = {"noise": 0, "woodpecker": 1}

    print("\n📂 Načítám a zpracovávám audio soubory...")

    for label_name, label_idx in labels.items():
        dir_path = os.path.join(DATASET_DIR, label_name)

        if not os.path.exists(dir_path):
            print(f"⚠️  Složka {dir_path} neexistuje!")
            continue

        files = [f for f in os.listdir(dir_path) if f.endswith(('.mp3', '.wav'))]
        print(f"\n{'='*60}")
        print(f"🏷️  Třída: {label_name.upper()} (Label: {label_idx})")
        print(f"📁 Souborů: {len(files)}")

        for i, fname in enumerate(files):
            if i % 10 == 0:
                print(f"   Zpracováno: {i}/{len(files)}", end='\r')

            spec = preprocess_audio(os.path.join(dir_path, fname))
            if spec is not None:
                X.append(spec)
                y.append(label_idx)

        print(f"   ✅ Zpracováno: {len(files)}/{len(files)}")

    return np.array(X), np.array(y)

def create_model(input_shape):
    """Vytvoří CNN model"""
    model = tf.keras.models.Sequential([
        tf.keras.layers.Input(shape=input_shape),

        # Convolutional Block 1
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Dropout(0.25),

        # Convolutional Block 2
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Dropout(0.25),

        # Convolutional Block 3
        tf.keras.layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Dropout(0.25),

        # Dense Layers
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(256, activation='relu'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(1, activation='sigmoid')  # Binary classification
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]
    )

    return model

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║          🧠 WOODPECKER DETECTOR - AI TRAINER             ║
    ║           Trénink neuronové sítě pro detekci            ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    # Načtení dat
    X, y = load_dataset()

    if len(X) == 0:
        print("\n❌ Žádná data k tréninku! Spusť nejprve 1_download_dataset.py")
        return

    print(f"\n{'='*60}")
    print(f"📊 Dataset statistika:")
    print(f"   Celkem vzorků: {len(X)}")
    print(f"   Datli: {np.sum(y == 1)}")
    print(f"   Šum: {np.sum(y == 0)}")
    print(f"   Shape: {X[0].shape}")
    print(f"{'='*60}")

    # Rozdělení na train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\n✂️  Rozdělení dat:")
    print(f"   Train: {len(X_train)} vzorků")
    print(f"   Test:  {len(X_test)} vzorků")

    # Vytvoření modelu
    print(f"\n🏗️  Vytvářím CNN model...")
    model = create_model(X[0].shape)

    print("\n📋 Architektura modelu:")
    model.summary()

    # Callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3,
            min_lr=0.00001
        )
    ]

    # Trénink
    print(f"\n{'='*60}")
    print("🚀 ZAHAJUJI TRÉNINK...")
    print(f"{'='*60}\n")

    history = model.fit(
        X_train, y_train,
        epochs=25,
        batch_size=16,
        validation_data=(X_test, y_test),
        callbacks=callbacks,
        verbose=1
    )

    # Evaluace
    print(f"\n{'='*60}")
    print("📊 FINÁLNÍ EVALUACE")
    print(f"{'='*60}")

    test_loss, test_acc, test_prec, test_rec = model.evaluate(X_test, y_test, verbose=0)

    print(f"\n✅ Test Accuracy:  {test_acc*100:.2f}%")
    print(f"✅ Test Precision: {test_prec*100:.2f}%")
    print(f"✅ Test Recall:    {test_rec*100:.2f}%")
    print(f"✅ Test Loss:      {test_loss:.4f}")

    # Uložení modelu
    print(f"\n💾 Ukládám model...")
    model.save(MODEL_PATH)

    # Metadata
    metadata = {
        "created": datetime.now().isoformat(),
        "sample_rate": SAMPLE_RATE,
        "duration": DURATION,
        "n_mels": N_MELS,
        "input_shape": list(X[0].shape),
        "training_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "test_accuracy": float(test_acc),
        "test_precision": float(test_prec),
        "test_recall": float(test_rec),
        "epochs_trained": len(history.history['loss'])
    }

    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║                   ✅ TRÉNINK DOKONČEN                    ║
    ╠══════════════════════════════════════════════════════════╣
    ║  💾 Model:        {MODEL_PATH}                  ║
    ║  📄 Metadata:     {METADATA_PATH}            ║
    ║  🎯 Přesnost:     {test_acc*100:.1f}%                                   ║
    ╚══════════════════════════════════════════════════════════╝

    Další krok: uvicorn 3_main_app:app --host 0.0.0.0 --port 8000
    """)

if __name__ == "__main__":
    main()
