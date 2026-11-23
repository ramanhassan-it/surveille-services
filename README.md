# surveille-services

Script python qui verifie toutes les X minutes si mes machines et services marchent encore, et qui garde un historique.

En exploitation le plus important c'est de savoir qu'un truc est tombe avant que quelqu'un appelle pour dire que ca marche plus. En entreprise ils utilisent des outils comme Zabbix, PRTG ou Nagios. J'ai voulu faire une version mini pour comprendre comment ca marche dedans.

Le script lit une liste de services dans `services.txt`, teste chaque service, affiche le resultat et l'ajoute dans `logs/historique.csv`. Si un service passe de OK a DOWN (ou revient), il ecrit une alerte dans `logs/alertes.txt`.

Ensuite `rapport.py` lit l'historique et calcule la disponibilite de chaque service (en %).

## Ce qu'il sait tester

| type | exemple | ca verifie quoi |
|---|---|---|
| ping | `192.168.1.1` | la machine repond au reseau |
| port | `192.168.1.20:445` | un service ecoute sur ce port (partage, RDP, DNS...) |
| http | `https://ramanhassan.ch` | le site repond (erreur 500+ = DOWN) |
| disque | `C:\` | le disque est rempli a moins de 90% |

Une machine peut repondre au ping alors que le service dessus est mort, c'est pour ca qu'il y a aussi le test de port.

## Utilisation

Rien a installer, que python.

Mettre ses services dans `services.txt` (format `nom ; type ; cible`) puis :

```
python surveille.py
python surveille.py --boucle 5
python rapport.py
python rapport.py 7
```

`--boucle 5` = relance toutes les 5 min. `rapport.py 7` = seulement les 7 derniers jours.

```
--- 2026-11-15 03:00:03 ---
DOWN  box              ping     3004 ms  pas de reponse au ping
DOWN  dns google       port     3001 ms  timeout
OK    disque C         disque      0 ms  82% utilise, 85.7 Go libre
...
!! 2026-11-15 03:00:03  TOMBE   box (192.168.1.1) pas de reponse au ping
```

Y'a un historique d'exemple (2 jours) dans `exemple/` pour tester le rapport sans attendre :

```
python rapport.py exemple/historique.csv
```

```
service            dispo     moy  tests  dernier down
--------------------------------------------------------------
portfolio          93.8%   234ms     48  2026-11-16 01:00:00
box                95.8%     5ms     48  2026-11-15 04:00:04
dns google         95.8%    18ms     48  2026-11-15 04:00:04
dns cloudflare     95.8%    15ms     48  2026-11-15 04:00:04
github             95.8%   302ms     48  2026-11-15 04:00:04
disque C          100.0%     0ms     48  -
```

Dans l'exemple on voit que quand la box tombe, tout tombe en meme temps (dns, sites). Donc si tout est DOWN d'un coup, faut regarder la box / le reseau en premier et pas chaque service un par un.

## Le lancer tout seul

Plutot que `--boucle` (faut laisser la fenetre ouverte), mieux vaut le planificateur.

Windows (planificateur de taches), toutes les 5 min :

```
schtasks /create /tn "surveille-services" /tr "python C:\chemin\vers\surveille.py" /sc minute /mo 5
```

Linux (cron, `crontab -e`) :

```
*/5 * * * * python3 /home/raman/surveille-services/surveille.py
```

## A utiliser sur ses machines

Le script fait juste un ping, une connexion sur un port ou une requete web, comme n'importe quel navigateur. Mais tester les ports de machines qui sont pas a toi c'est pas correct, donc je le lance que sur mon reseau et mes propres sites.

## Problemes

- le planificateur lance le script depuis `C:\Windows\System32`, donc il trouvait pas `services.txt`. Corrige avec `os.chdir` au debut du script
- si le pc qui lance le script perd internet, tout passe en DOWN alors que les serveurs vont bien. Il se surveille pas lui meme
- `historique.csv` grossit tout le temps et il est relu en entier a chaque passage pour retrouver le dernier etat. Ca va devenir lent apres quelques mois
- un site qui repond 403 ou 404 est compte OK (le serveur repond). C'est voulu mais ca se discute
- les alertes vont juste dans un fichier, personne est prevenu

## A faire

- envoyer l'alerte par mail ou sur Telegram
- verifier la date d'expiration des certificats SSL
- verifier qu'une sauvegarde a bien ete faite (date du dernier fichier dans un dossier)
- une petite page web avec l'etat de chaque service
