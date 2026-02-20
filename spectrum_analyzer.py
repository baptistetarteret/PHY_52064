import pyaudio
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
CHUNK = 2048             # Nombre d'échantillons par lecture (plus c'est gros, plus la FFT est précise)
FORMAT = pyaudio.paInt32 # Le INMP441 sort souvent du 24-bit encapsulé en 32-bit
CHANNELS = 2             # L'I2S envoie souvent 2 canaux (même pour 1 micro)
RATE = 44100             # Fréquence d'échantillonnage standard

# Initialisation PyAudio
p = pyaudio.PyAudio()

# Ouverture du flux
stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

# Préparation graphique
plt.ion() # Mode interactif
fig, ax = plt.subplots(figsize=(10, 5))
x_freq = np.linspace(0, RATE // 2, CHUNK // 2 + 1) # Axe des fréquences
line, = ax.plot(x_freq, np.zeros(len(x_freq)), color='cyan')

ax.set_title("Analyse de spectre FFT - INMP441 + Pi 5")
ax.set_xlabel("Fréquence (Hz)")
ax.set_ylabel("Amplitude")
ax.set_xlim(20, 20000)  # On limite à la plage audible (20Hz - 20kHz)
ax.set_ylim(0, 10**8)   # À ajuster selon le gain de ton micro
ax.set_xscale('log')    # Échelle logarithmique (plus naturelle pour l'oreille)
ax.grid(True, which='both', linestyle='--', alpha=0.5)

print("Capturer le son... (Appuie sur Ctrl+C pour arrêter)")

try:
    while True:
        # 1. Lecture des données brutes
        data = stream.read(CHUNK, exception_on_overflow=False)
        
        # 2. Conversion en tableau Numpy (on prend un seul canal)
        audio_data = np.frombuffer(data, dtype=np.int32)
        audio_data = audio_data[::2] # On prend 1 échantillon sur 2 (stéréo -> mono)
        
        # 3. Application d'une fenêtre de Hanning (évite les artefacts aux bords)
        windowed_data = audio_data * np.hanning(len(audio_data))
        
        # 4. Calcul de la FFT
        fft_data = np.abs(np.fft.rfft(windowed_data))
        
        # 5. Mise à jour du graphique
        line.set_ydata(fft_data)
        
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nArrêt en cours...")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()