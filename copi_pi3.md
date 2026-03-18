sudo adduser tempuser
sudo usermod -aG sudo tempuser

ssh tempuser@adresse_ip

Désactiver l'autologin
bashsudo nano /etc/systemd/system/getty@tty1.service.d/autologin.conf
```

Commente la ligne `ExecStart` avec un `#` ou change `--autologin phypi30` :
```
[Service]
#ExecStart=...--autologin phypi30...
Puis :
bashsudo systemctl daemon-reload
sudo kill -9 $(pgrep -u phypi30)
Maintenant renomme :
bashsudo usermod -l phypi31 phypi30
sudo usermod -d /home/phypi31 -m phypi30
sudo groupmod -n phypi31 phypi30
Réactiver l'autologin avec le nouveau nom
bashsudo nano /etc/systemd/system/getty@tty1.service.d/autologin.conf
Remplace phypi30 par phypi31, décommente la ligne.
bashsudo systemctl daemon-reload



C'est bon ! Le usermod -l a réussi. Les erreurs suivantes sont normales car phypi30 n'existe plus.
Vérifie l'état :
bashid phypi31
ls /home/
Le home a peut-être not été renommé, donc vérifie et fais-le manuellement si besoin :
bashsudo usermod -d /home/phypi31 -m phypi31
sudo groupmod -n phypi31 phypi31 2>/dev/null || true
Ensuite réactive l'autologin :
bashsudo nano /etc/systemd/system/getty@tty1.service.d/autologin.conf
Remplace phypi30 par phypi31 dans le fichier, puis :
bashsudo systemctl daemon-reload
Enfin supprime tempuser :
bashsudo deluser --remove-home tempuser
Et reconnecte-toi en SSH avec phypi31.












Modifier une IP fixe configurée avec nmcli
Voir les connexions existantes
sudo nmcli con show
Tu obtiens la liste avec les noms (colonne NAME).
Modifier l'IP fixe
sudo nmcli con mod "NOM_CONNEXION" ipv4.addresses "192.168.1.50/24"
sudo nmcli con mod "NOM_CONNEXION" ipv4.gateway "192.168.1.1"
sudo nmcli con mod "NOM_CONNEXION" ipv4.dns "192.168.1.1"   
sudo nmcli con mod "NOM_CONNEXION" ipv4.method manual
Appliquer les changements
sudo nmcli con down "NOM_CONNEXION"
sudo nmcli con up "NOM_CONNEXION"
Ou plus brutal si tu es en SSH et que ça coupe :
sudo nmcli con reload

Vérifier le résultat
baship a
# ou
sudo nmcli con show "NOM_CONNEXION" | grep ipv4

Repasser en DHCP si besoin
bashsudo nmcli con mod "NOM_CONNEXION" ipv4.method auto
sudo nmcli con mod "NOM_CONNEXION" ipv4.addresses ""
sudo nmcli con mod "NOM_CONNEXION" ipv4.gateway ""
sudo nmcli con up "NOM_CONNEXION"


Attention SSH : si tu modifies l'IP depuis une session SSH, la connexion va couper au moment du con up. Utilise un écran ou prévois de te reconnecter sur la nouvelle IP.