from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pyaudio
import numpy as np
import threading

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION EXPERTE ---
RATE = 48000        # Fréquence optimale pour le HPF du INMP441
CHUNK = 4096        # Haute résolution : 48000 / 4096 = 11.7 Hz de précision
FORMAT = pyaudio.paInt32
CHANNELS = 2
SENSITIVITY_REF = 2**23 # 24-bit max pour le INMP441

fft_output = []
freq_labels = []

def audio_processor():
    global fft_output, freq_labels
    p = pyaudio.PyAudio()
    
    # Génération des étiquettes de fréquence une seule fois
    freq_labels = np.fft.rfftfreq(CHUNK, 1/RATE).astype(int).tolist()
    
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                    input=True, frames_per_buffer=CHUNK)
    
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Récupération canal gauche et passage en float
            audio_data = np.frombuffer(data, dtype=np.int32)[::2].astype(np.float32)
            
            # Fenêtrage de haute qualité (Blackman pour réduire les lobes secondaires)
            windowed = audio_data * np.blackman(len(audio_data))
            
            # FFT
            fft_raw = np.abs(np.fft.rfft(windowed))
            
            # Conversion en dBFS (selon datasheet : -26dBFS @ 94dB SPL)
            # On normalise par rapport au max théorique 24-bit
            fft_db = 20 * np.log10((fft_raw / SENSITIVITY_REF) + 1e-12)
            
            # On limite à la plage dynamique du micro (EIN à -87 dBFS)
            fft_db = np.clip(fft_db, -100, 0)
            
            fft_output = fft_db.tolist()
        except Exception as e:
            print(f"Erreur : {e}")
            continue

threading.Thread(target=audio_processor, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html') # On va créer un fichier séparé pour le HTML

@app.route('/data')
def get_data():
    return jsonify({"db": fft_output, "labels": freq_labels})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)