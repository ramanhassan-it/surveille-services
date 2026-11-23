# surveille services
# verifie si mes machines et services repondent (ping, port, site web, disque)
# et garde tout dans logs/historique.csv
# usage : python surveille.py   (ou python surveille.py --boucle 5 pour relancer toutes les 5 min)

import csv
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

FICHIER_SERVICES = "services.txt"
HISTORIQUE = "logs/historique.csv"
ALERTES = "logs/alertes.txt"
TIMEOUT = 3
SEUIL_DISQUE = 90  # en %, au dessus le disque est considere DOWN

windows = platform.system() == "Windows"

# le planificateur de taches lance le script depuis C:\Windows\System32
# donc sans ca il trouve pas services.txt
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def lire_services():
    services = []
    with open(FICHIER_SERVICES, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#"):
                continue
            morceaux = [m.strip() for m in ligne.split(";")]
            if len(morceaux) != 3:
                print("ligne ignoree (il faut nom ; type ; cible) :", ligne)
                continue
            services.append(morceaux)
    return services


def test_ping(ip):
    if windows:
        cmd = ["ping", "-n", "1", "-w", str(TIMEOUT * 1000), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", str(TIMEOUT), ip]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    except FileNotFoundError:
        return False, "commande ping introuvable"
    # meme probleme que dans inventaire-reseau : sur windows returncode = 0 meme si injoignable
    if "ttl=" in res.stdout.lower():
        return True, ""
    return False, "pas de reponse au ping"


def test_port(cible):
    hote, port = cible.rsplit(":", 1)
    try:
        s = socket.create_connection((hote, int(port)), timeout=TIMEOUT)
        s.close()
        return True, ""
    except socket.timeout:
        return False, "timeout"
    except ConnectionRefusedError:
        return False, "port ferme"
    except Exception as e:
        return False, str(e)


def test_http(url):
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": "surveille-services"})
    try:
        r = urllib.request.urlopen(req, timeout=TIMEOUT)
        return True, "code " + str(r.status)
    except urllib.error.HTTPError as e:
        # le serveur repond, mais avec une erreur
        if e.code >= 500:
            return False, "erreur serveur " + str(e.code)
        return True, "code " + str(e.code)
    except Exception as e:
        return False, str(e)[:60]


def test_disque(chemin):
    try:
        total, utilise, libre = shutil.disk_usage(chemin)
    except FileNotFoundError:
        return False, "chemin introuvable"
    pourcent = round(utilise / total * 100)
    libre_go = round(libre / 1024**3, 1)
    return pourcent < SEUIL_DISQUE, f"{pourcent}% utilise, {libre_go} Go libre"


TESTS = {
    "ping": test_ping,
    "port": test_port,
    "http": test_http,
    "disque": test_disque,
}


def derniers_etats():
    # relit l'historique pour savoir si un service etait OK ou DOWN la derniere fois
    etats = {}
    if not os.path.exists(HISTORIQUE):
        return etats
    with open(HISTORIQUE, encoding="utf-8-sig") as f:
        for ligne in csv.DictReader(f, delimiter=";"):
            etats[ligne["nom"]] = ligne["etat"]
    return etats


def verifier_tout():
    services = lire_services()
    avant = derniers_etats()
    maintenant = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resultats = []
    alertes = []

    print("\n---", maintenant, "---")
    for nom, type_test, cible in services:
        if type_test not in TESTS:
            print("type inconnu :", type_test, "pour", nom)
            continue

        debut = time.time()
        try:
            ok, detail = TESTS[type_test](cible)
        except Exception as e:
            # un test qui plante doit pas bloquer tous les autres
            ok, detail = False, "erreur : " + str(e)[:50]
        ms = round((time.time() - debut) * 1000)
        etat = "OK" if ok else "DOWN"

        print(f"{etat:<5} {nom:<16} {type_test:<7} {ms:>5} ms  {detail}")
        resultats.append([maintenant, nom, type_test, cible, etat, ms, detail])

        # alerte seulement quand ca change, sinon ca spam a chaque passage
        if avant.get(nom) == "OK" and etat == "DOWN":
            alertes.append(f"{maintenant}  TOMBE   {nom} ({cible}) {detail}")
        elif avant.get(nom) == "DOWN" and etat == "OK":
            alertes.append(f"{maintenant}  REVENU  {nom} ({cible})")

    os.makedirs("logs", exist_ok=True)
    nouveau = not os.path.exists(HISTORIQUE)
    # ; et utf-8-sig pour que excel ouvre bien le csv
    with open(HISTORIQUE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if nouveau:
            w.writerow(["date", "nom", "type", "cible", "etat", "temps_ms", "detail"])
        w.writerows(resultats)

    if alertes:
        with open(ALERTES, "a", encoding="utf-8") as f:
            for a in alertes:
                print("!!", a)
                f.write(a + "\n")

    nb_down = sum(1 for r in resultats if r[4] == "DOWN")
    print(f"{len(resultats) - nb_down}/{len(resultats)} OK")


if "--boucle" in sys.argv:
    minutes = int(sys.argv[sys.argv.index("--boucle") + 1])
    print("verification toutes les", minutes, "min, ctrl+c pour arreter")
    try:
        while True:
            verifier_tout()
            time.sleep(minutes * 60)
    except KeyboardInterrupt:
        print("arrete")
else:
    verifier_tout()
