1. Espacement des micros
C'est le paramètre le plus critique. Le délai différentiel entre deux micros vaut :
dt = d / 343
Avec des micros espacés de 1 m, le délai max est 1/343 = 2.9 ms. Si ton bruit est de 0.5 ms, l'incertitude relative est 0.5/2.9 = 17% — énorme.
Avec des micros espacés de 10 m, le délai max est 29 ms. La même incertitude de 0.5 ms donne 1.7% — bien meilleur.
Règle générale : l'espacement des micros doit être grand devant bruit_ms × 343.

2. Forme du triangle
Un triangle équilatéral est optimal. Les configurations dégénérées à éviter :

Micros colinéaires : les hyperboles deviennent presque parallèles, l'intersection est très mal définie
Triangle très aplati : mauvaise résolution dans la direction perpendiculaire à la base
Source dans l'alignement d'un côté : une des hyperboles dégénère


3. Position de la source par rapport aux micros
La précision se dégrade fortement quand la source est loin en dehors du triangle. À l'intérieur ou proche, les hyperboles se croisent à angle favorable. Loin, elles se croisent presque tangentiellement — petite erreur de timestamp → grande erreur de position.
Erreur position ~ bruit_temps × c / sin(angle_intersection)
Quand l'angle tend vers zéro (source très lointaine), l'erreur explose.


4. Incertitude temporelle
L'erreur de position est directement proportionnelle au bruit sur les timestamps :
erreur_position ~ bruit_ms × 0.343 m/ms
Avec 1 ms de bruit → ~34 cm d'erreur minimum. Avec 0.1 ms → ~3.4 cm. C'est pour ça que chrony sub-ms est indispensable, et que le chunk à 1 ms est la limite basse du système.