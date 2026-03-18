import pyaudio
import numpy as np
from flask import Flask, jsonify
import threading

app = Flask(__name__)

# --- CONFIGURATION TECHNIQUE ---
RATE = 48000
CHUNK = 4096  # Haute résolution
DEVICE_INDEX = 0
SENSITIVITY_REF = 2**23  # Référence 24-bit du INMP441

# Stockage global
fft_shared = []
freq_labels = []

def audio_processor():
    global fft_shared, freq_labels
    p = pyaudio.PyAudio()
    
    # Pré-calcul des fréquences pour l'axe X
    freq_labels = np.fft.rfftfreq(CHUNK, 1/RATE).astype(int).tolist()
    
    try:
        stream = p.open(format=pyaudio.paInt32, channels=2, rate=RATE,
                        input=True, input_device_index=DEVICE_INDEX,
                        frames_per_buffer=CHUNK)
        
        while True:
            raw = stream.read(CHUNK, exception_on_overflow=False)
            # Canal gauche et conversion float
            audio = np.frombuffer(raw, dtype=np.int32)[::2].astype(np.float32)
            
            # Fenêtrage de Blackman pour éviter les fuites de fréquence
            windowed = audio * np.blackman(len(audio))
            
            # FFT
            fft_mag = np.abs(np.fft.rfft(windowed))
            
            # Conversion dBFS (Logarithmique)
            # Normalisation par rapport au max et à la taille du CHUNK
            fft_db = 20 * np.log10((fft_mag / (SENSITIVITY_REF * (CHUNK/2))) + 1e-12)
            
            # On limite à la plage utile du micro
            fft_shared = np.clip(fft_db, -100, 0).tolist()
            
    except Exception as e:
        print(f"Erreur : {e}")

threading.Thread(target=audio_processor, daemon=True).start()

# --- INTERFACE HTML + CHART.JS (Sans fichiers externes) ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>FFT Precise Pi 5</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background: #080808; color: #00ff41; font-family: monospace; margin: 0; overflow: hidden; }
        .header { padding: 10px; border-bottom: 1px solid #111; text-align: center; }
        canvas { width: 95vw !important; height: 80vh !important; margin: auto; }
    </style>
</head>
<body>
    <div class="header">FFT HAUTE PRÉCISION - INMP441 | 11.7 Hz / point</div>
    <canvas id="fftChart"></canvas>

    <script>
        const ctx = document.getElementById('fftChart').getContext('2d');
        let chart;

        async function init() {
            const res = await fetch('/data');
            const data = await res.json();

            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Amplitude (dBFS)',
                        data: data.db,
                        borderColor: '#00ff41',
                        borderWidth: 1.5,
                        pointRadius: 0,
                        fill: false,
                        tension: 0.1
                    }]
                },
                options: {
                    animation: false,
                    responsive: true,
                    scales: {
                        x: { 
                            type: 'logarithmic', 
                            min: 60, max: 20000,
                            title: { display: true, text: 'Fréquence (Hz)', color: '#00ff41' },
                            ticks: { color: '#00ff41' },
                            grid: { color: '#222' }
                        },
                        y: { 
                            min: -100, max: 0,
                            title: { display: true, text: 'Niveau (dBFS)', color: '#00ff41' },
                            ticks: { color: '#00ff41' },
                            grid: { color: '#222' }
                        }
                    }
                }
            });
            update();
        }

        async function update() {
            try {
                const res = await fetch('/data');
                const data = await res.json();
                chart.data.datasets[0].data = data.db;
                chart.update('none');
            } catch(e) {}
            requestAnimationFrame(update);
        }
        init();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return HTML_PAGE

@app.route('/data')
def get_data():
    return jsonify({"db": fft_shared, "labels": freq_labels})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)