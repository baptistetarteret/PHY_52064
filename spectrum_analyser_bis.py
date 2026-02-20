import pyaudio
import numpy as np
import os

# --- CONFIGURATION ---
CHUNK = 1024
FORMAT = pyaudio.paInt32
CHANNELS = 2
RATE = 44100
COLUMNS = 60  # Largeur de l'affichage dans ton terminal
MAX_VAL = 20  # Hauteur max des barres (en lignes)

p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                input=True, frames_per_buffer=CHUNK)

def draw_bars(data):
    # On efface l'écran du terminal (méthode rapide)
    print("\033[H", end="") 
    
    # FFT et traitement
    fft_data = np.abs(np.fft.rfft(data))
    # On divise les fréquences en 'COLUMNS' groupes (bins)
    bins = np.array_split(fft_data, COLUMNS)
    
    output = ""
    for b in bins:
        # On calcule la moyenne du groupe et on normalise
        v = int(np.mean(b) / 1000000) # Ajuste ce diviseur selon la sensibilité
        v = min(v, MAX_VAL)
        # On crée une barre verticale simple
        output += "█" if v > 2 else " " 
        
    print(f"Spectre FFT (INMP441) - Ctrl+C pour quitter")
    print("-" * COLUMNS)
    print(output)

print("\033[2J") # Efface l'écran une fois au début
try:
    while True:
        raw_data = stream.read(CHUNK, exception_on_overflow=False)
        audio_data = np.frombuffer(raw_data, dtype=np.int32)[::2]
        # On applique une petite fenêtre
        draw_bars(audio_data * np.hanning(len(audio_data)))
except KeyboardInterrupt:
    print("\nTerminé.")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()