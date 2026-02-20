import pyaudio
import numpy as np
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION CALIBRÉE ---
RATE = 48000
CHUNK = 4096        # Précision de 11.7 Hz
FORMAT = pyaudio.paInt32
CHANNELS = 2
DEVICE_INDEX = 0    # Ton index fonctionnel
SENSITIVITY_REF = 2**23 # Référence 24-bit (8.38M)

fft_shared = []
freq_labels = []

def audio_processor():
    global fft_shared, freq_labels
    p = pyaudio.PyAudio()
    
    # Pré-calcul des fréquences pour l'axe X
    freq_labels = np.fft.rfftfreq(CHUNK, 1/RATE).astype(int).tolist()
    
    try:
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                        input=True, input_device_index=DEVICE_INDEX,
                        frames_per_buffer=CHUNK)
        
        while True:
            # Lecture des données I2S
            raw = stream.read(CHUNK, exception_on_overflow=False)
            # Conversion 32-bit et sélection du canal GAUCHE (L/R -> GND)
            audio = np.frombuffer(raw, dtype=np.int32)[::2].astype(np.float32)
            
            # Fenêtrage de Blackman pour une FFT nette
            windowed = audio * np.blackman(len(audio))
            
            # Calcul FFT (Magnitude)
            fft_mag = np.abs(np.fft.rfft(windowed))
            
            # Conversion en dBFS (Calibré : 0dB = saturation, -26dB = 94dB SPL)
            # On divise par CHUNK pour normaliser l'énergie de la FFT
            fft_db = 20 * np.log10((fft_mag / (SENSITIVITY_REF * (CHUNK/2))) + 1e-12)
            
            # Clipping propre selon le bruit de fond (-87dBFS selon specs)
            fft_shared = np.clip(fft_db, -100, 0).tolist()
            
    except Exception as e:
        print(f"Erreur Audio : {e}")

threading.Thread(target=audio_processor, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    return jsonify({"db": fft_shared, "labels": freq_labels})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)