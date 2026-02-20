from flask import Flask, render_template, jsonify
from flask_cors import CORS
import pyaudio
import numpy as np
import threading

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION AUDIO ---
CHUNK = 1024
FORMAT = pyaudio.paInt32
CHANNELS = 2
RATE = 44100
fft_output = []

def audio_processor():
    global fft_output
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                    input=True, frames_per_buffer=CHUNK)
    
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int32)[::2]
            # Calcul FFT
            windowed = audio_data * np.hanning(len(audio_data))
            fft_data = np.abs(np.fft.rfft(windowed))
            # On réduit un peu la taille pour le web (on prend 128 points)
            fft_output = np.interp(np.linspace(0, len(fft_data), 128), 
                                   np.arange(len(fft_data)), fft_data).tolist()
        except:
            continue

# Lancer la capture dans un thread séparé
threading.Thread(target=audio_processor, daemon=True).start()

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pi 5 - INMP441 Analyzer</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="background: #111; color: white; font-family: sans-serif; text-align: center;">
        <h1>Analyseur FFT Temps Réel</h1>
        <canvas id="fftChart" width="800" height="400"></canvas>
        <script>
            const ctx = document.getElementById('fftChart').getContext('2d');
            const chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Array.from({length: 128}, (_, i) => Math.round(i * 22050 / 128) + "Hz"),
                    datasets: [{ label: 'Amplitude', data: [], backgroundColor: '#00f2ff' }]
                },
                options: { 
                    animation: false,
                    scales: { y: { beginAtZero: true, max: 200000000, display: false }, x: { ticks: { color: 'white' } } }
                }
            });

            async function updateData() {
                const response = await fetch('/data');
                const data = await response.json();
                chart.data.datasets[0].data = data;
                chart.update();
                requestAnimationFrame(updateData);
            }
            updateData();
        </script>
    </body>
    </html>
    """

@app.route('/data')
def get_data():
    return jsonify(fft_output)

if __name__ == '__main__':
    # '0.0.0.0' permet l'accès depuis n'importe quel appareil du réseau
    app.run(host='0.0.0.0', port=5000, debug=False)