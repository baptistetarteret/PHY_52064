import pyaudio
import numpy as np
from flask import Flask, jsonify
import threading

app = Flask(__name__)

# --- CONFIGURATION AUDIO ---
RATE = 48000
CHUNK = 2048
DEVICE_INDEX = 0
NB_BARRES = 16  # Nombre de zones de fréquences

# Stockage des données pour le web
bars_data = [0] * NB_BARRES

def audio_processor():
    global bars_data
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=pyaudio.paInt32, channels=2, rate=RATE,
                        input=True, input_device_index=DEVICE_INDEX,
                        frames_per_buffer=CHUNK)
        
        while True:
            raw = stream.read(CHUNK, exception_on_overflow=False)
            audio = np.frombuffer(raw, dtype=np.int32)[::2].astype(np.float32)
            
            # Calcul de la FFT
            fft_mag = np.abs(np.fft.rfft(audio * np.hanning(len(audio))))
            
            # On regroupe par bandes (Bass, Mid, High)
            groupes = np.array_split(fft_mag, NB_BARRES)
            
            # Conversion en pourcentage pour l'affichage (0 à 100%)
            temp_bars = []
            for g in groupes:
                # Moyenne et conversion log (dB)
                lvl = 20 * np.log10(np.mean(g) / (2**23) + 1e-10)
                # On mappe -80dB -> 0% et -20dB -> 100%
                val = np.clip(np.interp(lvl, [-70, -15], [0, 100]), 0, 100)
                temp_bars.append(int(val))
            
            bars_data = temp_bars
    except Exception as e:
        print(f"Erreur audio: {e}")

# Lancement de l'audio en arrière-plan
threading.Thread(target=audio_processor, daemon=True).start()

# --- INTERFACE HTML UNIQUE ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Micro Monitor</title>
    <style>
        body { background: #000; color: #fff; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .grid { display: flex; align-items: flex-end; height: 150px; gap: 8px; }
        .bar { width: 25px; background: #0f0; border-radius: 3px; transition: height 0.05s; box-shadow: 0 0 10px #0f0; }
        h2 { font-weight: 200; color: #888; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h2>MICROPHONE EN DIRECT</h2>
    <div class="grid" id="viz"></div>
    <script>
        const viz = document.getElementById('viz');
        for(let i=0; i<16; i++) {
            let b = document.createElement('div');
            b.className = 'bar'; b.id = 'b'+i;
            viz.appendChild(b);
        }
        setInterval(async () => {
            try {
                const res = await fetch('/data');
                const data = await res.json();
                data.forEach((v, i) => document.getElementById('b'+i).style.height = v + 'px');
            } catch(e) {}
        }, 50);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_PAGE

@app.route('/data')
def get_data():
    return jsonify(bars_data)

if __name__ == '__main__':
    print("Serveur lancé sur http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)