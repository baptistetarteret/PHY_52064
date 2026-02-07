# Projet de PHY_52064

## Objectif :

Produire des modules de sondage sonore actif, 
produire un protocol de gestion de la detection et de la donnée sonore
produire un system et protocol de communication
produire une base arriere pour gestion des detection, calcul et triangulation

## Details

Precision : 10cm si possible
=> 3e-4s (0.3ms) dephasage des capteurs 

frequence propre metaux : 10kHz
=> shanon : 30kHz
44.1 kHz (audio standard) correct pour la fondamentale
48 kHz (audio professionnel) - mieux pour la fondamentale + 1ère harmonique
96 kHz - 100 kHz analyse de Fourier complète

synchronisation des horloges : 
=> module quartz a horloge, + decompte pour synchro
=> emission du pi en lora, detection par tous, synchro, derive petit a petit (problem, compliqué de resynchro, ou alors tout le monde en ecoute en continu)
=> synchro en module RF regulier d'un maitre

pi5 : oscillateur à cristal 32,768 kHz
+ derive < 10 ppm (60 µs / min soit 6e-5/min)

Arduino sans RTC : > 60–100 ppm
avec RTC : ~2 ppm





## Micro :

### ICS‐43434:

Sensitivity −26 dB FS ±1 dB  −26 dB FS ±1 dB
SNR 64 dBA 64 dBA
Current 490 µA 230 µA
AOP 120 dB SPL 120 dB SPL
Sample Rate 23 – 51.6 kHz 6.25 – 18.75 kHz




## Synchro temps:
### Mesurer le Round-Trip Time (RTT)
1. Master envoie T1 (timestamp départ)
2. Slave reçoit à T2, répond immédiatement avec T2
3. Master reçoit à T3
4. Offset = ((T2 - T1) + (T2 - T3)) / 2
5. Slave ajuste son horloge